from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.providers.bolna import BolnaProvider
from src.providers.slack import SlackProvider
from src.routes.alerts import router as alerts_router
from src.routes.calls import router as calls_router
from src.routes.health import router as health_router
from src.routes.webhook import router as webhook_router
from src.services.alert_service import AlertService
from src.services.call_service import CallService
from src.utils.logger import logger
from src.utils.openapi import API_DESCRIPTION, OPENAPI_TAGS



# Context Manager - for building provider/service objects once and stash on app.state so handlers reuse them. Better Performannce and low runtime latency.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting calling-agent service")
    bolna_provider = BolnaProvider()
    slack_provider = SlackProvider()

    app.state.bolna_provider = bolna_provider
    app.state.slack_provider = slack_provider
    app.state.call_service = CallService(bolna_provider) # Bolna AI Service Object
    app.state.alert_service = AlertService(slack_provider) # Slack Alert Service Object

    try:
        yield
    finally:
        logger.info("Shutting down calling-agent service")
        await bolna_provider.close()
        await slack_provider.close()


app = FastAPI(
    title="Calling Agent",
    description=API_DESCRIPTION, # For Better OpenAPI SwaggerUI Docs
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS, # For Better OpenAPI SwaggerUI Docs
    lifespan=lifespan,
)
app.include_router(health_router) # Health Check Router
app.include_router(calls_router) # Route for Scheduling Calls from available agents
app.include_router(alerts_router) # Route for Slack ALert via execution_id
app.include_router(webhook_router) # Route for Webhook Support for Slack ALert via Bolna AI Analytics Integration


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
