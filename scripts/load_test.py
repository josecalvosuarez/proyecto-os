#!/usr/bin/env python3
"""
load_test.py — Generates continuous job load for the OS Troubleshooting Lab.

Run this from your HOST machine (Windows) after `vagrant up`:
    python scripts/load_test.py

Requirements on host:
    pip install redis

The script pushes jobs to the Redis queue on vm-broker (192.168.56.10).
Workers on vm-worker pick them up and write results to vm-db.

Press Ctrl+C to stop.
"""

import redis
import json
import uuid
import time
import random
import sys
import argparse
from datetime import datetime

REDIS_HOST = "192.168.56.10"
REDIS_PORT = 6379
QUEUE_NAME = "job_queue"

# Payload sizes — larger payloads make the CPU bug more visible
PAYLOAD_SIZES = {
    "small":  500,
    "medium": 5_000,
    "large":  50_000,
}


def generate_payload(size: int) -> str:
    """Generate a realistic-looking text payload of approx `size` characters."""
    words = [
        "image", "process", "resize", "filter", "compress", "upload",
        "validate", "convert", "encode", "decode", "analyze", "transform",
    ]
    result = []
    while len(" ".join(result)) < size:
        result.append(random.choice(words))
        result.append(str(random.randint(1000, 9999)))
    return " ".join(result)[:size]


def push_jobs(r: redis.Redis, batch_size: int, payload_size: int):
    """Push a batch of jobs to the queue."""
    pipe = r.pipeline()
    for _ in range(batch_size):
        job = {
            "job_id":  str(uuid.uuid4()),
            "payload": generate_payload(payload_size),
            "created": datetime.utcnow().isoformat(),
        }
        pipe.rpush(QUEUE_NAME, json.dumps(job))
    pipe.execute()


def print_status(r: redis.Redis, pushed: int, elapsed: float):
    queue_len = r.llen(QUEUE_NAME)
    rate = pushed / elapsed if elapsed > 0 else 0
    mem_info = r.info("memory")
    used_mb = mem_info["used_memory"] / (1024 * 1024)

    print(
        f"\r[{datetime.now().strftime('%H:%M:%S')}] "
        f"Pushed: {pushed:>6} jobs | "
        f"Queue depth: {queue_len:>5} | "
        f"Rate: {rate:>5.1f} jobs/s | "
        f"Redis mem: {used_mb:.1f} MB",
        end="",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description="OS Lab load generator")
    parser.add_argument(
        "--size", choices=["small", "medium", "large"], default="large",
        help="Payload size per job (default: large — makes CPU bug visible faster)"
    )
    parser.add_argument(
        "--rate", type=int, default=10,
        help="Jobs to push per second (default: 10)"
    )
    args = parser.parse_args()

    payload_size = PAYLOAD_SIZES[args.size]
    batch_size   = max(1, args.rate)
    interval     = 1.0  # push one batch per second

    print(f"OS Troubleshooting Lab — Load Generator")
    print(f"----------------------------------------")
    print(f"Target : Redis @ {REDIS_HOST}:{REDIS_PORT}")
    print(f"Queue  : {QUEUE_NAME}")
    print(f"Rate   : {batch_size} jobs/sec  |  Payload: {args.size} ({payload_size} chars)")
    print(f"\nConnecting to Redis...")

    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print(f"Connected. Starting load... (Ctrl+C to stop)\n")
    except redis.exceptions.ConnectionError:
        print(f"\nERROR: Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}")
        print("Make sure the VMs are running: vagrant status")
        sys.exit(1)

    pushed  = 0
    start   = time.time()

    try:
        while True:
            loop_start = time.time()

            push_jobs(r, batch_size, payload_size)
            pushed += batch_size

            print_status(r, pushed, time.time() - start)

            # Sleep for the remainder of the interval
            elapsed = time.time() - loop_start
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n\nStopped. Total jobs pushed: {pushed}")
        print(f"Queue depth at stop: {r.llen(QUEUE_NAME)} jobs remaining")


if __name__ == "__main__":
    main()
