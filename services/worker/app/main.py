"""Taskiq worker entrypoint — Phase 1 keeps process healthy."""

from __future__ import annotations

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("crimelens.worker")


async def main() -> None:
    logger.info("worker_starting phase=1")
    try:
        while True:
            logger.info("worker_heartbeat phase=1")
            await asyncio.sleep(30)
    finally:
        logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
