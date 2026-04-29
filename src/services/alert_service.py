from src.config import settings
from src.models.bolna import ALERT_SKIP_STATUSES, STATUS_COLORS, CallExecutionResponse, CallStatus
from src.models.slack import SlackAttachment, SlackPostMessageRequest
from src.providers.slack import SlackProvider
from src.utils.logger import logger


class AlertService:
    def __init__(self, slack: SlackProvider) -> None:
        self.slack = slack
        self.channel = settings.slack_alert_channel

    def _format_duration(self, raw: str | None) -> str:
        if not raw:
            return "unknown"
        try:
            seconds = int(float(raw))
        except (TypeError, ValueError):
            return str(raw)
        if seconds < 60:
            return f"{seconds} seconds"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"

    def _build_attachment(self, execution: CallExecutionResponse) -> SlackAttachment:
        duration_raw = execution.telephony_data.duration if execution.telephony_data else None
        transcript = execution.transcript or "_No transcript available_"
        status_value = execution.status.value if execution.status else "unknown"

        body = (
            f"*Call ID:* `{execution.id}`\n"
            f"*Agent ID:* `{execution.agent_id}`\n"
            f"*Duration:* {self._format_duration(duration_raw)}\n"
            f"*Status:* {status_value}\n\n"
            f"*Transcript:*\n{transcript}"
        )
        color = STATUS_COLORS.get(execution.status, "#1d9bd1") if execution.status else "#1d9bd1"

        return SlackAttachment(
            text=body,
            fallback=f"Call {execution.id} ended ({status_value})",
            color=color,
        )

    async def send_call_ended_alert(self, execution: CallExecutionResponse) -> None:
        message = SlackPostMessageRequest(
            channel=self.channel,
            text=f"📞 Call Ended — `{execution.id}`",
            attachments=[self._build_attachment(execution)],
        )
        await self.slack.post_message(message)

    async def alert_if_eligible(self, execution: CallExecutionResponse) -> bool:
        if execution.status is None or execution.status in ALERT_SKIP_STATUSES:
            logger.info(f"Skipping Slack alert | execution_id={execution.id} status={execution.status}")
            return False
        try:
            await self.send_call_ended_alert(execution)
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert | execution_id={execution.id} error={e!r}")
            return False
