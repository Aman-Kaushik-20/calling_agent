import httpx
from fastapi import APIRouter, HTTPException, Request, status

from src.models.bolna import (
    CallExecutionResponse,
    CallRequestModel,
    CallResponseModel,
)
from src.services.call_service import CallService
from src.utils.logger import logger

router = APIRouter(prefix="/calls", tags=["calls"])


def _service(request: Request) -> CallService:
    return request.app.state.call_service


@router.post("", response_model=CallResponseModel, status_code=status.HTTP_200_OK)
async def make_call(payload: CallRequestModel, request: Request) -> CallResponseModel:
    service = _service(request)
    try:
        return await service.initiate_call(payload)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        logger.error(f"Bolna transport error in make_call | error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bolna upstream error")


@router.get("/{execution_id}", response_model=CallExecutionResponse)
async def get_call(execution_id: str, request: Request) -> CallExecutionResponse:
    service = _service(request)
    try:
        return await service.get_execution(execution_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        logger.error(f"Bolna transport error in get_call | error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bolna upstream error")
