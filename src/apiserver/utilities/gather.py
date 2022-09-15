from typing import Coroutine, Callable

from anyio import create_memory_object_stream, create_task_group


async def result_task(task, send_stream):
    result = await task()
    await send_stream.send(result)


# Simple tests seem to indicate these are not faster for just two DB calls
async def gather(tasks: list[Callable[[], Coroutine]]):
    send_stream, receive_stream = create_memory_object_stream()
    task_num = len(tasks)
    results = []
    async with create_task_group() as tg:
        for task in tasks:
            tg.start_soon(result_task, task, send_stream)
        async with receive_stream:
            async for item in receive_stream:
                results.append(item)
                if len(results) == task_num:
                    await send_stream.aclose()
    return results
