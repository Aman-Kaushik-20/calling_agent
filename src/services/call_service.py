from src.models.bolna import CallExecutionResponse, CallRequestModel, CallResponseModel
from src.providers.bolna import BolnaProvider
from src.utils.logger import logger

# Service to Schedule call or Get status check of the calls(it uses provider of bolna)
class CallService:
    def __init__(self, bolna: BolnaProvider) -> None:
        self.bolna = bolna

    async def initiate_call(self, call_params: CallRequestModel) -> CallResponseModel:
        logger.info(f"CallService.initiate_call | agent_id={call_params.agent_id}")
        return await self.bolna.make_call(call_params)

    async def get_execution(self, execution_id: str) -> CallExecutionResponse:
        logger.info(f"CallService.get_execution | execution_id={execution_id}")
        return await self.bolna.get_execution(execution_id)
