
import asyncio
import logging

from app.main import app as fastapi_app
from executors.nautilus_executor import BacktestExecutor
from data.data_fetcher import DataFetcher
from shared.config import settings

import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run all services concurrently."""
    logger.info("Starting all services...")

    # Start FastAPI app
    config = uvicorn.Config(fastapi_app, host=settings.BACKTEST_SERVICE_HOST, port=settings.BACKTEST_SERVICE_PORT, log_level="info")
    server = uvicorn.Server(config)
    fastapi_task = asyncio.create_task(server.serve())

    # Start Backtest Executor
    backtest_executor = BacktestExecutor()
    executor_task = asyncio.create_task(asyncio.to_thread(backtest_executor.start))

    # Start Data Fetcher
    data_fetcher = DataFetcher()
    fetcher_task = asyncio.create_task(data_fetcher.start())

    await asyncio.gather(fastapi_task, executor_task, fetcher_task)

if __name__ == "__main__":
    asyncio.run(main())
