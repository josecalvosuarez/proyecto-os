#!/bin/bash
set -e

echo "==> Installing Redis..."
apt-get update -qq
apt-get install -y redis-server

echo "==> Configuring Redis..."
# NOTE: maxmemory is intentionally set very low (8mb) to cause OOM
# under load. A healthy value would be 256mb or more.
cat > /etc/redis/redis.conf << 'EOF'
bind 0.0.0.0
port 6379
daemonize yes
loglevel notice
logfile /var/log/redis/redis-server.log
maxmemory 8mb
maxmemory-policy allkeys-lru
EOF

mkdir -p /var/log/redis
chown redis:redis /var/log/redis

echo "==> Starting Redis..."
systemctl enable redis-server
systemctl restart redis-server

echo "==> vm-broker provisioning complete."
echo "    Redis listening on 192.168.56.10:6379"
