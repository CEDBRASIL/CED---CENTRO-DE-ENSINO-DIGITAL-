import unittest
from unittest import mock
import sys
from types import SimpleNamespace

class DummyRouter:
    def route(self, *a, **k):
        def decorator(f):
            return f
        return decorator
    get=post=patch=delete=route

def File(*a, **k):
    return None

fastapi_stub = SimpleNamespace(APIRouter=DummyRouter, UploadFile=object, File=File, HTTPException=Exception)
fastapi_responses_stub = SimpleNamespace(JSONResponse=lambda x:x)
sys.modules.setdefault('fastapi', fastapi_stub)
sys.modules.setdefault('fastapi.responses', fastapi_responses_stub)

import disparos
import psycopg2

class WaitForDbTest(unittest.TestCase):
    def test_wait_for_db_retries(self):
        calls = []
        def fake_connect(*args, **kwargs):
            if len(calls) < 2:
                calls.append(None)
                raise psycopg2.OperationalError('fail')
            calls.append(None)
            class Cur:
                def __enter__(self): return self
                def __exit__(self, *exc): pass
                def execute(self, q): pass
                def fetchone(self): return (1,)
            class Conn:
                def __enter__(self): return self
                def __exit__(self, *exc): pass
                def cursor(self): return Cur()
            return Conn()
        with mock.patch('disparos.psycopg2.connect', side_effect=fake_connect):
            disparos.wait_for_db(max_attempts=3, base_delay=0.01)
        self.assertEqual(len(calls), 3)

if __name__ == '__main__':
    unittest.main()
