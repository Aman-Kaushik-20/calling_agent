import httpx

from src.config import settings
from src.models.bolna import CallExecutionResponse
from src.providers._attachment import _format_duration, title_for
from src.utils.logger import logger


# ClickUp comments are plain text (no rich shape supported on this endpoint),
# so we flatten the same fields Slack/Discord show into a multi-line string.
def _build_comment(execution: CallExecutionResponse) -> str:
    lines = [f"{title_for(execution)} — {execution.id}", ""]

    if execution.agent_id:
        lines.append(f"Agent: {execution.agent_id}")

    telephony = execution.telephony_data
    if telephony and (telephony.from_number or telephony.to_number):
        lines.append(f"From → To: {telephony.from_number or '?'} → {telephony.to_number or '?'}")
    if execution.status:
        lines.append(f"Status: {execution.status.value}")
    duration_raw = telephony.duration if telephony else None
    if duration_raw:
        lines.append(f"Duration: {_format_duration(duration_raw)}")
    if telephony and telephony.hangup_reason:
        lines.append(f"Hangup Reason: {telephony.hangup_reason}")
    if telephony and telephony.hangup_by:
        lines.append(f"Hangup By: {telephony.hangup_by}")

    transcript = execution.transcript
    if transcript:
        lines.extend(["", "Transcript:", transcript])
    else:
        lines.extend(["", "Transcript: (none)"])

    return "\n".join(lines)


# ClickUp notifier — appends a comment on the configured task for every alert.
class ClickUpProvider:
    name = "clickup"
    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self) -> None:
        self.task_id = settings.clickup_task_id
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(15.0, connect=5.0),
            # ClickUp uses the raw token in Authorization, not "Bearer ...".
            headers={
                "Authorization": settings.clickup_api_token,
                "Content-Type": "application/json",
                "User-Agent": "calling-agent/0.2 (bolna)",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def send(self, execution: CallExecutionResponse) -> None:
        payload = {
            "comment_text": _build_comment(execution),
            "notify_all": False,
        }
        logger.info(f"ClickUp post | execution_id={execution.id} task={self.task_id}")
        response = await self.client.post(f"/task/{self.task_id}/comment", json=payload)
        if response.status_code >= 400:
            # ClickUp returns {"err":"...","ECODE":"..."} — log it so misconfigurations are obvious.
            logger.error(
                f"ClickUp post failed | execution_id={execution.id} task={self.task_id} "
                f"status={response.status_code} body={response.text[:500]}"
            )
        response.raise_for_status()
