import asyncio


def attempt_cancel(task: asyncio.Task):
    """
    Cancels task if it's not `None` and is currently running.
    """
    if task and not task.done(): task.cancel()
    
async def cancellable_wait(duration: float, cancel_event: asyncio.Event = None):
    """
    Waits for 'duration' seconds, OR until 'cancel_event' is set.
    Returns True if time finished, False if cancelled/interrupted.
    """
    if cancel_event is None:
        await asyncio.sleep(duration)
        return True

    # Create a task for the timer
    sleep_task = asyncio.create_task(asyncio.sleep(duration))
    # Create a task for the cancel event
    cancel_task = asyncio.create_task(cancel_event.wait())

    # Wait for whichever happens first
    done, pending = await asyncio.wait(
        [sleep_task, cancel_task], 
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cleanup: Cancel the one that didn't finish
    for task in pending:
        task.cancel()

    # If the sleep task is done, the time ran out normally
    if sleep_task in done:
        return True
    
    # Otherwise, the cancel event fired
    return False