"""
worker.py — Job processor for the OS Troubleshooting Lab.

Reads jobs from the Redis queue and writes results to PostgreSQL.

BUGS INJECTED (do not show to students):
  1. _inefficient_checksum() uses a Python-level loop to compute a simple
     checksum instead of using hashlib. This burns CPU unnecessarily and
     is visible in top/htop as sustained high CPU on this process.
  2. Logging is set to DEBUG with no rotation. Every job produces ~10
     debug lines. Under load this fills /var/log/app/worker.log fast.
"""

import redis
import psycopg2
import json
import time
import logging
import os
import random

# ── Logging setup ────────────────────────────────────────────────────────────
# BUG #2: DEBUG level + no rotation handler = disk fills up under load
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("worker")

# ── Config ───────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "192.168.56.10")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DB_HOST    = os.getenv("DB_HOST",    "192.168.56.12")
DB_PORT    = int(os.getenv("DB_PORT", 5432))
DB_NAME    = os.getenv("DB_NAME",    "labdb")
DB_USER    = os.getenv("DB_USER",    "labuser")
DB_PASS    = os.getenv("DB_PASS",    "labpass")
QUEUE_NAME = "job_queue"


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER, password=DB_PASS,
        connect_timeout=5
    )


def _inefficient_checksum(data: str) -> int:
    """
    BUG #1 — CPU SPIKE
    Computes a checksum by iterating character by character in pure Python.
    For large payloads this loop runs millions of iterations, pegging the CPU.
    The correct implementation would be: hashlib.md5(data.encode()).hexdigest()
    """
    log.debug("Starting checksum computation for %d bytes", len(data))
    result = 0
    for _ in range(5):          # repeat 5x to simulate "heavy processing"
        for ch in data:
            result = (result * 31 + ord(ch)) & 0xFFFFFFFF
    log.debug("Checksum result: %d", result)
    return result


def process_job(job: dict) -> dict:
    """Simulate processing a job. Returns result metadata."""
    job_id  = job["job_id"]
    payload = job.get("payload", "")

    log.debug("[%s] Received job, payload length=%d", job_id, len(payload))
    log.debug("[%s] Validating payload fields...", job_id)

    start = time.time()

    # CPU-intensive checksum (the bug)
    checksum = _inefficient_checksum(payload)

    # Simulate variable work duration
    time.sleep(random.uniform(0.05, 0.15))

    duration_ms = int((time.time() - start) * 1000)
    output = f"processed:checksum={checksum}:duration={duration_ms}ms"

    log.debug("[%s] Job complete in %dms", job_id, duration_ms)
    log.debug("[%s] Output: %s", job_id, output)
    return {"output": output, "duration_ms": duration_ms}


def save_result(conn, job_id: str, result: dict):
    with conn.cursor() as cur:
        # Update job status
        cur.execute(
            "UPDATE jobs SET status='done', updated_at=NOW() WHERE job_id=%s",
            (job_id,)
        )
        # Insert result — no index on job_id or created_at in this table
        cur.execute(
            "INSERT INTO results (job_id, output, duration_ms) VALUES (%s, %s, %s)",
            (job_id, result["output"], result["duration_ms"])
        )
    conn.commit()


def main():
    log.info("Worker starting up...")
    log.info("Connecting to Redis at %s:%d", REDIS_HOST, REDIS_PORT)

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    log.info("Connecting to PostgreSQL at %s:%d", DB_HOST, DB_PORT)
    db_conn = None

    while True:
        try:
            if db_conn is None or db_conn.closed:
                db_conn = get_db_connection()
                log.info("PostgreSQL connection established")

            log.debug("Waiting for jobs on queue '%s'...", QUEUE_NAME)
            item = r.blpop(QUEUE_NAME, timeout=5)

            if item is None:
                log.debug("No jobs in queue, polling again...")
                continue

            _, raw = item
            job = json.loads(raw)
            job_id = job.get("job_id", "unknown")

            log.info("[%s] Processing job...", job_id)
            result = process_job(job)
            save_result(db_conn, job_id, result)
            log.info("[%s] Saved result to database", job_id)

        except redis.exceptions.ConnectionError as e:
            log.error("Redis connection error: %s — retrying in 5s", e)
            time.sleep(5)

        except psycopg2.OperationalError as e:
            log.error("PostgreSQL error: %s — retrying in 5s", e)
            db_conn = None
            time.sleep(5)

        except Exception as e:
            log.error("Unexpected error: %s", e, exc_info=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
