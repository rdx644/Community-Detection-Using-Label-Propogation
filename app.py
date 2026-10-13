"""Production launcher: a single process owns the expiring analysis store."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "reddit_communities.api:app",
        host=os.getenv("RACI_HOST", "127.0.0.1"),
        port=int(os.getenv("RACI_PORT", "8000")),
        workers=1,
        limit_concurrency=32,
        access_log=False,
    )
