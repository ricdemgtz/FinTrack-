"""Minimal Notion client used behind a feature flag."""

from typing import Any


class NotionClient:
    def __init__(self, token: str, database_id: str):
        self.token = token
        self.database_id = database_id

    def create_transaction(self, tx: dict) -> Any:
        """Send transaction to Notion (placeholder implementation)."""
        # In real implementation we'd call Notion API here.
        return {"sent": True, "transaction": tx.get("id")}
