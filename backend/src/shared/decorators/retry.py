def retry(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise e
        return wrapper
    return decorator