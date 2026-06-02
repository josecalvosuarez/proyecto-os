#!/bin/bash
set -e

echo "==> Installing PostgreSQL..."
apt-get update -qq
apt-get install -y postgresql postgresql-contrib

echo "==> Configuring PostgreSQL..."
PG_CONF="/etc/postgresql/14/main/postgresql.conf"
PG_HBA="/etc/postgresql/14/main/pg_hba.conf"

# NOTE: max_connections is intentionally set to 5.
# With 3+ workers each opening their own connection, the pool
# exhausts quickly under load. A healthy value is 100+.
sed -i "s/^#max_connections = .*/max_connections = 5/" $PG_CONF
sed -i "s/^max_connections = .*/max_connections = 5/" $PG_CONF

# Allow connections from the private network
echo "host    all    all    192.168.56.0/24    md5" >> $PG_HBA

echo "==> Starting PostgreSQL..."
systemctl enable postgresql
systemctl restart postgresql

echo "==> Creating database and user..."
sudo -u postgres psql << 'EOSQL'
CREATE USER labuser WITH PASSWORD 'labpass';
CREATE DATABASE labdb OWNER labuser;
GRANT ALL PRIVILEGES ON DATABASE labdb TO labuser;
EOSQL

echo "==> Creating schema..."
# NOTE: the results table intentionally has NO index on status or created_at.
# Queries filtering by status or ordering by created_at will do full
# sequential scans, becoming very slow as the table grows.
sudo -u postgres psql -d labdb << 'EOSQL'
\c labdb

CREATE TABLE IF NOT EXISTS jobs (
    id          SERIAL PRIMARY KEY,
    job_id      VARCHAR(64) UNIQUE NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    payload     TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS results (
    id          SERIAL PRIMARY KEY,
    job_id      VARCHAR(64) NOT NULL,
    output      TEXT,
    duration_ms INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
    -- NOTE: no index on job_id or created_at intentionally
);

GRANT ALL ON ALL TABLES IN SCHEMA public TO labuser;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO labuser;
EOSQL

echo "==> vm-db provisioning complete."
echo "    PostgreSQL on 192.168.56.12:5432 | db=labdb user=labuser pass=labpass"
