from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot import main


@pytest.mark.asyncio
async def test_post_transaction_expense():
    mock_client = MagicMock()
    mock_post = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = mock_post

    with patch("services.bot.main.httpx.AsyncClient", return_value=mock_client):
        await main.post_transaction(10.0, "Cafe", income=False)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/transactions")
    assert kwargs["json"]["amount"] == -10.0


@pytest.mark.asyncio
async def test_post_transaction_income():
    mock_client = MagicMock()
    mock_post = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = mock_post

    with patch("services.bot.main.httpx.AsyncClient", return_value=mock_client):
        await main.post_transaction(20.0, "Salario", income=True)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["amount"] == 20.0


@pytest.mark.asyncio
async def test_send_photo():
    class DummyAttachment:
        filename = "ticket.jpg"

        async def read(self):
            return b"data"

    mock_client = MagicMock()
    mock_post = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = mock_post

    with patch("services.bot.main.httpx.AsyncClient", return_value=mock_client):
        with patch("services.bot.main.OCR_ENDPOINT", "http://webhook"):  # noqa: F821
            await main.send_photo(DummyAttachment())

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://webhook"
    file_tuple = kwargs["files"]["file"]
    assert file_tuple[0] == "ticket.jpg"
    assert file_tuple[1] == b"data"

