import json
import os
import sys
from collections import defaultdict

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.worker.worker import process_ocr


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.queues = defaultdict(list)

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = str(value)

    def delete(self, key):
        self.store.pop(key, None)

    def rpush(self, name, value):
        self.queues[name].append(value)

    def lpush(self, name, value):
        self.queues[name].insert(0, value)


class DummyHTTPClient:
    def post(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None


def failing_ocr(job):
    raise RuntimeError("boom")


def test_retry_and_dead_letter():
    redis_conn = FakeRedis()
    job = {
        "id": "1",
        "max_retries": 2,
        "webhook_url": "http://example.com",
        "webhook_secret": "s",
    }

    with pytest.raises(RuntimeError):
        process_ocr(
            job,
            redis_conn,
            http_client=DummyHTTPClient(),
            ocr_func=failing_ocr,
            queue_name="main",
            dead_letter_queue="dead",
        )

    assert json.loads(redis_conn.queues["main"].pop()) == job

    with pytest.raises(RuntimeError):
        process_ocr(
            job,
            redis_conn,
            http_client=DummyHTTPClient(),
            ocr_func=failing_ocr,
            queue_name="main",
            dead_letter_queue="dead",
        )

    assert redis_conn.queues["main"] == []
    assert json.loads(redis_conn.queues["dead"][0]) == job
    assert redis_conn.get("retries:1") is None
