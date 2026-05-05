import asyncio

from src.models.bolna import ALERT_SKIP_STATUSES, CallExecutionResponse
from src.utils.logger import logger


# Fan a single execution out to every notifier concurrently.
# return_exceptions=True so one provider failing doesn't kill the others.
async def fanout(notifiers, execution: CallExecutionResponse) -> dict[str, str]:
    if not notifiers:
        return {}

    results = await asyncio.gather(
        *(n.send(execution) for n in notifiers),
        return_exceptions=True,
    )

    delivered: dict[str, str] = {}
    for n, r in zip(notifiers, results):
        if isinstance(r, Exception):
            logger.error(
                f"Notifier failed | provider={n.name} execution_id={execution.id} error={r!r}"
            )
            delivered[n.name] = f"error: {type(r).__name__}: {r}"
        else:
            delivered[n.name] = "ok"
    return delivered


# Webhook flow: skip in-flight statuses, otherwise fan out.
async def fanout_if_eligible(notifiers, execution: CallExecutionResponse) -> dict[str, str] | None:
    if execution.status is None or execution.status in ALERT_SKIP_STATUSES:
        logger.info(
            f"Skipping notifier fan-out | execution_id={execution.id} status={execution.status}"
        )
        return None
    return await fanout(notifiers, execution)
