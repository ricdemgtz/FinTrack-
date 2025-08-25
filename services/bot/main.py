from __future__ import annotations

import os
from types import SimpleNamespace

try:  # pragma: no cover - allows tests without installed packages
    import discord
    from discord import app_commands
except Exception:  # pragma: no cover
    discord = None  # type: ignore
    app_commands = None  # type: ignore

try:  # pragma: no cover
    import httpx
except Exception:  # pragma: no cover
    httpx = SimpleNamespace(AsyncClient=object)  # type: ignore


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
OCR_ENDPOINT = os.getenv("N8N_WEBHOOK_URL") or f"{API_BASE_URL}/webhooks/ocr"


if discord is not None:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
else:  # pragma: no cover
    client = None  # type: ignore
    tree = None  # type: ignore


async def post_transaction(amount: float, merchant: str, note: str = "", income: bool = False) -> None:
    payload = {
        "user_id": 1,
        "account_id": 1,
        "amount": abs(amount) if income else -abs(amount),
        "merchant": merchant,
        "note": note,
    }

    async with httpx.AsyncClient() as http:
        await http.post(f"{API_BASE_URL}/transactions", json=payload)


async def send_photo(attachment: discord.Attachment) -> None:
    data = await attachment.read()

    async with httpx.AsyncClient() as http:
        await http.post(
            OCR_ENDPOINT,
            files={"file": (attachment.filename, data)},
        )


if tree is not None:

    @tree.command(name="gasto", description="Registrar un gasto")
    @app_commands.describe(amount="Monto del gasto", merchant="Comercio", note="Nota opcional")
    async def gasto(
        interaction: discord.Interaction,
        amount: float,
        merchant: str,
        note: str = "",
    ):
        await post_transaction(amount, merchant, note, income=False)
        await interaction.response.send_message("Gasto registrado")


    @tree.command(name="ingreso", description="Registrar un ingreso")
    @app_commands.describe(amount="Monto del ingreso", merchant="Origen", note="Nota opcional")
    async def ingreso(
        interaction: discord.Interaction,
        amount: float,
        merchant: str,
        note: str = "",
    ):
        await post_transaction(amount, merchant, note, income=True)
        await interaction.response.send_message("Ingreso registrado")


    @tree.command(name="foto", description="Enviar foto a OCR")
    async def foto(interaction: discord.Interaction, attachment: discord.Attachment):
        await send_photo(attachment)
        await interaction.response.send_message("Imagen enviada")


    @client.event
    async def on_ready():
        await tree.sync()
        print(f"Logged in as {client.user}")


if __name__ == "__main__" and client is not None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    client.run(token)

