import httpx
from fastapi import APIRouter, HTTPException, Request, status

from src.utils.logger import logger

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/{execution_id}")
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
