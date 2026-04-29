import httpx

from src.config import settings
from src.models.bolna import (
    CallExecutionResponse,
    CallRequestModel,
    CallResponseModel,
    ErrorResponse,
)
from src.utils.logger import logger

# Specefic Error Response Schema we get from Bolna API 
def _format_bolna_error(response: httpx.Response) -> str:
    try:
        err = ErrorResponse.model_validate_json(response.text)
        return f"code={err.error} message={err.message}"
    except Exception:
        return f"body={response.text}"

# Provider Class for Bolna AI - 2 main functions-
# 1. Schedule Calls
# 2. Get Call Execution Result
class BolnaProvider:
    def __init__(self) -> None:
        self.bolna_url = settings.bolna_base_url.rstrip("/")
        self.api_key = settings.bolna_api_key
        self.client = httpx.AsyncClient(
            base_url=self.bolna_url,
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        ) # Initialize client before-hand so runtime latency is low

    async def close(self) -> None:
        await self.client.aclose()

    async def make_call(self, call_params: CallRequestModel) -> CallResponseModel:
        payload = call_params.model_dump(
            mode="json",
            exclude_none=True,
            exclude={"date", "time", "timezone"},
        )

        logger.info(
            f"Initiating Bolna call | agent_id={call_params.agent_id} "
            f"to={call_params.recipient_phone_number} scheduled_at={payload.get('scheduled_at')}"
        )

        try:
            response = await self.client.post("/call", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Bolna /call failed | agent_id={call_params.agent_id} "
                f"status={e.response.status_code} {_format_bolna_error(e.response)}"
            )
            raise
        except httpx.HTTPError as e:
            logger.error(f"Bolna /call transport error | agent_id={call_params.agent_id} error={e!r}")
            raise

        data = response.json()
        logger.info(
            f"Bolna call queued | agent_id={call_params.agent_id} "
            f"execution_id={data.get('execution_id')} status={data.get('status')}"
        )
        return CallResponseModel.model_validate(data)

    async def get_execution(self, execution_id: str) -> CallExecutionResponse:
        logger.info(f"Fetching Bolna execution | execution_id={execution_id}")

        try:
            response = await self.client.get(f"/executions/{execution_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Bolna /executions failed | execution_id={execution_id} "
                f"status={e.response.status_code} {_format_bolna_error(e.response)}"
            )
            raise
        except httpx.HTTPError as e:
            logger.error(f"Bolna /executions transport error | execution_id={execution_id} error={e!r}")
            raise

        return CallExecutionResponse.model_validate(response.json())
