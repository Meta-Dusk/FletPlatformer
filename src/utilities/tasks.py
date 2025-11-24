import asyncio


def attempt_cancel(task: asyncio.Task):
    if task and not task.done(): task.cancel()