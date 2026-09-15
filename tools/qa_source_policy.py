"""Versioned source policy ONLY for newly created qa-* synthetic rounds."""
from datetime import datetime, timedelta, timezone
import hashlib
import json

VERSION = 'qa-friday-utc-v1'


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed.astimezone(timezone.utc)


def evaluate(round_id, friday, snapshots, now, previous=None):
    """Pure evaluator. Snapshots carry source observation and archive clocks.

    Never mutates input or scores a pending/cancelled result. Caller persists
    returned events if audit durability is required.
    """
    if not round_id.startswith('qa-'):
        raise ValueError('policy restricted to new qa-* rounds')
    cutoff = instant(friday + 'T23:59:59Z')
    if cutoff.weekday() != 4:
        raise ValueError('target date must be Friday UTC')
    clock = instant(now)
    grace = cutoff + timedelta(hours=24)
    valid = []
    excluded_events = []
    for snapshot in snapshots:
        observed = instant(snapshot['observed_at'])
        fetched = instant(snapshot['fetched_at'])
        if fetched > grace and fetched <= clock:
            excluded_events.append({'type': 'late_archive_ignored', 'candidate_sha256':
                hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()})
        # A stale previous-day observation is not this Friday's result.
        # No snapshot may be observed after it was fetched or in the future.
        if (observed.date() == cutoff.date() and observed <= cutoff
                and observed <= fetched <= grace and fetched <= clock
                and snapshot.get('value') is not None):
            valid.append(snapshot)
    valid.sort(key=lambda s: (instant(s['observed_at']), instant(s['fetched_at']),
                             json.dumps(s, sort_keys=True)))
    selected = valid[-1] if valid else None
    fingerprint = (hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()
                   if selected else None)
    if previous:
        if previous['round_id'] != round_id or previous['policy_version'] != VERSION:
            raise ValueError('previous decision belongs to different round/policy')
        if previous['target_friday'] != friday:
            raise ValueError('target date cannot change')
        if previous['status'] in ('resolved', 'cancelled'):
            # A finalized result is frozen; a new candidate becomes review evidence.
            events = list(previous.get('events', []))
            for event in excluded_events:
                if event not in events:
                    events.append(event)
            if fingerprint and fingerprint != previous.get('snapshot_sha256'):
                event = {'type': 'revision_requires_review', 'candidate_sha256': fingerprint}
                if event not in events:
                    events.append(event)
            return {**previous, 'events': events}
    # Wait until grace expires so delayed archives have a deterministic window.
    status = 'pending' if clock < grace else ('resolved' if selected else 'cancelled')
    return {'round_id': round_id, 'target_friday': friday, 'policy_version': VERSION,
            'decision_version': 1, 'status': status,
            'value': selected['value'] if status == 'resolved' else None,
            'snapshot_sha256': fingerprint if status == 'resolved' else None,
            'counts_in_denominator': status == 'resolved', 'events': excluded_events}


def denominator(decisions):
    return sum(d['status'] == 'resolved' for d in decisions)
