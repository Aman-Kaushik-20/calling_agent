"""OpenAPI metadata: app description, tag info, route summaries, and request examples.

Kept separate from route files so the handlers stay short and readable.
"""

API_DESCRIPTION = """
Backend integration that:

1. Initiates outbound voice calls via the **Bolna AI** API.
2. Receives Bolna's status webhooks and posts a **Slack** alert when a call ends.
3. Exposes a manual alert endpoint so a Slack message can be triggered for any past `execution_id`.

**Tags**

- `calls` — initiate / fetch call executions on Bolna.
- `alerts` — manually trigger a Slack alert for an existing execution.
- `webhook` — Bolna webhook receiver (called by Bolna, not by you).
- `health` — liveness probe.
"""

OPENAPI_TAGS = [
    {"name": "calls", "description": "Initiate outbound calls and fetch their execution data from Bolna."},
    {"name": "alerts", "description": "Manually trigger a Slack alert for an execution_id (fetches from Bolna, then posts to Slack)."},
    {"name": "webhook", "description": "Receives Bolna's status webhooks and posts to Slack when the call has ended."},
    {"name": "health", "description": "Liveness probe."},
]


# ─── POST /calls ──────────────────────────────────────────────────────────────

MAKE_CALL_SUMMARY = "Initiate an outbound call"
MAKE_CALL_DESCRIPTION = (
    "Forwards the request to Bolna's `POST /call` and returns the queued `execution_id`.\n\n"
    "- Omit `date`/`time` to call immediately.\n"
    "- Omit `from_phone_number`, `agent_data`, and `retry_config` to use the platform defaults configured on the agent.\n"
    "- On a Bolna trial account, `recipient_phone_number` must be a verified number on the dashboard."
)
MAKE_CALL_RESPONSES = {
    400: {"description": "Bolna rejected the request (e.g. unverified recipient on trial)."},
    502: {"description": "Bolna is unreachable (timeout, DNS, connection refused)."},
}
CALL_REQUEST_EXAMPLES: dict[str, dict] = {
    "minimal": {
        "summary": "Call now (minimal)",
        "description": "Place an outbound call right now using the agent's default `from_phone_number` and configuration on Bolna's dashboard.",
        "value": {
            "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
            "recipient_phone_number": "+919354885227",
        },
    },
    "scheduled": {
        "summary": "Schedule for a specific date/time (IST)",
        "description": "Send `date`, `time`, and optional `timezone` (IANA, defaults to `Asia/Kolkata`). The service computes `scheduled_at` for Bolna.",
        "value": {
            "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
            "recipient_phone_number": "+919354885227",
            "date": "2026-04-29",
            "time": "18:18:00",
            "timezone": "Asia/Kolkata",
        },
    },
    "with_user_data": {
        "summary": "With dynamic prompt variables",
        "description": "Pass `user_data` keys that the agent's prompt references (e.g. `{{name}}`, `{{topic}}`).",
        "value": {
            "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
            "recipient_phone_number": "+919354885227",
            "user_data": {"name": "Aman", "topic": "demo call"},
        },
    },
}


# ─── GET /calls/{execution_id} ────────────────────────────────────────────────

GET_CALL_SUMMARY = "Fetch a call's execution details"
GET_CALL_DESCRIPTION = (
    "Proxies Bolna's `GET /executions/{execution_id}`. Returns the full execution record — "
    "status, transcript, telephony metadata, cost breakdown, and timestamps."
)
GET_CALL_RESPONSES = {
    404: {"description": "No execution exists with this id on Bolna."},
    502: {"description": "Bolna is unreachable."},
}


# ─── POST /alerts/{execution_id} ──────────────────────────────────────────────

ALERT_SUMMARY = "Manually trigger a Slack alert for an execution"
ALERT_DESCRIPTION = (
    "Fetches the execution from Bolna, then posts a formatted alert to the configured Slack channel — "
    "regardless of the call's status. Useful for backfills or when the webhook didn't fire."
)
ALERT_RESPONSES = {
    200: {
        "description": "Alert sent.",
        "content": {
            "application/json": {
                "example": {
                    "sent": True,
                    "execution_id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
                    "status": "completed",
                }
            }
        },
    },
    404: {"description": "No execution exists with this id on Bolna."},
    502: {"description": "Bolna is unreachable, or Slack rejected the post."},
}


# ─── POST /webhook/bolna ──────────────────────────────────────────────────────

WEBHOOK_SUMMARY = "Bolna webhook receiver"
WEBHOOK_DESCRIPTION = (
    "Bolna calls this endpoint on every status change. The handler:\n\n"
    "1. Parses the payload (`CallExecutionResponse` schema).\n"
    "2. Skips the alert if the status indicates the call hasn't ended (`scheduled`, `queued`, `rescheduled`, `initiated`, `ringing`, `in-progress`, `canceled`).\n"
    "3. Otherwise posts a formatted attachment to the configured Slack channel.\n\n"
    "Always returns 200 OK so Bolna does not retry."
)
WEBHOOK_RESPONSES = {
    200: {
        "description": "Acknowledged. The Slack alert may or may not have been sent depending on `status`.",
        "content": {"application/json": {"example": {"received": True}}},
    }
}
WEBHOOK_OPENAPI_EXTRA = {
    "requestBody": {
        "description": (
            "Bolna posts the same payload shape as `GET /executions/{execution_id}` whenever a call's "
            "status changes. The handler always returns 200 — even on parse failure — so Bolna does not retry."
        ),
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/CallExecutionResponse"},
                "examples": {
                    "completed_short_call": {
                        "summary": "Completed call (transcript present)",
                        "value": {
                            "id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
                            "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
                            "status": "completed",
                            "transcript": "Agent: Hi! ...\nUser: Hello.\n...",
                            "telephony_data": {"duration": "42"},
                        },
                    },
                    "busy_no_transcript": {
                        "summary": "Recipient busy (no transcript)",
                        "value": {
                            "id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
                            "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
                            "status": "busy",
                            "transcript": None,
                            "telephony_data": {
                                "duration": "0.0",
                                "hangup_by": "Carrier",
                                "hangup_reason": "Call recipient was busy",
                            },
                        },
                    },
                    "in_progress_skipped": {
                        "summary": "In-progress (alert is skipped)",
                        "value": {
                            "id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
                            "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
                            "status": "in-progress",
                        },
                    },
                },
            }
        },
    }
}


# ─── GET /health ──────────────────────────────────────────────────────────────

HEALTH_SUMMARY = "Liveness probe"
HEALTH_DESCRIPTION = "Returns `{\"status\": \"ok\"}` if the process is up. No upstream calls."
HEALTH_RESPONSES = {200: {"content": {"application/json": {"example": {"status": "ok"}}}}}
