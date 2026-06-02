#!/usr/bin/env python3
"""
check_status.py — Shows a dashboard of the lab system health.

Run from your HOST machine (Windows):
    python scripts/check_status.py

Requirements on host:
    pip install redis psycopg2-binary
"""

import redis
import psycopg2
import sys
from datetime import datetime

REDIS_HOST = "192.168.56.10"
DB_HOST    = "192.168.56.12"

SEP = "-" * 52


def check_redis():
    print(f"\n{'BROKER (vm-broker — 192.168.56.10)':^52}")
    print(SEP)
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True, socket_timeout=3)
        r.ping()

        queue_len  = r.llen("job_queue")
        mem_info   = r.info("memory")
        used_mb    = mem_info["used_memory"] / (1024 * 1024)
        max_mb_raw = mem_info.get("maxmemory", 0)
        max_mb     = max_mb_raw / (1024 * 1024) if max_mb_raw else 0

        print(f"  Status        : {'OK' if queue_len >= 0 else 'ERROR'}")
        print(f"  Queue depth   : {queue_len} jobs pending")
        print(f"  Memory used   : {used_mb:.1f} MB / {max_mb:.0f} MB max")

        if max_mb > 0:
            pct = (used_mb / max_mb) * 100
            bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
            print(f"  Memory usage  : [{bar}] {pct:.0f}%")
            if pct > 80:
                print(f"  ⚠  WARNING: Redis memory usage above 80%")

    except redis.exceptions.ConnectionError as e:
        print(f"  Status : UNREACHABLE — {e}")


def check_db():
    print(f"\n{'DATABASE (vm-db — 192.168.56.12)':^52}")
    print(SEP)
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=5432, dbname="labdb",
            user="labuser", password="labpass", connect_timeout=3
        )
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'")
        pending = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM jobs WHERE status='done'")
        done = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM results")
        results = cur.fetchone()[0]

        cur.execute("""
            SELECT AVG(duration_ms), MAX(duration_ms), MIN(duration_ms)
            FROM results
            WHERE created_at > NOW() - INTERVAL '1 minute'
        """)
        row = cur.fetchone()
        avg_ms, max_ms, min_ms = row if row[0] else (0, 0, 0)

        cur.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE datname='labdb'")
        connections = cur.fetchone()[0]

        print(f"  Status        : OK")
        print(f"  Jobs pending  : {pending}")
        print(f"  Jobs done     : {done}")
        print(f"  Results saved : {results}")
        print(f"  Connections   : {connections} active")
        if avg_ms:
            print(f"  Throughput    : avg {avg_ms:.0f}ms | min {min_ms}ms | max {max_ms}ms (last 1 min)")
        else:
            print(f"  Throughput    : no results in last 1 minute")

        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"  Status : UNREACHABLE — {e}")


def main():
    print(f"\n{'OS TROUBLESHOOTING LAB — SYSTEM STATUS':^52}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)
    check_redis()
    check_db()
    print(f"\n{SEP}\n")


if __name__ == "__main__":
    main()
