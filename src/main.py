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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting calling-agent service")
    bolna_provider = BolnaProvider()
    slack_provider = SlackProvider()

    app.state.bolna_provider = bolna_provider
    app.state.slack_provider = slack_provider
    app.state.call_service = CallService(bolna_provider)
    app.state.alert_service = AlertService(slack_provider)

    try:
        yield
    finally:
        logger.info("Shutting down calling-agent service")
        await bolna_provider.close()
        await slack_provider.close()


app = FastAPI(title="Calling Agent", lifespan=lifespan)
app.include_router(health_router)
app.include_router(calls_router)
app.include_router(alerts_router)
app.include_router(webhook_router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
