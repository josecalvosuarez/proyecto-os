#!/bin/bash
set -e

echo "==> Installing Python and dependencies..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv

echo "==> Setting up app environment..."
python3 -m venv /opt/venv
/opt/venv/bin/pip install --quiet redis psycopg2-binary

echo "==> Configuring logging directory..."
mkdir -p /var/log/app

# NOTE: log rotation is intentionally NOT configured here.
# The worker logs at DEBUG level with no size limit, which will
# eventually fill /var/log. A healthy setup would use logrotate.

echo "==> Installing worker systemd service..."
cat > /etc/systemd/system/worker.service << 'EOF'
[Unit]
Description=OS Lab Job Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/app
ExecStart=/opt/venv/bin/python3 /opt/app/worker.py
Restart=always
RestartSec=3
StandardOutput=append:/var/log/app/worker.log
StandardError=append:/var/log/app/worker.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable worker
systemctl start worker

echo "==> vm-worker provisioning complete."
echo "    Worker service running. Logs: /var/log/app/worker.log"
