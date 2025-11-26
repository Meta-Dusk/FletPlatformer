import asyncio


def attempt_cancel(task: asyncio.Task):
    """
    Cancels task if it's not `None` and is currently running.
    """
    if task and not task.done(): task.cancel()