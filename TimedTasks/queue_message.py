import asyncio
import threading
from queue import Queue

queue = Queue()


class MessageThread(threading.Thread):

    def run(self) -> None:
        global queue
        while True:
            if queue.qsize() > 0:
                data = queue.get()
                func = data.get("func")
                args = data.get("args")
                print(func)
                print(args)
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(func(args[0]))


for i in range(3):
    p = MessageThread()
    p.start()



