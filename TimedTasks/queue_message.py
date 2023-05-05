import asyncio
import threading

n = 10
queue = asyncio.Queue()


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


async def producer(data):
    global queue
    await queue.put(data)


async def consumer():
    global queue
    while True:
        if queue.qsize() > 0:
            data = await queue.get()
            func = data.get("func")
            args = data.get("args")
            print(func)
            print(args)
            await func(args[0])


def thread_main():
    new_loop = asyncio.new_event_loop()  # 在当前线程下创建时间循环，（未启用），在start_loop里面启动它
    t = threading.Thread(target=start_loop, args=(new_loop,))  # 通过当前线程开启新的线程去启动事件循环
    t1 = threading.Thread(target=start_loop, args=(new_loop,))  # 通过当前线程开启新的线程去启动事件循环
    t2 = threading.Thread(target=start_loop, args=(new_loop,))  # 通过当前线程开启新的线程去启动事件循环
    t.start()
    t1.start()
    t2.start()
    asyncio.run_coroutine_threadsafe(consumer(), new_loop)  # 这几个是关键，代表在新线程中事件循环不断“游走”执行
    asyncio.run_coroutine_threadsafe(consumer(), new_loop)  # 这几个是关键，代表在新线程中事件循环不断“游走”执行
    asyncio.run_coroutine_threadsafe(consumer(), new_loop)  # 这几个是关键，代表在新线程中事件循环不断“游走”执行

