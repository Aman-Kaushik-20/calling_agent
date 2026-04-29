---
name: calling-agent
description: helping me build a Python backend integration service. Here is everything you need to know before writing any code.
---

**PROBLEM STATEMENT**

Build an integration that sends a Slack alert whenever a Bolna Voice AI call ends with the following information: `id`, `agent_id`, `duration`, and `transcript`.

The flow is:
1. My service exposes a `POST /calls` endpoint to initiate an outbound call via Bolna API
2. Bolna calls my webhook at `POST /webhook/bolna` when the call status changes
3. When the webhook receives a payload with `status == "completed"` (or `"call-disconnected"`), extract `id`, `agent_id`, `transcript`, and `telephony_data.duration`
4. Send a formatted Slack alert with those 4 fields using the Slack Incoming Webhooks API

---

**API DOCUMENTATION LINKS** (read these before writing any code)

- Bolna: Make a call → https://www.bolna.ai/docs/api-reference/calls/make.md
- Bolna: Get execution → https://www.bolna.ai/docs/api-reference/executions/get_execution.md
- Bolna: Get agent → https://www.bolna.ai/docs/api-reference/agent/v2/get.md
- Bolna: Webhooks → https://www.bolna.ai/docs/polling-call-status-webhooks.md
- Slack: Incoming Webhooks (Python SDK) → https://docs.slack.dev/tools/python-slack-sdk/webhook/

---

**TECH STACK**

- Python 3.11+
- FastAPI + uvicorn
- httpx (async HTTP client for Bolna API calls)
- slack-sdk (for Slack Incoming Webhook)
- pydantic + pydantic-settings (models and config)
- uv + pyproject.toml (no requirements.txt)
- python-dotenv

---

**PROJECT STRUCTURE**

```
calling_agent/
├── README.md
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── src/
    ├── main.py               ← FastAPI app init, router registration
    ├── config.py             ← pydantic-settings, loads all env vars
    ├── models/
    │   ├── __init__.py
    │   └── bolna.py          ← Pydantic models for Bolna webhook payload and call request
    ├── providers/
    │   ├── __init__.py
    │   ├── bolna.py          ← async httpx client: make_call(), get_execution()
    │   └── slack.py          ← slack_sdk WebhookClient: post_message()
    ├── services/
    │   ├── __init__.py
    │   ├── call_service.py   ← calls bolna provider to initiate call, returns execution_id
    │   └── alert_service.py  ← receives execution data, formats message, calls slack provider
    ├── routes/
    │   ├── __init__.py
    │   ├── calls.py          ← POST /calls, GET /calls/{execution_id}
    │   ├── webhook.py        ← POST /webhook/bolna
    │   └── health.py         ← GET /health
    └── utils/
        ├── __init__.py
        └── logger.py         ← configured logger instance used across the app
```

---

**ENVIRONMENT VARIABLES**

```bash
# .env.example
BOLNA_API_KEY=your_bolna_api_key
BOLNA_BASE_URL=https://api.bolna.ai
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

---

**ROUTE CONTRACTS**



`POST /calls`
```json
// Request body
{
  "agent_id": "123e4567-e89b-12d3-a456-426655440000",
  "recipient_phone_number": "+10123456789",
  "from_phone_number": "+19876543007",
  "user_data": {
    "variable1": "value1"
  },
  "agent_data": {
    "voice_id": "Sam"
  }
}

// Response
{
  "message": "done",
  "status": "queued",
  "execution_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

`GET /calls/{execution_id}` — proxies `GET /executions/{execution_id}` from Bolna and returns the full response as-is.

`POST /webhook/bolna`
```json
// Bolna POSTs this to your server on every status change
// Payload structure matches GET /executions/{execution_id} response exactly
// Only trigger Slack alert when status == "completed" or "call-disconnected"
// Always return 200 OK immediately regardless of processing outcome
```

`GET /health`
```json
{ "status": "ok" }
```

---

**WEBHOOK BEHAVIOR RULES**

- Bolna fires the webhook on every status change: `queued` → `in-progress` → `completed`
- Only send the Slack alert when `status` is `"completed"` or `"call-disconnected"`
- Always return `200 OK` immediately — if you return non-200, Bolna may retry
- `duration` lives at `telephony_data.duration` in the payload, not at the top level
- `transcript` may be `null` for very short or failed calls — handle gracefully

---

**SLACK ALERT FORMAT**

The Slack message should be clean and readable. Use Block Kit with sections. Example structure:

```
📞 Call Ended

Call ID:    4c06b4d1-4096-4561-919a-4f94539c8d4a
Agent ID:   3c90c3cc-0d44-4b50-8888-8dd25736052a
Duration:   42 seconds
Status:     completed

Transcript:
"Hello, I'm calling about your recent inquiry..."
```

---

**LOCAL DEVELOPMENT SETUP**

This app is designed for local development with ngrok:

```bash
# Terminal 1
uv run uvicorn src.main:app --reload --port 8000

# Terminal 2
ngrok http 8000
# Copy the https URL e.g. https://abc123.ngrok-free.app

# Then paste this into Bolna's Analytics Tab:
# https://abc123.ngrok-free.app/webhook/bolna
```

---

**CODING RULES**

- All Bolna API calls must be async using `httpx.AsyncClient`
- Providers are pure HTTP clients — no business logic
- Services contain all orchestration logic — routes just call services
- Config is loaded once via `pydantic-settings` in `config.py` and injected where needed
- Use the logger from `utils/logger.py` everywhere — no bare `print()` statements
- All errors from external APIs (Bolna, Slack) must be caught and logged — never let them crash the webhook handler
- Pydantic models in `models/bolna.py` must match the actual Bolna API response schema from the docs
- Everything must be async for performance.
- Try to do everything in optimal way for best performance and low latency.


---

