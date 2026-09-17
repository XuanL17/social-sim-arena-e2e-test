"""Authentication boundaries and retry-safe user-authored registration PRs."""
import base64
import json
import os
import unittest
from unittest.mock import patch, Mock
from urllib.parse import parse_qs, urlsplit
from cryptography.fernet import Fernet
from ssa import registration_login as r


class RegistrationLoginTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'SSA_OAUTH_CLIENT_ID':'client', 'SSA_OAUTH_CLIENT_SECRET':'secret',
            'SSA_OAUTH_COOKIE_KEY':Fernet.generate_key().decode(),
            'SSA_REGISTRATION_ORIGIN':'https://arena.example',
            'SSA_REGISTRATION_REPO':'owner/arena', 'SSA_REGISTRATION_BASE':'test-registry'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.user = {'id':17, 'login':'XuanL17'}
        self.record = {'entrant_id':'new-person','name':'Xuan','organization':'Lab',
                       'github':'impostor', 'keys':[{'id':'k1','alg':'ed25519',
                           'public':base64.b64encode(bytes(range(32))).decode()}]}
        self.session = {'token':'user-token', 'id':17, 'login':'XuanL17',
                        'origin':'https://arena.example', 'csrf':'csrf'}
        self.headers = {'Cookie':r.SESSION+'='+r.pack(self.session),
                        'Origin':'https://arena.example', 'X-CSRF-Token':'csrf',
                        'Content-Type':'application/json'}

    def test_server_binds_verified_identity(self):
        doc = r.registration(self.record, self.user['login'])
        self.assertEqual(doc['github'], 'XuanL17')
        self.assertEqual(doc['type'], 'participant')

    def test_no_private_keys_or_duplicate_key_ids(self):
        for change in [{'private':'secret'}, {'keys':self.record['keys']*2}, {'keys':[]}]:
            with self.subTest(change=list(change)), self.assertRaises(r.LoginError):
                r.registration(dict(self.record, **change), 'XuanL17')

    def test_missing_login_rejected(self):
        with self.assertRaises(r.LoginError) as c:
            r.dispatch('POST','/api/registration',dict(self.headers, Cookie=''),b'{}')
        self.assertEqual(c.exception.status,401)

    def test_tampered_cookie_rejected(self):
        with self.assertRaises(r.LoginError):
            r.dispatch('GET','/api/auth/session',{'Cookie':r.SESSION+'=fake'})

    def test_expired_cookie_rejected(self):
        import time
        expired = r.cipher().encrypt_at_time(json.dumps(self.session).encode(), int(time.time()) - r.TTL - 5).decode()
        with self.assertRaises(r.LoginError):
            r.unpack({'Cookie':r.SESSION+'='+expired},r.SESSION)

    def test_csrf_and_cross_origin_rejected_before_github(self):
        for extra in [{'Origin':'https://evil.test'}, {'X-CSRF-Token':'wrong'}]:
            with self.subTest(extra=extra), patch.object(r,'GitHub') as gh, self.assertRaises(r.LoginError):
                r.dispatch('POST','/api/registration',dict(self.headers,**extra),b'{}')
            gh.assert_not_called()

    def test_session_response_never_exposes_oauth_token(self):
        status, payload, _=r.dispatch('GET','/api/auth/session',self.headers)
        self.assertEqual(status,200)
        self.assertEqual(payload,{'login':'XuanL17','csrf':'csrf'})

    def test_changed_token_identity_rejected(self):
        with patch.object(r,'GitHub') as gh:
            gh.return_value.call.return_value={'id':18,'login':'other'}
            with self.assertRaises(r.LoginError) as c:
                r.dispatch('POST','/api/registration',self.headers,json.dumps(self.record).encode())
            self.assertEqual(c.exception.status,401)

    def test_start_uses_state_pkce_exact_callback_and_clears_old_session(self):
        status, _, headers=r.dispatch('GET','/api/auth/github/start',{})
        q=parse_qs(urlsplit(dict(headers)['Location']).query)
        self.assertEqual(status,302)
        self.assertEqual(q['redirect_uri'],['https://arena.example/api/auth/github/callback'])
        self.assertEqual(q['code_challenge_method'],['S256'])
        self.assertEqual(q['prompt'],['select_account'])
        cookies=[v for k,v in headers if k=='Set-Cookie']
        self.assertIn('Max-Age=0',cookies[1])
        self.assertTrue(all('HttpOnly' in v and 'Secure' in v for v in cookies))

    def test_callback_rejects_wrong_state_without_exchanging_code(self):
        saved=r.pack({'state':'right','verifier':'pkce','origin':'https://arena.example'})
        with patch.object(r.requests,'post') as post, self.assertRaises(r.LoginError):
            r.dispatch('GET','/api/auth/github/callback?state=wrong&code=secret',{'Cookie':r.STATE+'='+saved})
        post.assert_not_called()

    def test_callback_sets_encrypted_session(self):
        saved=r.pack({'state':'right','verifier':'pkce','origin':'https://arena.example'})
        with patch.object(r.requests,'post') as post, patch.object(r,'GitHub') as gh:
            post.return_value.status_code=200
            post.return_value.json.return_value={'access_token':'user-token'}
            gh.return_value.call.return_value=self.user
            status,_,headers=r.dispatch('GET','/api/auth/github/callback?state=right&code=code',{'Cookie':r.STATE+'='+saved})
            self.assertEqual(status,302)
            self.assertNotIn('user-token',str(headers))
            self.assertEqual(post.call_args.kwargs['data']['code_verifier'],'pkce')

    def test_registered_id_cannot_be_taken_over(self):
        gh=Mock(); gh.call.return_value={'content':'exists'}
        with self.assertRaises(r.LoginError) as c:r.create_registration(gh,self.user,self.record)
        self.assertEqual(c.exception.status,409)
        self.assertEqual(gh.call.call_count,1)

    def test_retry_returns_existing_pr_without_writes(self):
        gh=Mock(); gh.call.side_effect=[None,[{'state':'open','html_url':'https://github.com/owner/arena/pull/1'}]]
        result=r.create_registration(gh,self.user,self.record)
        self.assertEqual(result['status'],'pending_review')
        self.assertTrue(all(c.args[0]=='GET' for c in gh.call.call_args_list))

    def test_first_submission_forks_writes_only_entrant_and_opens_user_pr(self):
        gh=Mock(); gh.call.side_effect=[None,[],{'object':{'sha':'base'}},
            {'owner':{'id':17},'full_name':'XuanL17/arena'}, None, {},None,{},
            {'files':[{'filename':'entrants/new-person.json','status':'added'}]},
            {'user':self.user,'html_url':'https://github.com/owner/arena/pull/1'}]
        result=r.create_registration(gh,self.user,self.record)
        self.assertEqual(result['status'],'pending_review')
        writes=[c for c in gh.call.call_args_list if c.args[0]=='PUT']
        self.assertEqual(len(writes),1)
        body=json.loads(base64.b64decode(writes[0].args[2]['content']))
        self.assertEqual(body['github'],'XuanL17')
        self.assertEqual(gh.call.call_args.args[2]['base'],'test-registry')


if __name__=='__main__':unittest.main()
