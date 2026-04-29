import httpx
from fastapi import APIRouter, Body, HTTPException, Request, status

from src.models.bolna import CallExecutionResponse, CallRequestModel, CallResponseModel
from src.utils.logger import logger
from src.utils.openapi import (
    CALL_REQUEST_EXAMPLES,
    GET_CALL_DESCRIPTION,
    GET_CALL_RESPONSES,
    GET_CALL_SUMMARY,
    MAKE_CALL_DESCRIPTION,
    MAKE_CALL_RESPONSES,
    MAKE_CALL_SUMMARY,
)

router = APIRouter(prefix="/calls", tags=["calls"])

# Route that Forwards the request to Bolna's `POST /call` and returns the queued `execution_id

@router.post(
    "",
    response_model=CallResponseModel,
    summary=MAKE_CALL_SUMMARY, # For Better OpenAPI SwaggerUI Docs
    description=MAKE_CALL_DESCRIPTION,
    responses=MAKE_CALL_RESPONSES,
)
async def make_call(
    request: Request,
    payload: CallRequestModel = Body(..., openapi_examples=CALL_REQUEST_EXAMPLES),
) -> CallResponseModel:
    try:
        return await request.app.state.call_service.initiate_call(payload)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        logger.error(f"Bolna transport error in make_call | error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bolna upstream error")

# Route that Fetch a call's execution details
@router.get(
    "/{execution_id}",
    response_model=CallExecutionResponse,
    summary=GET_CALL_SUMMARY,
    description=GET_CALL_DESCRIPTION, # For Better OpenAPI SwaggerUI Docs
    responses=GET_CALL_RESPONSES,
)
async def get_call(execution_id: str, request: Request) -> CallExecutionResponse:
    try:
        return await request.app.state.call_service.get_execution(execution_id)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        logger.error(f"Bolna transport error in get_call | error={e!r}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bolna upstream error")
