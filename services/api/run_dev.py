"""Windows-safe local API entrypoint (psycopg needs SelectorEventLoop).

Uvicorn on Windows forces ProactorEventLoop, which breaks psycopg async.
This entrypoint pins Selector before uvicorn can override it.
"""

from __future__ import annotations

import asyncio
import sys


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # uvicorn may reassign Proactor — keep Selector instead
    asyncio.WindowsProactorEventLoopPolicy = asyncio.WindowsSelectorEventLoopPolicy  # type: ignore[misc,assignment]

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        loop="asyncio",
    )


if __name__ == "__main__":
    main()
