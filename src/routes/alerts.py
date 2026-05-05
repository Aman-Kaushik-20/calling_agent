import httpx
from fastapi import APIRouter, HTTPException, Request, status

from src.services.notifier import fanout
from src.utils.logger import logger
from src.utils.openapi import ALERT_DESCRIPTION, ALERT_RESPONSES, ALERT_SUMMARY

router = APIRouter(prefix="/alerts", tags=["alerts"])


# Manual back-fill: fetch the execution from Bolna, then fan it out to every
# enabled notifier (Slack / Discord / Mattermost / ClickUp). Always sends —
# the eligibility filter is only applied to the live webhook.
@router.post(
    "/{execution_id}",
    summary=ALERT_SUMMARY,
    description=ALERT_DESCRIPTION,
    responses=ALERT_RESPONSES,
)
async def alert_for_execution(execution_id: str, request: Request) -> dict[str, object]:
    try:
        execution = await request.app.state.call_service.get_execution(execution_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        logger.error(f"Bolna transport error in manual alert | execution_id={execution_id} error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bolna upstream error")

    delivered = await fanout(request.app.state.notifiers, execution)

    return {
        "sent": True,
        "execution_id": str(execution.id),
        "status": execution.status.value if execution.status else None,
        "delivered": delivered,
    }
