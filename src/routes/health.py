from fastapi import APIRouter

from src.utils.openapi import HEALTH_DESCRIPTION, HEALTH_RESPONSES, HEALTH_SUMMARY

router = APIRouter()


@router.get(
    "/health",
    tags=["health"],
    summary=HEALTH_SUMMARY,
    description=HEALTH_DESCRIPTION,
    responses=HEALTH_RESPONSES,
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
