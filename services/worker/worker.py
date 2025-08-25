import os
import json
import hmac
import hashlib
import uuid
import logging
from io import BytesIO

try:  # pragma: no cover - optional dependency in tests
    import httpx
except Exception:  # httpx may not be installed in test environment
    httpx = None
from PIL import Image
import pytesseract

QUEUE_NAME = os.getenv("OCR_QUEUE", "ocr")
DEAD_LETTER_QUEUE = os.getenv("OCR_DEAD_LETTER_QUEUE", "ocr_dead")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def process_ocr(
    job: dict,
    redis_conn,
    http_client=None,
    ocr_func=None,
    queue_name: str = QUEUE_NAME,
    dead_letter_queue: str = DEAD_LETTER_QUEUE,
):
    """Process a single OCR job.

    Parameters
    ----------
    job: dict
        Job payload.
    redis_conn: object
        Redis-like connection used for tracking retries and queuing.
    http_client: object
        HTTP client (httpx-compatible). Optional; defaults to httpx.
    ocr_func: callable
        Optional OCR function. If provided, it's called with job and should
        return extracted text. If not provided and job contains ``n8n_url``,
        an HTTP POST is performed to that URL to get OCR result. Otherwise
        pytesseract is used on the image at ``image_url``.
    queue_name: str
        Name of the main queue for retries.
    dead_letter_queue: str
        Name of the dead-letter queue.
    """
    http_client = http_client or httpx

    job_id = job.get("id") or str(uuid.uuid4())
    max_retries = int(job.get("max_retries", 3))
    retries_key = f"retries:{job_id}"
    attempt = int(redis_conn.get(retries_key) or 0)

    try:
        if ocr_func:
            text = ocr_func(job)
        elif job.get("n8n_url"):
            resp = http_client.post(job["n8n_url"], json=job)
            resp.raise_for_status()
            text = resp.json().get("text", "")
        else:
            resp = http_client.get(job["image_url"])
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
            text = pytesseract.image_to_string(image)

        payload = {"id": job_id, "text": text}
        secret = job.get("webhook_secret", "")
        signature = hmac.new(
            secret.encode(), json.dumps(payload).encode(), hashlib.sha256
        ).hexdigest()
        headers = {"X-Hub-Signature": signature}
        http_client.post(job["webhook_url"], json=payload, headers=headers)

        if job.get("notion_token") and job.get("notion_page_id"):
            notion_headers = {
                "Authorization": f"Bearer {job['notion_token']}",
                "Notion-Version": "2022-06-28",
            }
            notion_payload = {
                "parent": {"page_id": job["notion_page_id"]},
                "properties": {
                    "title": {"title": [{"text": {"content": text}}]}
                },
            }
            http_client.post(
                "https://api.notion.com/v1/pages",
                json=notion_payload,
                headers=notion_headers,
            )

        redis_conn.delete(retries_key)
    except Exception:
        attempt += 1
        if attempt >= max_retries:
            redis_conn.lpush(dead_letter_queue, json.dumps(job))
            redis_conn.delete(retries_key)
        else:
            redis_conn.set(retries_key, attempt)
            redis_conn.rpush(queue_name, json.dumps(job))
        raise


def run():
    """Run worker loop consuming jobs from Redis."""
    import redis  # imported lazily for test environments without the package

    redis_conn = redis.from_url(REDIS_URL)
    logging.info("Worker started, listening to %s", QUEUE_NAME)
    while True:
        _, job_data = redis_conn.blpop(QUEUE_NAME)
        job = json.loads(job_data)
        try:
            process_ocr(job, redis_conn)
        except Exception:
            logging.exception("Failed to process job %s", job.get("id"))


if __name__ == "__main__":
    run()
