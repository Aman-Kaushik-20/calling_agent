import httpx
from fastapi import APIRouter, HTTPException, Request, status

from src.utils.logger import logger
from src.utils.openapi import ALERT_DESCRIPTION, ALERT_RESPONSES, ALERT_SUMMARY

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Route that Fetches the execution from Bolna, then posts a formatted alert to the configured Slack channel.
@router.post(
    "/{execution_id}",
    summary=ALERT_SUMMARY,  # For Better OpenAPI SwaggerUI Docs
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

    try:
        await request.app.state.alert_service.send_call_ended_alert(execution)
    except Exception as e:
        logger.error(f"Slack send failed in manual alert | execution_id={execution_id} error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Slack send failed: {e}")

    return {
        "sent": True,
        "execution_id": str(execution.id),
        "status": execution.status.value if execution.status else None,
    }
