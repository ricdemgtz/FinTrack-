import importlib
import asyncio

"""Tests for Discord bot HTTP interactions using mocked httpx."""


def test_post_transaction_calls_api(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://api.test")
    import services.bot.main as bot_main
    importlib.reload(bot_main)

    captured = {}

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, files=None):
            captured["url"] = url
            captured["json"] = json
            captured["files"] = files

    monkeypatch.setattr(bot_main.httpx, "AsyncClient", MockClient)
    asyncio.run(bot_main.post_transaction(15.0, "Store", "note", income=False))

    assert captured["url"] == "http://api.test/transactions"
    assert captured["json"]["amount"] == -15.0
    assert captured["json"]["merchant"] == "Store"
def test_send_photo_calls_webhook(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://webhook.test/ocr")
    import services.bot.main as bot_main
    importlib.reload(bot_main)

    captured = {}

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, files=None):
            captured["url"] = url
            captured["files"] = files

    monkeypatch.setattr(bot_main.httpx, "AsyncClient", MockClient)

    class DummyAttachment:
        filename = "receipt.jpg"

        async def read(self):
            return b"fake-bytes"

    asyncio.run(bot_main.send_photo(DummyAttachment()))

    assert captured["url"] == "http://webhook.test/ocr"
    assert "file" in captured["files"]
    assert captured["files"]["file"][0] == "receipt.jpg"
