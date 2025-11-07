# Botrix Worker Deployment

## Production Deployment with systemd

### Installation

1. **Create botrix user**:
```bash
sudo useradd -r -s /bin/false botrix
sudo mkdir -p /opt/botrix
sudo chown botrix:botrix /opt/botrix
```

2. **Install application**:
```bash
sudo -u botrix git clone <repo-url> /opt/botrix
cd /opt/botrix
sudo -u botrix python3 -m venv venv
sudo -u botrix ./venv/bin/pip install -r requirements.txt
```

3. **Create directories**:
```bash
sudo mkdir -p /opt/botrix/logs /opt/botrix/data
sudo chown botrix:botrix /opt/botrix/logs /opt/botrix/data
sudo mkdir -p /etc/botrix
```

4. **Configure environment**:
```bash
sudo cp deployment/worker.env.example /etc/botrix/worker.env
sudo vim /etc/botrix/worker.env
```

Edit `/etc/botrix/worker.env`:
```bash
REDIS_URL=redis://localhost:6379/0
MAX_RETRIES=3
HEALTH_CHECK_INTERVAL=30
```

5. **Install systemd service**:
```bash
sudo cp deployment/botrix-worker@.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Running Workers

**Start single worker**:
```bash
sudo systemctl start botrix-worker@1
sudo systemctl status botrix-worker@1
```

**Start multiple workers**:
```bash
sudo systemctl start botrix-worker@{1..4}
```

**Enable on boot**:
```bash
sudo systemctl enable botrix-worker@1
sudo systemctl enable botrix-worker@2
sudo systemctl enable botrix-worker@3
```

**View logs**:
```bash
# All workers
sudo journalctl -u 'botrix-worker@*' -f

# Specific worker
sudo journalctl -u botrix-worker@1 -f

# Last 100 lines
sudo journalctl -u botrix-worker@1 -n 100
```

**Stop workers**:
```bash
sudo systemctl stop botrix-worker@{1..4}
```

### Health Checks

Check worker health in Redis:
```bash
redis-cli
> KEYS botrix:worker:health:*
> GET botrix:worker:health:worker-1
```

### Monitoring

**Worker statistics**:
```python
import redis
import json

r = redis.Redis()
workers = r.keys("botrix:worker:health:*")

for worker_key in workers:
    data = json.loads(r.get(worker_key))
    print(f"Worker: {data['worker_id']}")
    print(f"  Status: {data['status']}")
    print(f"  Jobs Processed: {data['jobs_processed']}")
    print(f"  Success: {data['jobs_succeeded']}")
    print(f"  Failed: {data['jobs_failed']}")
    print(f"  Uptime: {data['uptime_seconds']}s")
```

### Troubleshooting

**Worker not starting**:
```bash
sudo systemctl status botrix-worker@1
sudo journalctl -u botrix-worker@1 -n 50
```

**Check Redis connection**:
```bash
redis-cli ping
```

**Check permissions**:
```bash
ls -la /opt/botrix
sudo -u botrix /opt/botrix/venv/bin/python3 -c "import redis; print('OK')"
```

**Restart all workers**:
```bash
sudo systemctl restart botrix-worker@{1..4}
```

### Scaling

To add more workers:
```bash
sudo systemctl start botrix-worker@5
sudo systemctl enable botrix-worker@5
```

To remove workers:
```bash
sudo systemctl stop botrix-worker@5
sudo systemctl disable botrix-worker@5
```

### Production Checklist

- [ ] Redis properly configured and secured
- [ ] Environment variables set in `/etc/botrix/worker.env`
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up
- [ ] Firewall rules configured
- [ ] Workers enabled for auto-start on boot
- [ ] Health checks monitored
- [ ] Resource limits appropriate for workload
