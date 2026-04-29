# Calling Agent

A small FastAPI service that initiates outbound voice calls via **Bolna AI** and posts a Slack alert when a call ends.

```
┌────────┐  POST /calls   ┌──────────────┐  POST /call   ┌──────────┐
│ Caller ├───────────────▶│ Calling      ├──────────────▶│ Bolna AI │
└────────┘                │ Agent        │               └────┬─────┘
                          │ (FastAPI)    │                    │ webhook
                          │              │◀───────────────────┘ on status
                          │              │   POST /webhook/bolna
                          │              │
                          │              │  chat.postMessage   ┌───────┐
                          │              ├────────────────────▶│ Slack │
                          └──────────────┘                     └───────┘
```

The webhook receiver also has a sibling endpoint, `POST /alerts/{execution_id}`, for **manually** triggering a Slack alert for any past call — handy when you don't want to expose your localhost via ngrok during development.

---

## Prerequisites

- **Python 3.12+** (`.python-version` pins `3.12`)
- **[uv](https://docs.astral.sh/uv/)** for dependency management (`pipx install uv` or see uv's docs)
- A Bolna account, a Slack workspace where you can install an app, and the credentials they produce — see **[SETUP.md](SETUP.md)** for a step-by-step walkthrough

---

## Quickstart

### 1. Get your credentials

Follow **[SETUP.md](SETUP.md)** to obtain:

- `BOLNA_API_KEY` — Bolna dashboard
- `SLACK_BOT_TOKEN` — Slack app (`xoxb-…`)
- `SLACK_ALERT_CHANNEL` — channel name (no `#`) where the bot is a member
- An `agent_id` UUID from a Bolna agent you've configured

### 2. Clone and set up the environment

```bash
git clone <this-repo>
cd calling_agent

# Install dependencies into a local .venv
uv sync

# Copy and fill in the env template
cp .env.example .env
$EDITOR .env           # paste the values from SETUP.md
```

### 3. Run the server

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The service listens on **<http://localhost:8000>**.

### 4. Open the API docs

Visit **<http://localhost:8000/docs>** — interactive Swagger UI with summaries, schemas, and ready-to-send example payloads for every endpoint.

---

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `GET`  | `/health` | Liveness probe. |
| `POST` | `/calls` | Initiate an outbound call via Bolna. Returns the `execution_id`. |
| `GET`  | `/calls/{execution_id}` | Fetch the full execution record from Bolna (status, transcript, telephony, costs). |
| `POST` | `/alerts/{execution_id}` | Manually fetch an execution and post a Slack alert for it (always sends). |
| `POST` | `/webhook/bolna` | Bolna's webhook receiver. Posts a Slack alert when the call has ended (skips in-flight statuses). Always returns `200`. |

### Quick test (after the server is running)

```bash
# Place a call (immediate)
curl -X POST http://localhost:8000/calls \
  -H 'Content-Type: application/json' \
  -d '{"agent_id": "<agent-uuid>", "recipient_phone_number": "+91XXXXXXXXXX"}'

# Manually alert Slack for an existing execution
curl -X POST http://localhost:8000/alerts/<execution_id>
```

For the full set of example bodies (scheduled calls, dynamic prompt variables, etc.), use the dropdown in the Swagger UI at `/docs`.

---

## Local development vs. live webhook

Bolna's webhook posts to a public URL — your `localhost` is not reachable. So:

- **Locally** — use `POST /alerts/{execution_id}`. After a call finishes on Bolna, run the curl below and the Slack alert fires for that execution. No tunnel, no public URL needed.

  ```bash
  curl -X POST http://localhost:8000/alerts/<execution_id>
  ```

- **For real-time events** — deploy the service (see [Deployment](#deployment)) and paste the deployed URL into Bolna's **Analytics → Webhook URL** field, e.g. `https://calling-tool.onrender.com/webhook/bolna`. From then on, every status change Bolna emits hits your live `/webhook/bolna` and triggers a Slack alert automatically.

---

## Project layout

```
calling_agent/
├── README.md              # this file
├── SETUP.md               # credential walkthrough (Slack + Bolna)
├── pyproject.toml         # deps + Python pin
├── uv.lock
├── .env.example
├── docs/img/              # screenshots referenced from SETUP.md
└── src/
    ├── main.py            # FastAPI app, lifespan, router registration
    ├── config.py          # pydantic-settings; loads .env
    ├── models/            # pydantic schemas (Bolna request/response, Slack message)
    ├── providers/         # async httpx clients (one per upstream)
    ├── services/          # orchestration: CallService, AlertService
    ├── routes/            # FastAPI routers: calls, alerts, webhook, health
    └── utils/             # logger + OpenAPI metadata strings
```

The split is deliberate: routes call services, services call providers, providers are pure HTTP clients. No layer reaches around another.

---

## Deployment

This is a single FastAPI app — it'll run on any Python host. Below are the steps for **[Render](https://render.com)** (free tier works) since that's what this project is deployed on:

1. Push the repo to GitHub.
2. On Render: **New → Web Service**, connect the GitHub repo.
3. Configure:
   - **Runtime:** Python
   - **Build command:** `pip install uv && uv sync --frozen`
   - **Start command:** `uv run uvicorn src.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment**, add the same variables you set in `.env` (`BOLNA_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_BASE_URL`, `SLACK_ALERT_CHANNEL`, `BOLNA_BASE_URL`).
5. Deploy. Render gives you a URL like `https://calling-tool.onrender.com`.
6. In the Bolna dashboard, open your agent → **Analytics** → set the webhook URL to:

   ```
   https://<your-app>.onrender.com/webhook/bolna
   ```

Bolna will now POST to your live service on every call status change, and the Slack alert fires automatically when the call ends.

---

## Future scope

Things deliberately left out to keep the surface area minimal for this assignment:

- **Authentication / authorization.** All endpoints are open right now — anyone who can reach the server can place calls or trigger alerts. Fine for a local / sandboxed deployment, not fine for production. The natural additions are an `X-API-Key` header check on `/calls` and `/alerts/{execution_id}`, or full Bearer/JWT auth via `fastapi.security` if this ever sits behind a real client. Bolna's `/webhook/bolna` is a separate concern — that one would be hardened by verifying a Bolna-signed header (or, simpler, an IP allowlist on the platform side).

- **Batch endpoints.** Single-call/single-alert is the spec. If usage grows, the natural extensions are:
  - `POST /batch_calls` — accept a list of `CallRequestModel` and fan out via `asyncio.TaskGroup` with a `Semaphore` to cap concurrency against Bolna's rate limits.
  - `POST /batch_alerts` — accept a list of `execution_id`s and trigger alerts in parallel.
  - `POST /webhook/bolna_batch` — receive an array of executions in one webhook call.

  None are implemented; sketches live in `improvements.md`.

---

## Troubleshooting

The most common errors (token mistakes, trial-account number restrictions, channel membership) are documented in **[SETUP.md](SETUP.md#troubleshooting)**.
