from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.models.bolna import CallExecutionResponse
from src.utils.logger import logger
from src.utils.openapi import (
    WEBHOOK_DESCRIPTION,
    WEBHOOK_OPENAPI_EXTRA,
    WEBHOOK_RESPONSES,
    WEBHOOK_SUMMARY,
)

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Bolna calls this endpoint on every status change and after filtering status type , this route posts a formatted attachment to the configured Slack channel

@router.post(
    "/bolna",
    status_code=status.HTTP_200_OK,
    summary=WEBHOOK_SUMMARY, # For Better OpenAPI SwaggerUI Docs
    description=WEBHOOK_DESCRIPTION,
    openapi_extra=WEBHOOK_OPENAPI_EXTRA,
    responses=WEBHOOK_RESPONSES,
)
async def bolna_webhook(request: Request) -> JSONResponse:
    raw = await request.body()
    try:
        execution = CallExecutionResponse.model_validate_json(raw)
    except Exception as e:
        logger.error(f"Bolna webhook payload could not be parsed | error={e!r} body={raw[:500]!r}")
        return JSONResponse({"received": True})

    logger.info(f"Bolna webhook received | execution_id={execution.id} status={execution.status}")
    await request.app.state.alert_service.alert_if_eligible(execution)
    return JSONResponse({"received": True})
