"""
SentinelForge Worker Service
Polls for queued jobs and executes them using the tool executor.
Includes schedule polling and OpenTelemetry instrumentation.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("sentinelforge.worker")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sentinelforge_user:sentinelforge_password@localhost:5432/sentinelforge",
)
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "5"))
POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "5"))
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

# ── OpenTelemetry setup ──
_tracer = None
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    _resource = Resource.create(
        {SERVICE_NAME: "sentinelforge-worker", SERVICE_VERSION: "2.3.1"}
    )
    _provider = TracerProvider(resource=_resource)
    _exporter = OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")
    _provider.add_span_processor(BatchSpanProcessor(_exporter))
    trace.set_tracer_provider(_provider)
    _tracer = trace.get_tracer("sentinelforge.worker")
    logger.info("✅ OpenTelemetry tracing initialized for worker")
except Exception as e:
    logger.warning(f"OpenTelemetry init skipped for worker: {e}")
    # Provide a no-op tracer
    from contextlib import contextmanager

    class _NoOpSpan:
        def set_attribute(self, *a, **kw):
            pass

        def set_status(self, *a, **kw):
            pass

        def record_exception(self, *a, **kw):
            pass

    class _NoOpTracer:
        @contextmanager
        def start_as_current_span(self, name, **kw):
            yield _NoOpSpan()

    _tracer = _NoOpTracer()


async def process_job(pool: asyncpg.Pool, job_id: str):
    """Process a single queued attack run."""
    with _tracer.start_as_current_span(
        "process_job", attributes={"job.id": job_id}
    ) as span:
        logger.info(f"Processing job {job_id}")

        async with pool.acquire() as conn:
            # Mark as running
            await conn.execute(
                "UPDATE attack_runs SET status = 'running', started_at = $1 WHERE id = $2",
                datetime.now(timezone.utc),
                job_id,
            )

            # Get job details
            row = await conn.fetchrow("SELECT * FROM attack_runs WHERE id = $1", job_id)
            if not row:
                logger.error(f"Job {job_id} not found")
                span.set_attribute("job.error", "not_found")
                return

            scenario_id = row["scenario_id"]
            target_model = row["target_model"]
            config = row["config"] or {}
            span.set_attribute("job.scenario", scenario_id)
            span.set_attribute("job.target", target_model)

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
                    with _tracer.start_as_current_span(
                        f"execute_tool.{tool_name}",
                        attributes={
                            "tool.name": tool_name,
                            "tool.target": target_model,
                        },
                    ):
                        tool_result = executor.execute_tool(
                            tool_name, target=target_model, args=config
                        )
                        results["tools_executed"].append(
                            {
                                "tool": tool_name,
                                "success": tool_result.get("success", False),
                                "duration": tool_result.get("duration", 0),
                            }
                        )

                # Update as completed
                await conn.execute(
                    """UPDATE attack_runs
                       SET status = 'completed', progress = 1.0,
                           results = $1, completed_at = $2
                       WHERE id = $3""",
                    json.dumps(results),
                    datetime.now(timezone.utc),
                    job_id,
                )
                span.set_attribute("job.status", "completed")
                logger.info(f"Job {job_id} completed successfully")

            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                span.record_exception(e)
                span.set_attribute("job.status", "failed")
                await conn.execute(
                    """UPDATE attack_runs
                       SET status = 'failed', error_message = $1, completed_at = $2
                       WHERE id = $3""",
                    str(e),
                    datetime.now(timezone.utc),
                    job_id,
                )


async def check_schedules(pool: asyncpg.Pool):
    """Check for due schedules and create attack runs for them."""
    with _tracer.start_as_current_span("check_schedules"):
        try:
            from croniter import croniter
        except ImportError:
            return  # croniter not installed

        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, cron_expression, scenario_id, target_model,
                          config, user_id, compare_drift, baseline_id
                   FROM schedules
                   WHERE is_active = true AND next_run_at <= $1
                   FOR UPDATE SKIP LOCKED""",
                now,
            )

            for row in rows:
                schedule_id = row["id"]
                logger.info(f"Triggering schedule {schedule_id}")

                # Create a new attack run
                import uuid

                run_id = str(uuid.uuid4())
                config = row["config"] or {}

                await conn.execute(
                    """INSERT INTO attack_runs
                       (id, scenario_id, target_model, status, config, user_id, created_at)
                       VALUES ($1, $2, $3, 'queued', $4, $5, $6)""",
                    run_id,
                    row["scenario_id"],
                    row["target_model"],
                    json.dumps(config),
                    row["user_id"],
                    now,
                )

                # Compute next run time
                cron = croniter(row["cron_expression"], now)
                next_run = cron.get_next(datetime)

                await conn.execute(
                    """UPDATE schedules
                       SET last_run_at = $1, next_run_at = $2
                       WHERE id = $3""",
                    now,
                    next_run,
                    schedule_id,
                )

                logger.info(
                    f"Schedule {schedule_id}: created run {run_id}, next at {next_run}"
                )


async def poll_and_process(pool: asyncpg.Pool):
    """Poll for queued jobs and scheduled tasks, then process them."""
    while True:
        try:
            # Check scheduled tasks first
            try:
                await check_schedules(pool)
            except Exception as e:
                # Don't let schedule errors block job processing
                logger.warning(f"Schedule check error: {e}")

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
            pool = await asyncpg.create_pool(
                DATABASE_URL, min_size=2, max_size=WORKER_CONCURRENCY + 2
            )
            logger.info("✅ Connected to database")
            break
        except Exception:
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
