import httpx

from src.config import settings
from src.models.bolna import STATUS_COLORS, CallExecutionResponse
from src.providers._attachment import _format_duration, title_for
from src.utils.logger import logger


# Convert Slack-style "#rrggbb" colour to Discord embed integer.
def _hex_to_int(color: str) -> int:
    return int(color.lstrip("#"), 16)


def _color_for(execution: CallExecutionResponse) -> int:
    if execution.status is None:
        return _hex_to_int("#1d9bd1")
    return _hex_to_int(STATUS_COLORS.get(execution.status, "#1d9bd1"))


def _build_embed(execution: CallExecutionResponse) -> dict:
    fields: list[dict] = []

    if execution.agent_id:
        fields.append({"name": "Agent ID", "value": f"`{execution.agent_id}`", "inline": True})

    telephony = execution.telephony_data
    if telephony and (telephony.from_number or telephony.to_number):
        fields.append(
            {
                "name": "From → To",
                "value": f"{telephony.from_number or '?'} → {telephony.to_number or '?'}",
                "inline": True,
            }
        )

    if execution.status:
        fields.append({"name": "Status", "value": execution.status.value, "inline": True})

    duration_raw = telephony.duration if telephony else None
    if duration_raw:
        fields.append(
            {"name": "Duration", "value": _format_duration(duration_raw), "inline": True}
        )

    if telephony and telephony.hangup_reason:
        fields.append(
            {"name": "Hangup Reason", "value": f"`{telephony.hangup_reason}`", "inline": True}
        )

    description_parts: list[str] = []
    transcript = execution.transcript
    if transcript:
        # Discord embed description max is 4096 chars; cap for safety.
        transcript = transcript[:3500]
        description_parts.append(f"**Transcript**\n```\n{transcript}\n```")
    else:
        description_parts.append("_No transcript available_")

    return {
        "title": f"{title_for(execution)} — {execution.id}",
        "color": _color_for(execution),
        "fields": fields,
        "description": "\n\n".join(description_parts) if description_parts else None,
    }


# Discord notifier — webhook URL is the only credential. POSTs an `embeds` array.
class DiscordProvider:
    name = "discord"

    def __init__(self) -> None:
        self.webhook_url = settings.discord_webhook_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            # Identifiable User-Agent — Discord's edge (Cloudflare) flags the
            # default python-httpx UA from cloud IPs as bot traffic, which
            # surfaces as HTML 429s with multi-minute retry_after.
            headers={
                "Content-Type": "application/json",
                "User-Agent": "calling-agent/0.2 (bolna)",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def send(self, execution: CallExecutionResponse) -> None:
        embed = _build_embed(execution)
        # Discord rejects null fields; strip them out.
        embed = {k: v for k, v in embed.items() if v is not None}
        payload = {"embeds": [embed]}

        logger.info(f"Discord post | execution_id={execution.id}")
        response = await self.client.post(self.webhook_url, json=payload)
        if response.status_code >= 400:
            retry_after = response.headers.get("x-ratelimit-reset-after") or response.headers.get(
                "retry-after"
            )
            logger.error(
                f"Discord post failed | execution_id={execution.id} status={response.status_code} "
                f"retry_after={retry_after} body={response.text[:500]}"
            )
        response.raise_for_status()
