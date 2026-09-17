"""GitHub OAuth registration. No database; short-lived encrypted HttpOnly session.

User access tokens create the user's own PR, preserving the existing CI owner check.
Never log cookies, OAuth codes, tokens, or request bodies.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlencode, quote, urlsplit, parse_qs

import requests
from cryptography.fernet import Fernet, InvalidToken
from jsonschema import validate, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SESSION = '__Host-ssa-registration'
STATE = '__Host-ssa-oauth-state'
TTL = 1800


class LoginError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def config():
    names = ['SSA_OAUTH_CLIENT_ID', 'SSA_OAUTH_CLIENT_SECRET', 'SSA_OAUTH_COOKIE_KEY',
             'SSA_REGISTRATION_ORIGIN', 'SSA_REGISTRATION_REPO', 'SSA_REGISTRATION_BASE']
    if any(not os.environ.get(n) for n in names):
        raise LoginError('login_not_configured', 503)
    origin = os.environ['SSA_REGISTRATION_ORIGIN']
    parsed = urlsplit(origin)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise LoginError('login_not_configured', 503)
    return origin


def cipher():
    return Fernet(os.environ['SSA_OAUTH_COOKIE_KEY'].encode())


def cookie(name, value='', age=TTL):
    return f'{name}={value}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age={age}'


def pack(value):
    return cipher().encrypt(json.dumps(value).encode()).decode()


def unpack(headers, name, ttl=TTL):
    jar = SimpleCookie()
    try:
        jar.load(headers.get('Cookie', ''))
        value = json.loads(cipher().decrypt(jar[name].value.encode(), ttl=ttl))
        if value['origin'] != config():
            raise ValueError()
        return value
    except (InvalidToken, KeyError, ValueError, TypeError):
        raise LoginError('login_required', 401) from None


class GitHub:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, data=None, missing=False):
        response = requests.request(method, 'https://api.github.com' + path,
            headers={'Authorization': 'Bearer ' + self.token,
                     'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28'}, json=data, timeout=15)
        if missing and response.status_code == 404:
            return None
        if response.status_code == 401:
            raise LoginError('login_required', 401)
        if response.status_code == 403:
            raise LoginError('github_permission_or_rate_limit', 403)
        if response.status_code not in (200, 201, 202, 204):
            raise LoginError('github_retry_required', 503)
        return response.json() if response.content else {}


def registration(document, login):
    if not isinstance(document, dict):
        raise LoginError('invalid_registration', 422)
    # Ignore a supplied username: only the authenticated /user result is authoritative.
    value = dict(document, github=login, type='participant')
    try:
        validate(value, json.loads((ROOT / 'schema/entrant.schema.json').read_text()))
        if not value.get('name', '').strip() or not value.get('organization', '').strip():
            raise ValueError()
        if bool(value.get('keys')) == bool(value.get('route')):
            raise ValueError()
        ids = set()
        for key in value.get('keys', []):
            raw = base64.b64decode(key['public'], validate=True)
            if len(raw) != 32 or key['id'] in ids or key.get('revoked'):
                raise ValueError()
            ids.add(key['id'])
    except (ValidationError, ValueError, TypeError, KeyError):
        raise LoginError('invalid_registration', 422) from None
    return value


def create_registration(gh, user, document):
    value = registration(document, user['login'])
    repo = os.environ['SSA_REGISTRATION_REPO']
    base = os.environ['SSA_REGISTRATION_BASE']
    prefix = '/repos/' + repo
    pathname = 'entrants/' + value['entrant_id'] + '.json'
    if gh.call('GET', prefix + '/contents/' + pathname + '?' + urlencode({'ref': base}), missing=True):
        raise LoginError('entrant_already_registered', 409)
    content = json.dumps(value, sort_keys=True, indent=2) + '\n'
    digest = hashlib.sha256(content.encode()).hexdigest()[:20]
    branch = f"registration/{user['id']}/{value['entrant_id']}/{digest}"
    head = user['login'] + ':' + branch
    pulls = gh.call('GET', prefix + '/pulls?' + urlencode({'state': 'all', 'head': head, 'base': base}))
    if pulls:
        pr = pulls[0]
        if pr['state'] == 'closed' and not pr.get('merged_at'):
            raise LoginError('registration_pr_closed', 409)
        return {'pr_url': pr['html_url'], 'status': 'merged' if pr.get('merged_at') else 'pending_review'}
    ref = gh.call('GET', prefix + '/git/ref/heads/' + quote(base, safe=''))
    if repo.split('/')[0].lower() == user['login'].lower():
        target = repo
    else:
        # GitHub returns the existing fork if already forked. It may need time to initialize.
        fork = gh.call('POST', prefix + '/forks', {'default_branch_only': False})
        if fork['owner']['id'] != user['id']:
            raise LoginError('fork_owner_mismatch', 403)
        target = fork['full_name']
    dest = '/repos/' + target
    existing = gh.call('GET', dest + '/git/ref/heads/' + quote(branch, safe=''), missing=True)
    if not existing:
        gh.call('POST', dest + '/git/refs', {'ref': 'refs/heads/' + branch, 'sha': ref['object']['sha']})
    old = gh.call('GET', dest + '/contents/' + pathname + '?' + urlencode({'ref': branch}), missing=True)
    if old:
        if base64.b64decode(old.get('content', '')).decode() != content:
            raise LoginError('registration_branch_changed', 409)
    else:
        gh.call('PUT', dest + '/contents/' + pathname, {
            'message': 'Register ' + value['entrant_id'], 'branch': branch,
            'content': base64.b64encode(content.encode()).decode()})
    # A participant can edit their fork independently. Never submit unrelated changes
    # through a pre-existing registration branch, including on retry.
    comparison = gh.call('GET', prefix + '/compare/' + quote(ref['object']['sha'], safe='')
                         + '...' + quote(head, safe=''))
    files = comparison.get('files', [])
    if len(files) != 1 or files[0].get('filename') != pathname or files[0].get('status') != 'added':
        raise LoginError('registration_branch_changed', 409)
    pr = gh.call('POST', prefix + '/pulls', {
        'title': 'Register ' + value['entrant_id'], 'head': head, 'base': base,
        'body': 'Register entrant and public signing keys through authenticated GitHub onboarding.\n\n'
                'Review the entrant record and run the existing ownership and schema checks before merging.'})
    if pr['user']['id'] != user['id']:
        raise LoginError('pr_author_mismatch', 502)
    return {'pr_url': pr['html_url'], 'status': 'pending_review'}


def dispatch(method, path, headers, raw=b''):
    origin = config()
    route = urlsplit(path).path
    query = parse_qs(urlsplit(path).query)
    if method == 'GET' and route == '/api/auth/github/start':
        verifier = secrets.token_urlsafe(32)
        state = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        location = 'https://github.com/login/oauth/authorize?' + urlencode({
            'client_id': os.environ['SSA_OAUTH_CLIENT_ID'], 'redirect_uri': origin + '/api/auth/github/callback',
            'scope': 'public_repo', 'state': state, 'code_challenge': challenge,
            'code_challenge_method': 'S256', 'prompt': 'select_account'})
        return 302, {}, [('Location', location), ('Set-Cookie', cookie(STATE, pack(
            {'state': state, 'verifier': verifier, 'origin': origin}), 600)),
            ('Set-Cookie', cookie(SESSION, age=0))]
    if method == 'GET' and route == '/api/auth/github/callback':
        saved = unpack(headers, STATE, 600)
        if not hmac.compare_digest(saved['state'], query.get('state', [''])[0]):
            raise LoginError('invalid_oauth_state', 403)
        code = query.get('code', [''])[0]
        if not code or len(code) > 1024:
            raise LoginError('authorization_cancelled')
        response = requests.post('https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'}, data={
                'client_id': os.environ['SSA_OAUTH_CLIENT_ID'],
                'client_secret': os.environ['SSA_OAUTH_CLIENT_SECRET'], 'code': code,
                'redirect_uri': origin + '/api/auth/github/callback', 'code_verifier': saved['verifier']}, timeout=15)
        result = response.json()
        if response.status_code != 200 or not result.get('access_token'):
            raise LoginError('authorization_failed', 401)
        token = result['access_token']
        user = GitHub(token).call('GET', '/user')
        session = pack({'token': token, 'id': user['id'], 'login': user['login'],
                        'csrf': secrets.token_urlsafe(32), 'origin': origin})
        return 302, {}, [('Location', origin + '/submit.html'),
            ('Set-Cookie', cookie(SESSION, session)), ('Set-Cookie', cookie(STATE, age=0))]
    if method == 'POST':
        if headers.get('Origin') != origin:
            raise LoginError('invalid_origin', 403)
    session = unpack(headers, SESSION)
    if method == 'GET' and route == '/api/auth/session':
        return 200, {'login': session['login'], 'csrf': session['csrf']}, []
    if method != 'POST' or not hmac.compare_digest(headers.get('X-CSRF-Token', ''), session['csrf']):
        raise LoginError('invalid_csrf', 403)
    if route == '/api/auth/logout':
        return 200, {'status': 'logged_out'}, [('Set-Cookie', cookie(SESSION, age=0))]
    if route != '/api/registration':
        raise LoginError('not_found', 404)
    if headers.get('Content-Type', '').split(';')[0] != 'application/json' or not 0 < len(raw) <= 16384:
        raise LoginError('invalid_body', 400)
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise LoginError('invalid_registration', 422) from None
    gh = GitHub(session['token'])
    user = gh.call('GET', '/user')
    if user['id'] != session['id']:
        raise LoginError('login_required', 401)
    return 200, create_registration(gh, user, document), []
