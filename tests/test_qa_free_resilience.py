"""Offline fault injection for the hosted free-model adapter; no real keys/calls."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import requests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('qa_free_adapter', ROOT/'examples/remote-entrant/openrouter_ai.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
MODEL = 'liquid/lfm-2.5-2.6b:free'

class Cache:
    def __init__(self): self.rows = {}
    def get(self, key): return self.rows.get(key)
    def set(self, key, value, options): self.rows[key] = value

class Reply:
    def __init__(self, data, status=200): self.data, self.status_code = data, status
    def json(self): return self.data
    def raise_for_status(self):
        if self.status_code >= 400: raise requests.HTTPError(str(self.status_code))

class Provider:
    def __init__(self, reply=None, failure=None):
        self.calls, self.payloads, self.failure = 0, [], failure
        self.reply = reply or Reply({'id':'qa-generation','model':MODEL,'usage':{'cost':0},
                                    'choices':[{'message':{'content':'{"mean":42,"sd":2}'}}]})
    def get(self, *args, **kwargs):
        return Reply({'data':[{'id':MODEL,'pricing':{'prompt':'0','completion':'0','request':'0'}}]})
    def post(self, *args, **kwargs):
        self.calls += 1
        self.payloads.append(kwargs['json'])
        if self.failure: raise self.failure
        return self.reply

class FreeResilience(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'OPENROUTER_API_KEY':'offline-test-key', 'OPENROUTER_MODEL':MODEL})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.prompt = {'request_id':'qa:round','round':{'target_type':'continuous_normal','question':'Test'}}

    def test_429_and_5xx_do_not_retry_or_cache(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                cache, provider = Cache(), Provider(Reply({'error':{}},status))
                with self.assertRaises(RuntimeError): adapter.infer(self.prompt, cache, provider)
                self.assertEqual(provider.calls, 1)
                self.assertFalse(cache.rows)
                self.assertFalse(provider.payloads[0]['provider']['allow_fallbacks'])

    def test_timeout_does_not_retry_or_cache(self):
        cache, provider = Cache(), Provider(failure=requests.ReadTimeout('offline timeout'))
        with self.assertRaises(requests.ReadTimeout): adapter.infer(self.prompt, cache, provider)
        self.assertEqual(provider.calls, 1)
        self.assertFalse(cache.rows)

    def test_invalid_answers_are_not_cached(self):
        for content in ('not json', '{"mean":true,"sd":1}', '{"mean":1,"sd":0}', '{"mean":NaN,"sd":1}'):
            with self.subTest(content=content):
                reply = Reply({'id':'qa','usage':{'cost':0},'choices':[{'message':{'content':content}}]})
                cache = Cache()
                with self.assertRaises(ValueError): adapter.infer(self.prompt,cache,Provider(reply))
                self.assertFalse(cache.rows)

    def test_missing_or_nonzero_cost_is_rejected(self):
        for cost in (None,0.01):
            provider,cache = Provider(),Cache()
            provider.reply.data['usage']['cost'] = cost
            with self.assertRaises(RuntimeError): adapter.infer(self.prompt,cache,provider)
            self.assertFalse(cache.rows)

    def test_changed_question_cannot_reuse_old_forecast(self):
        cache,provider = Cache(),Provider()
        adapter.infer(self.prompt,cache,provider)
        changed = {**self.prompt,'round':{**self.prompt['round'],'question':'Changed'}}
        adapter.infer(changed,cache,provider)
        self.assertEqual(provider.calls,2)
        _,cached = adapter.infer(changed,cache,provider)
        self.assertTrue(cached)
        self.assertEqual(provider.calls,2)

    def test_unapproved_model_override_cannot_call_provider(self):
        provider = Provider()
        for model in ('paid/model','unapproved/model:free'):
            with self.assertRaises(ValueError):
                adapter.infer({**self.prompt,'e2e_model':model},Cache(),provider)
        self.assertEqual(provider.calls,0)

if __name__ == '__main__': unittest.main()
