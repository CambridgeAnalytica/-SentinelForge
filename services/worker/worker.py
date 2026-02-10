"""
SentinelForge Worker Service
Polls for queued jobs and executes them using the tool executor.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("sentinelforge.worker")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sentinelforge_user:sentinelforge_password@localhost:5432/sentinelforge"
)
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "5"))
POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "5"))


async def process_job(pool: asyncpg.Pool, job_id: str):
    """Process a single queued attack run."""
    logger.info(f"Processing job {job_id}")

    async with pool.acquire() as conn:
        # Mark as running
        await conn.execute(
            "UPDATE attack_runs SET status = 'running', started_at = $1 WHERE id = $2",
            datetime.now(timezone.utc), job_id
        )

        # Get job details
        row = await conn.fetchrow("SELECT * FROM attack_runs WHERE id = $1", job_id)
        if not row:
            logger.error(f"Job {job_id} not found")
            return

        scenario_id = row["scenario_id"]
        target_model = row["target_model"]
        config = row["config"] or {}

        try:
            # Import and use executor
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from tools.executor import ToolExecutor
            executor = ToolExecutor()

            results = {
                "scenario": scenario_id,
                "target": target_model,
                "tools_executed": [],
                "findings": [],
            }

            # Execute each tool in config
            tools_to_run = config.get("tools", [scenario_id])
            for tool_name in tools_to_run:
                tool_result = executor.execute_tool(
                    tool_name, target=target_model, args=config
                )
                results["tools_executed"].append({
                    "tool": tool_name,
                    "success": tool_result.get("success", False),
                    "duration": tool_result.get("duration", 0),
                })

            # Update as completed
            import json
            await conn.execute(
                """UPDATE attack_runs
                   SET status = 'completed', progress = 100.0,
                       results = $1, completed_at = $2
                   WHERE id = $3""",
                json.dumps(results),
                datetime.now(timezone.utc),
                job_id,
            )
            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await conn.execute(
                """UPDATE attack_runs
                   SET status = 'failed', error_message = $1, completed_at = $2
                   WHERE id = $3""",
                str(e),
                datetime.now(timezone.utc),
                job_id,
            )


async def poll_and_process(pool: asyncpg.Pool):
    """Poll for queued jobs and process them."""
    while True:
        try:
            async with pool.acquire() as conn:
                # Get queued jobs (with advisory lock to prevent duplicates)
                rows = await conn.fetch(
                    """SELECT id FROM attack_runs
                       WHERE status = 'queued'
                       ORDER BY created_at ASC
                       LIMIT $1
                       FOR UPDATE SKIP LOCKED""",
                    WORKER_CONCURRENCY,
                )

                if rows:
                    logger.info(f"Found {len(rows)} queued jobs")
                    tasks = [process_job(pool, row["id"]) for row in rows]
                    await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Poll error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def main():
    """Worker main entry point."""
    logger.info(f"🔧 SentinelForge Worker starting (concurrency={WORKER_CONCURRENCY})")

    # Wait for database
    for attempt in range(30):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=WORKER_CONCURRENCY + 2)
            logger.info("✅ Connected to database")
            break
        except Exception as e:
            logger.warning(f"Waiting for database... ({attempt+1}/30)")
            await asyncio.sleep(2)
    else:
        logger.error("Failed to connect to database after 30 attempts")
        sys.exit(1)

    try:
        await poll_and_process(pool)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
