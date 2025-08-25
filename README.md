# FinTrack+

FinTrack+ es un entorno de desarrollo basado en Docker para una API de seguimiento de gastos, un bot de Discord y flujos de automatización con n8n.

## Variables de entorno

1. Copia el archivo de ejemplo y completa los valores necesarios.
   ```bash
   cp .env.example .env
   ```
2. Ajusta credenciales de base de datos y Redis.
3. Define `DISCORD_BOT_TOKEN` y `DISCORD_GUILD_ID` para el bot.
4. Añade claves de Notion si deseas sincronización opcional (`NOTION_API_KEY`, `NOTION_DATABASE_ID`).

## Levantar los servicios

Con **Make**:
```bash
make dev      # build + up en primer plano
make up       # solo levantar en segundo plano
make logs     # seguir logs
make migrate  # aplicar migraciones
```

Directamente con **docker-compose**:
```bash
docker-compose up --build
```

## Bot de Discord
El bot usa [discord.py](https://discordpy.readthedocs.io/) y expone los comandos `/gasto`, `/ingreso` y `/foto`.

1. Crea una aplicación en el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications).
2. En "Bot", habilita los scopes `bot` y `applications.commands` al generar el enlace de invitación.
3. Intents requeridos: `Guilds` (por defecto) y `Message Content` si deseas procesar adjuntos.
4. Invita el bot a tu servidor usando el enlace generado.
5. Copia el token del bot y colócalo en `.env` como `DISCORD_BOT_TOKEN`. Opcionalmente define `DISCORD_GUILD_ID`.

## Túnel con Cloudflared
1. Instala [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).
2. Inicia sesión y crea un túnel:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create fintrack
   ```
3. Copia la configuración de ejemplo y edítala:
   ```bash
   cp cloudflared/config.yaml.example cloudflared/config.yaml
   ```
   Sustituye `tunnel`, `credentials-file` y define los hostnames necesarios:
   ```yaml
   ingress:
     - hostname: api.tudominio.com
       service: http://api:8000
     - hostname: bot.tudominio.com
       service: http://bot:3000
     - hostname: worker.tudominio.com
       service: http://worker:3000
     - hostname: n8n.tudominio.com
       service: http://n8n:5678
     - service: http_status:404
   ```
4. Ejecuta el túnel:
   ```bash
   cloudflared tunnel --config cloudflared/config.yaml run fintrack
   ```

## Ejemplos
- **Comprobar salud de la API**:
  ```bash
  curl https://api.tudominio.com/health
  ```
- **Registrar gasto vía Discord**: en tu servidor escribe `/gasto 12.50 Starbucks Latte`.
- **Flujo OCR con n8n**:
  1. Envía `/foto` con una imagen desde Discord.
  2. El bot reenvía la imagen al webhook de n8n.
  3. n8n realiza OCR y POSTea el texto a `https://api.tudominio.com/webhooks/ocr`.
  4. La API guarda el resultado junto al attachment correspondiente.

## Servicios y puertos
| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| api      | 8000   | API principal (FastAPI) |
| bot      | 3000   | Bot de Discord (HTTP opcional) |
| worker   | 3000   | Procesamiento de OCR |
| db       | 5432   | PostgreSQL |
| redis    | 6379   | Almacenamiento de colas y rate limit |
| n8n      | 5678   | Flujos de automatización |
| watchtower | -    | Actualización automática de contenedores |

