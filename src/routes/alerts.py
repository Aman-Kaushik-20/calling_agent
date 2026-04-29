import httpx
from fastapi import APIRouter, HTTPException, Request, status

from src.services.alert_service import AlertService
from src.services.call_service import CallService
from src.utils.logger import logger

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _services(request: Request) -> tuple[CallService, AlertService]:
    return request.app.state.call_service, request.app.state.alert_service


@router.post("/{execution_id}", status_code=status.HTTP_200_OK)
async def alert_for_execution(execution_id: str, request: Request) -> dict[str, object]:
    call_service, alert_service = _services(request)

    try:
        execution = await call_service.get_execution(execution_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        logger.error(f"Bolna transport error in manual alert | execution_id={execution_id} error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bolna upstream error")

    try:
        await alert_service.send_call_ended_alert(execution)
    except Exception as e:
        logger.error(f"Slack send failed in manual alert | execution_id={execution_id} error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Slack send failed: {e}")

    return {
        "sent": True,
        "execution_id": str(execution.id),
        "status": execution.status.value if execution.status else None,
    }
