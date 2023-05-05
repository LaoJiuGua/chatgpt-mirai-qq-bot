import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler

aioscheduler = AsyncIOScheduler()

aioscheduler.start()

# if __name__ == '__main__':
#     aioscheduler.add_job(func=task, trigger="interval", seconds=10)
#     aioscheduler.start()
#     print(123)