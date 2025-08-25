import hashlib
import hmac


def verify_hmac(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature for the given body.

    Args:
        body: Raw request body as bytes.
        signature: Hex-encoded HMAC sent by client.
        secret: Shared secret used to compute HMAC.
    Returns:
        True if signature is valid, False otherwise.
    """
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
