def async_sleep(seconds: float) -> None:
    import asyncio
    asyncio.sleep(seconds)

def async_map(coroutines):
    import asyncio
    return asyncio.gather(*coroutines)

def async_run(coroutine):
    import asyncio
    return asyncio.run(coroutine)