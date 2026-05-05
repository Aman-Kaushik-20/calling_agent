# Credentials Setup

Bolna is the only required upstream — everything else is an optional notification destination. Set up only the notifiers you want; missing env vars silently disable that destination, and `GET /health` reports which ones are live.

| Provider | Required env vars |
|---|---|
| **Bolna** *(required)* | `BOLNA_API_KEY`, `BOLNA_BASE_URL` |
| Slack *(optional)* | `SLACK_BOT_TOKEN`, `SLACK_BASE_URL`, `SLACK_ALERT_CHANNEL` |
| Discord *(optional)* | `DISCORD_WEBHOOK_URL` |
| Mattermost *(optional)* | `MATTERMOST_WEBHOOK_URL` |
| ClickUp *(optional)* | `CLICKUP_API_TOKEN`, `CLICKUP_TASK_ID` |

This guide walks through each one. Bolna + one notifier takes ~15 min; adding the rest is a few minutes each.

---

## 1. Slack — Create a bot and get the token

We post alerts via Slack's `chat.postMessage` API, which needs a **Bot User OAuth Token** (`xoxb-…`) and a channel the bot belongs to.

### 1.1 Create a Slack app

1. Go to <https://api.slack.com/apps> and click **Create New App** → **From scratch**.
2. Name it (e.g. `calling-agent-alerts`) and pick the workspace you want alerts in.

![Slack: Create App "From scratch" dialog with app name and workspace picker](docs/img/slack-01-create-app.png)

### 1.2 Add the `chat:write` bot scope

1. A new Window Will Open. In the left sidebar, open **OAuth & Permissions**.

![Slack: Create App "From scratch" dialog with app name and workspace picker](docs/img/slack-01-auth-page.png)

2. Scroll to **Scopes → Bot Token Scopes** and click **Add an OAuth Scope**.
3. Add `chat:write`.
4. *(Optional, but convenient)* Add `chat:write.public` so the bot can post in public channels without being explicitly invited.

![Slack: OAuth & Permissions → Bot Token Scopes showing chat:write added](docs/img/slack-02-scopes.png)

### 1.3 Install the app to your workspace

1. Scroll up on the same page and click **Install to Workspace** (or **Reinstall** if you've changed scopes).
2. Approve the consent screen.
3. After the redirect, copy the **Bot User OAuth Token** — it starts with `xoxb-`. This is your `SLACK_BOT_TOKEN`.

![Slack: OAuth & Permissions → Bot User OAuth Token, "Copy" button highlighted](docs/img/slack-03-token.png)

> **Treat the token like a password.** Never commit it. `.env` is already in `.gitignore`.

### 1.4 Invite the bot to your alert channel

1. In Slack, open the channel where alerts should land (e.g. `#all-yoyo`).
2. Type `/invite @<your-app-name>` and confirm.
3. Note the **channel name without the `#`**. That's your `SLACK_ALERT_CHANNEL`.

![Slack: /invite command in a channel adding the bot user](docs/img/slack-04-invite.png)

> If you skipped `chat:write.public` and forget to invite the bot, posts will return `not_in_channel`.

Smoke test once you have both values:
```bash
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d "{\"channel\": \"$SLACK_ALERT_CHANNEL\", \"text\": \"hello from calling-agent\"}" \
  https://slack.com/api/chat.postMessage
```

---

## 2. Discord — easiest, no app/scopes/review

1. Create a server (top-left `+` → "Create My Own"), or use one you already have.
2. Pick a channel (e.g. `#bolna-alerts`) → click the gear ⚙ → **Integrations** → **Webhooks** → **New Webhook** → name it → **Copy Webhook URL**.
3. URL shape: `https://discord.com/api/webhooks/<id>/<token>`. That's `DISCORD_WEBHOOK_URL` — the only credential.

Smoke test:
```bash
curl -H 'Content-Type: application/json' \
  -d '{"content":"hello from calling-agent"}' \
  "$DISCORD_WEBHOOK_URL"
```

---

## 3. Mattermost — Slack-compatible payloads

Two paths — pick whichever's lighter for your environment.

### 3a. Local Docker preview (60 seconds, no signup)
```bash
docker run --rm --name mattermost-preview -d \
  --publish 8065:8065 \
  mattermost/mattermost-preview
```
- Visit <http://localhost:8065> → create the **first** account (auto-becomes admin) → create a team and channel.
- Top-left menu → **System Console** → **Integrations → Integration Management** → set **Enable Incoming Webhooks** = `true` → Save.
- Back to your team → profile menu → **Integrations** → **Incoming Webhooks** → **Add** → pick the channel → Save → copy the URL.
- URL shape: `http://localhost:8065/hooks/<hash>`.

### 3b. Mattermost Cloud trial (real public URL, good for the deployed demo)
Sign up at <https://mattermost.com/cloud-trial/>. Once you're in, the webhook setup steps from §3a from "Top-left menu →" onward are identical — just on `https://<workspace>.cloud.mattermost.com` instead of localhost.

That URL is `MATTERMOST_WEBHOOK_URL`. Slack's `{text, attachments}` JSON shape works as-is — this provider reuses the Slack formatter under the hood.

Smoke test:
```bash
curl -H 'Content-Type: application/json' \
  -d '{"text":"hello from calling-agent"}' \
  "$MATTERMOST_WEBHOOK_URL"
# expected: ok
```

> **Production caveat.** If `MATTERMOST_WEBHOOK_URL` points at `localhost`, the deployed Render service can't reach it — either skip the env var on the deploy, or use Mattermost Cloud.

---

## 4. ClickUp — task comments

Each Bolna call ends as a comment on a single dedicated ClickUp task. Comments appear in the task's right-hand panel and update in real-time via websocket — visible without refresh.

### 4.1 Token
1. Sign up at <https://clickup.com> (free tier is fine).
2. Avatar (bottom-left) → **Settings** → **Apps** → **API Token** → **Generate**. Copy the value (starts with `pk_…`). That's `CLICKUP_API_TOKEN`.

### 4.2 Task ID
1. Create (or pick) a Workspace → Space → List → a single Task (e.g. "Voice Call Event Log").
2. Open the task. The URL is `https://app.clickup.com/t/<task_id>` — copy the part after `/t/`. That's `CLICKUP_TASK_ID`.

Smoke test:
```bash
curl -X POST "https://api.clickup.com/api/v2/task/$CLICKUP_TASK_ID/comment" \
  -H "Authorization: $CLICKUP_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment_text":"hello from calling-agent","notify_all":false}'
```

You should see the comment appear instantly in the task's UI.

---

## 5. Bolna — Get the API key, verify a number, and pick an agent

### 5.1 Sign in and grab the API key

1. Go to <https://platform.bolna.ai> and sign in (or sign up).
2. Open **<https://platform.bolna.ai/developers> → Create New API Keys** (path may vary slightly).
3. Click **Create API Key**, name it (e.g. `local-dev`), and copy the value. This is your `BOLNA_API_KEY`.

![Bolna: API Keys page with "Create API Key" button and a key visible](docs/img/bolna-01-api-key.png)

> Bolna may only show the key **once**. Save it immediately. If you lose it, revoke and create a new one.

### 5.2 Verify your phone number (trial accounts only)

If you're on the Bolna **trial plan**, the API will only dial **verified** numbers. You'll see this error otherwise:

```
{"detail": "{\"message\":\"Trial accounts can only make calls to verified phone numbers.\"}"}
```

1. Go To <https://platform.bolna.ai/verified-phone-numbers> and Add & Verify your New Number.
2. Add the recipient number in **E.164** format (e.g. `+919354885227`).
3. Bolna sends an SMS or call with a code. Enter it.

![Bolna: Verified Numbers page with an E.164 number being added](docs/img/bolna-02-verify-number.png)

### 5.3 Create or pick an agent

You need an `agent_id` (UUID) to call into the service.

1. Open **Agents** in the dashboard.
2. Either create a new agent (set a voice, prompt, default `from_phone_number`, etc.) or open an existing one.
3. Copy the agent's UUID from the URL or the agent details panel — e.g. `3ead2b76-6776-4bce-983f-b7e0b8bb4754`.

You'll pass this UUID in the `agent_id` field of `POST /calls`.

![Bolna: Agent details panel with the agent UUID highlighted](docs/img/bolna-03-agent-id.png)

4. Optionally If you want the Webhook Support so that Bolna AI sends call events to your Webhook. add the URL in `Analytics Tab'

---

## 6. Fill in `.env`

Copy the template and paste the values you collected. Skip blocks for notifiers you don't want — they auto-disable.

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# Bolna (required)
BOLNA_API_KEY=<paste from §5.1>
BOLNA_BASE_URL=https://api.bolna.ai

# Slack (optional — §1)
SLACK_BOT_TOKEN=xoxb-<paste from §1.3>
SLACK_BASE_URL=https://slack.com/api
SLACK_ALERT_CHANNEL=<channel name without # from §1.4>

# Discord (optional — §2)
DISCORD_WEBHOOK_URL=<paste from §2>

# Mattermost (optional — §3)
MATTERMOST_WEBHOOK_URL=<paste from §3a or §3b>

# ClickUp (optional — §4)
CLICKUP_API_TOKEN=pk_<paste from §4.1>
CLICKUP_TASK_ID=<paste from §4.2>
```

Run the server and confirm via `/health`:
```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
curl -s http://localhost:8000/health
# {"status":"ok","notifiers":["slack","discord","mattermost","clickup"]}
```

Only the providers whose env vars you populated will appear in `notifiers`.

---

## End-to-end smoke test (after the server is running)

Fire a fake Bolna webhook with a terminal status — the service fans it out to every enabled notifier:

```bash
curl -X POST http://localhost:8000/webhook/bolna \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
    "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
    "status": "completed",
    "transcript": "Agent: Hi.\nUser: Hello.",
    "telephony_data": {
      "duration": "42",
      "to_number": "+919354885227",
      "from_number": "+918035735856",
      "provider": "plivo",
      "call_type": "outbound",
      "hangup_by": "User",
      "hangup_reason": "Normal hangup"
    }
  }'
```

Response:
```json
{"received": true, "delivered": {"slack": "ok", "discord": "ok", "mattermost": "ok", "clickup": "ok"}}
```

Each enabled destination gets one message in its native shape. Re-run with `"status": "in-progress"` to confirm the in-flight skip — the response should show `"delivered": {}` and the server log should print `Skipping notifier fan-out`.

Head back to the [main README](README.md) for the rest of the run instructions.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 invalid_auth` from Slack | Wrong token, or you copied the **Signing Secret** instead | Re-copy the **Bot User OAuth Token** (`xoxb-…`) |
| `not_in_channel` from Slack | Bot isn't a member of the target channel | `/invite @<bot>` in that channel, or add `chat:write.public` scope and reinstall |
| `channel_not_found` | Wrong channel name in `.env` (don't include `#`, don't include the channel ID) | Use the human-readable name, e.g. `all-yoyo` |
| Bolna returns `Trial accounts can only make calls to verified phone numbers` | Recipient is not on the verified list | See §5.2, or upgrade off trial |
| Bolna returns `401` | Wrong or revoked API key | Generate a fresh one in §5.1 |
| `/health` shows `notifiers: []` | No notifier env vars matched | Re-check `.env` — every required var per provider must be present |
| Discord: 401 on webhook URL | URL was rotated or deleted | Recreate the webhook on the channel |
| Discord: 429 Too Many Requests | Discord rate-limits each webhook to ~30 msg/min (with a tighter ~5/2s burst). Repeated test runs trip it. | Server logs `retry_after`. Slow down your tests, or add retry-with-backoff |
| Mattermost: `ConnectError` from deployed service | Webhook URL points at `localhost`, which the deployed instance can't reach | Either skip `MATTERMOST_WEBHOOK_URL` on the deploy, or use Mattermost Cloud / public self-host |
| Mattermost: `Webhooks have been disabled` | System Console toggle off | System Console → Integrations → enable Incoming Webhooks |
| ClickUp: `Team not authorized` | Used a workspace ID where a task ID was needed | Open the task in ClickUp; the ID is the part after `/t/` in the URL |
| ClickUp: `validateListIDEx List ID invalid` | List/task ID confusion | List IDs are numeric (e.g. `901614781100`); task IDs are alphanumeric (e.g. `86d2w7fxf`). This service uses task IDs |
| Webhook returns 200 but nothing fires | Either no notifiers are enabled, or all of them failed silently | Check `delivered` map in response body; check server logs for per-provider error |
| Calls dial from a different number than expected | Agent's default `from_phone_number` differs | Either change the default on the dashboard, or pass `from_phone_number` (a Bolna-registered number) in the request body |
