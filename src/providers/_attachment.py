"""Shared Slack-shaped attachment builder.

Slack and Mattermost both consume this exact JSON shape, so the formatter
lives here and is imported by both providers. Discord and ClickUp reuse the
title and duration helpers but build their own bodies.
"""

from src.models.bolna import STATUS_COLORS, CallExecutionResponse, CallStatus
from src.models.slack import SlackAttachment, SlackPostMessageRequest


# Per-status title prefix.
STATUS_TITLES: dict[CallStatus, str] = {
    CallStatus.COMPLETED: "📞 Call Ended",
    CallStatus.CALL_DISCONNECTED: "📴 Call Disconnected",
    CallStatus.BUSY: "📵 Recipient Busy",
    CallStatus.NO_ANSWER: "🔕 No Answer",
    CallStatus.FAILED: "❌ Call Failed",
    CallStatus.ERROR: "⚠️ Call Error",
    CallStatus.STOPPED: "⏹️ Call Stopped",
    CallStatus.BALANCE_LOW: "💸 Balance Low",
}


def _format_duration(raw: str | None) -> str:
    if not raw:
        return "unknown"
    try:
        seconds = int(float(raw))
    except (TypeError, ValueError):
        return str(raw)
    if seconds < 60:
        return f"{seconds} seconds"
    return f"{seconds // 60}m {seconds % 60}s"


def _color_for(execution: CallExecutionResponse) -> str:
    if execution.status is None:
        return "#1d9bd1"
    return STATUS_COLORS.get(execution.status, "#1d9bd1")


def title_for(execution: CallExecutionResponse) -> str:
    if execution.status is None:
        return "📞 Call Ended"
    return STATUS_TITLES.get(execution.status, f"📞 Call {execution.status.value}")


def build_body(execution: CallExecutionResponse) -> str:
    duration_raw = execution.telephony_data.duration if execution.telephony_data else None
    transcript = execution.transcript or "_No transcript available_"
    status_value = execution.status.value if execution.status else "unknown"

    return (
        f"*Call ID:* `{execution.id}`\n"
        f"*Agent ID:* `{execution.agent_id}`\n"
        f"*Duration:* {_format_duration(duration_raw)}\n"
        f"*Status:* {status_value}\n\n"
        f"*Transcript:*\n{transcript}"
    )


def build_message(channel: str, execution: CallExecutionResponse) -> SlackPostMessageRequest:
    title = title_for(execution)
    return SlackPostMessageRequest(
        channel=channel,
        text=f"{title} — `{execution.id}`",
        attachments=[
            SlackAttachment(
                text=build_body(execution),
                fallback=f"{title} — {execution.id}",
                color=_color_for(execution),
            )
        ],
    )
