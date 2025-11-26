import asyncio


def silence_event_loop_closed(loop: asyncio.AbstractEventLoop, context: dict[str, any]) -> None:
    """Custom exception handler to silence the specific 'WinError 64' on Windows shutdown."""
    exception = context.get("exception")
    
    # ? WinError 64: "The specified network name is no longer available"
    if isinstance(exception, OSError) and getattr(exception, "winerror", 0) == 64: return
    
    # ? ConnectionResetError: Often happens alongside the socket disconnect
    if isinstance(exception, ConnectionResetError): return

    # ? Pass everything else to the default handler
    loop.default_exception_handler(context)
    