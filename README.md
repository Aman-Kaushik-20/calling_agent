# Calling Agent — multi-channel Bolna event dispatcher

A small **FastAPI** service that initiates outbound voice calls via **Bolna AI** and fans every terminal-status webhook out to every configured notification destination — concurrently, with per-provider error isolation.

Currently supports four destinations:

- **Slack** — `chat.postMessage` with colour-coded attachments
- **Discord** — channel webhook with rich embeds
- **Mattermost** — incoming webhook (Slack-compatible payload)
- **ClickUp** — task comments (one comment per call)

```
                                          ┌──────────┐
                                          │ Slack    │
                                          └──────────┘
                                          ▲
┌────────┐  POST /calls   ┌─────────────┐ │ ┌──────────┐
│ Caller ├───────────────▶│ Calling     ├─┴▶│ Discord  │
└────────┘                │ Agent       │   └──────────┘
                          │ (FastAPI)   │   ┌──────────┐
                          │             ├──▶│Mattermost│
            POST /webhook │             │   └──────────┘
            /bolna ───────▶             │   ┌──────────┐
            ◀──────────────              ├──▶│ ClickUp  │
            POST /call    │             │   └──────────┘
            ◀──────────────              │
            from Bolna AI │             │
                          └─────────────┘
```

A notifier is enabled when its env vars are present; missing vars silently disable it. `GET /health` reports which destinations are live.

A sibling endpoint `POST /alerts/{execution_id}` triggers the same fan-out manually for any past Bolna `execution_id` — handy when developing locally without exposing your laptop via ngrok.

---

## Prerequisites

- **Python 3.12+** (`.python-version` pins `3.12`)
- **[uv](https://docs.astral.sh/uv/)** for dependency management (`pipx install uv` or see uv's docs)
- A Bolna account, plus credentials for any subset of the four notification destinations — see **[SETUP.md](SETUP.md)** for the Slack + Bolna walkthrough

---

## Quickstart

### 1. Get your credentials

Bolna is required to fetch call data; everything else is optional. You can adopt destinations one at a time.

- `BOLNA_API_KEY` — Bolna dashboard
- `SLACK_BOT_TOKEN` + `SLACK_ALERT_CHANNEL` — Slack app (`xoxb-…`); see **[SETUP.md](SETUP.md)**
- `DISCORD_WEBHOOK_URL` — Discord channel → Edit Channel → Integrations → Webhooks → New
- `MATTERMOST_WEBHOOK_URL` — incoming webhook (Mattermost Cloud trial, Docker preview, or self-hosted)
- `CLICKUP_API_TOKEN` (`pk_…`) + `CLICKUP_TASK_ID` — personal API token + the task that should receive comments
- An `agent_id` UUID from a Bolna agent you've configured

### 2. Clone and set up the environment

```bash
git clone <this-repo>
cd calling_agent

# Install dependencies into a local .venv
uv sync

# Copy and fill in the env template
cp .env.example .env
$EDITOR .env           # paste any subset of provider credentials
```

### 3. Run the server

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The service listens on **<http://localhost:8000>**.

### 4. Open the API docs

Visit **<http://localhost:8000/docs>** — interactive Swagger UI with summaries, schemas, and ready-to-send example payloads. Hit `/health` to confirm which notifiers your env enabled.

---

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET`  | `/health` | Liveness probe. Body: `{status, notifiers: [...]}`. |
| `POST` | `/calls` | Initiate an outbound call via Bolna. Returns the queued `execution_id`. |
| `GET`  | `/calls/{execution_id}` | Fetch the full execution record from Bolna (status, transcript, telephony, costs). |
| `POST` | `/alerts/{execution_id}` | Manually fan an alert out to every enabled notifier (always sends, regardless of status). |
| `POST` | `/webhook/bolna` | Bolna's webhook receiver. Fans terminal-status events out to every enabled notifier (skips in-flight). Always returns `200`. |

The webhook + manual-alert responses both include a `delivered` map reporting per-provider outcome:

```json
{
  "received": true,
  "delivered": {"slack": "ok", "discord": "ok", "mattermost": "ok", "clickup": "ok"}
}
```

### Quick test (after the server is running)

```bash
# Place a call (immediate)
curl -X POST http://localhost:8000/calls \
  -H 'Content-Type: application/json' \
  -d '{"agent_id": "<agent-uuid>", "recipient_phone_number": "+91XXXXXXXXXX"}'

# Manually fan-out for an existing execution
curl -X POST http://localhost:8000/alerts/<execution_id>
```

For the full set of example bodies (scheduled calls, dynamic prompt variables, etc.), use the dropdown in the Swagger UI at `/docs`.

---

## How fan-out works

```python
# src/services/notifier.py
async def fanout(notifiers, execution) -> dict[str, str]:
    results = await asyncio.gather(
        *(n.send(execution) for n in notifiers),
        return_exceptions=True,
    )
    return {n.name: ("ok" if not isinstance(r, Exception) else f"error: ...")
            for n, r in zip(notifiers, results)}
```

- **All providers fire concurrently** via `asyncio.gather`.
- `return_exceptions=True` isolates per-provider failures — Slack 401-ing won't stop Discord from posting.
- Every error is logged with the provider name and execution_id.
- The webhook handler always returns 200 to Bolna regardless of any provider failure (a non-2xx would trigger Bolna's retry).
- The webhook also skips in-flight statuses (`scheduled`, `queued`, `rescheduled`, `initiated`, `ringing`, `in-progress`, `canceled`) — only terminal states get fanned out.

Each provider implements the same minimal surface:

```python
class XProvider:
    name: str
    async def send(execution: CallExecutionResponse) -> None: ...
    async def close() -> None: ...
```

---

## Local development vs. live webhook

Bolna's webhook posts to a public URL — your `localhost` is not reachable. So:

- **Locally** — use `POST /alerts/{execution_id}`. After a call finishes on Bolna, run the curl below and the fan-out fires for that execution. No tunnel, no public URL needed.

  ```bash
  curl -X POST http://localhost:8000/alerts/<execution_id>
  ```

- **For real-time events** — deploy the service (see [Deployment](#deployment)) and paste the deployed URL into Bolna's **Analytics → Webhook URL** field, e.g. `https://calling-tool.onrender.com/webhook/bolna`. From then on, every status change Bolna emits hits your live `/webhook/bolna` and triggers the fan-out automatically.

> **Mattermost note:** if you point at a local Docker preview (`http://localhost:8065/...`), the deployed instance can't reach it. Either skip `MATTERMOST_WEBHOOK_URL` on the deploy, or use Mattermost Cloud / a public self-host.

---

## Project layout

```
calling_agent/
├── README.md              # this file
├── SETUP.md               # Slack + Bolna credential walkthrough
├── pyproject.toml         # deps + Python pin
├── uv.lock
├── .env.example
├── docs/img/              # screenshots referenced from SETUP.md
├── temp/
│   └── ghost_test.py      # offline end-to-end test (no real upstream calls)
└── src/
    ├── main.py            # FastAPI app, lifespan, conditional notifier construction
    ├── config.py          # pydantic-settings; loads .env (every notifier is optional)
    ├── models/
    │   ├── bolna.py       # CallStatus, CallRequestModel, CallExecutionResponse, ...
    │   └── slack.py       # Slack-compatible attachment/message shapes (also used by Mattermost)
    ├── providers/
    │   ├── bolna.py       # Bolna HTTP client (calls + executions)
    │   ├── slack.py       # Slack notifier
    │   ├── discord.py     # Discord notifier
    │   ├── mattermost.py  # Mattermost notifier (reuses Slack formatter)
    │   ├── clickup.py     # ClickUp notifier (task comments)
    │   └── _attachment.py # shared Slack/Mattermost attachment builder
    ├── services/
    │   ├── call_service.py
    │   └── notifier.py    # fan-out via asyncio.gather + skip-in-flight gate
    ├── routes/            # calls, alerts, webhook, health
    └── utils/             # logger + OpenAPI metadata
```

The split is deliberate: routes call services, services call providers, providers are pure HTTP clients. Each provider owns both its HTTP and its formatter.

---

## Testing

A self-contained "ghost test" lives at [temp/ghost_test.py](temp/ghost_test.py). It boots the app with all four notifiers enabled but routes every upstream HTTP call (Bolna, Slack, Discord, Mattermost, ClickUp) through `httpx.MockTransport`, so nothing leaves the machine. Run it with:

```bash
uv run python temp/ghost_test.py
```

It exercises:

- `/health` — reports all four notifiers
- `/webhook/bolna` (in-flight status) — skipped, no fan-out
- `/webhook/bolna` (terminal status) — fans out to all four
- `/alerts/{id}` — fetches from (mock) Bolna, fans out to all four
- Per-provider error isolation — a failing notifier doesn't block the rest

---

## Deployment

This is a single FastAPI app — runs anywhere Python does. Steps for **[Render](https://render.com)** (free tier works):

1. Push the repo to GitHub.
2. On Render: **New → Web Service**, connect the GitHub repo.
3. Configure:
   - **Runtime:** Python
   - **Build command:** `pip install uv && uv sync --frozen`
   - **Start command:** `uv run uvicorn src.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment**, add the same variables you set in `.env`. Skip the providers you don't want — they auto-disable.
5. Deploy. Render gives you a URL like `https://calling-tool.onrender.com`.
6. In the Bolna dashboard, open your agent → **Analytics** → set the webhook URL to:

   ```
   https://<your-app>.onrender.com/webhook/bolna
   ```

Bolna will now POST to your live service on every call status change, and the fan-out fires automatically when the call ends.

---

## Future scope

Things deliberately left out to keep the surface area minimal:

- **Authentication / authorization.** All endpoints are open right now. The natural additions are an `X-API-Key` header check on `/calls` and `/alerts/{execution_id}`, or full Bearer/JWT auth via `fastapi.security`. Bolna's `/webhook/bolna` is a separate concern — that one would be hardened by verifying a Bolna-signed header (or, simpler, an IP allowlist on the platform side).

- **Per-request notifier routing.** A `notify_to: ["slack","discord"]` knob on `/alerts/{execution_id}` to fan out to a subset.

- **Retries / dead-letter** when a provider fails. Currently we log and move on.

- **Batch endpoints.** Single-call/single-alert is the spec. If usage grows:
  - `POST /batch_calls` — accept a list of `CallRequestModel` and fan out via `asyncio.TaskGroup` with a `Semaphore` to cap concurrency against Bolna's rate limits.
  - `POST /batch_alerts` — accept a list of `execution_id`s and trigger fan-outs in parallel.
  - `POST /webhook/bolna_batch` — receive an array of executions in one webhook call.

  None are implemented; sketches live in [temp/improvements.md](temp/improvements.md).

---

## Troubleshooting

The most common errors (token mistakes, trial-account number restrictions, channel membership) are documented in **[SETUP.md](SETUP.md#troubleshooting)**.
