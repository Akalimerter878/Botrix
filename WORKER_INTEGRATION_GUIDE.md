# Botrix Worker & Integration Testing Guide

## Overview

Complete guide for the Botrix worker daemon, integration testing, and deployment infrastructure.

---

## Table of Contents

1. [Worker Daemon](#worker-daemon)
2. [Integration Testing](#integration-testing)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [Troubleshooting](#troubleshooting)

---

## Worker Daemon

### Overview

The worker daemon (`workers/worker_daemon.py`) is a Python service that:
- Consumes jobs from Redis queue
- Processes account creation requests
- Updates job status in real-time
- Supports graceful shutdown
- Includes automatic retry logic
- Reports health status
- Supports multiple concurrent workers

### Features

✅ **Queue Processing**
- BLPOP-based blocking queue consumption
- Automatic job dequeuing from Redis
- FIFO (First-In-First-Out) processing

✅ **Graceful Shutdown**
- Handles SIGTERM and SIGINT signals
- Completes current job before exiting
- Updates health status on shutdown

✅ **Health Checks**
- Updates Redis health key every 30 seconds
- Includes worker statistics (jobs processed, success/fail counts)
- TTL-based expiration for dead worker detection

✅ **Automatic Retry**
- Configurable max retry attempts (default: 3)
- Incremental backoff between retries
- Permanent failure after max retries

✅ **Concurrent Workers**
- Multiple workers can run simultaneously
- Each worker has unique ID
- Job distribution via Redis BLPOP

✅ **Comprehensive Logging**
- Structured logging with worker ID
- Job lifecycle tracking
- Error logging with stack traces

### Usage

**Basic Usage**:
```bash
python -m workers.worker_daemon
```

**With Options**:
```bash
python -m workers.worker_daemon \
    --worker-id worker-1 \
    --redis-url redis://localhost:6379/0 \
    --max-retries 3 \
    --health-check-interval 30
```

**Environment Variables**:
```bash
export REDIS_URL="redis://localhost:6379/0"
export MAX_RETRIES=3
export HEALTH_CHECK_INTERVAL=30

python -m workers.worker_daemon --worker-id worker-1
```

### Configuration

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `--worker-id` | `WORKER_ID` | auto-generated | Unique worker identifier |
| `--redis-url` | `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `--max-retries` | `MAX_RETRIES` | `3` | Maximum retry attempts |
| `--health-check-interval` | `HEALTH_CHECK_INTERVAL` | `30` | Health check interval (seconds) |

### Job Processing Flow

1. **Dequeue Job**: Worker performs BLPOP on `botrix:jobs:queue`
2. **Update Status**: Set job status to "running"
3. **Process Accounts**: Create accounts using `KickAccountCreator`
4. **Store Results**: Save results to `botrix:jobs:results:{job_id}`
5. **Update Status**: Set final status ("completed" or "failed")
6. **Publish Event**: Notify subscribers via `botrix:jobs:updates` channel
7. **Retry on Failure**: Requeue job if retry count < max retries

### Health Check Format

```json
{
  "worker_id": "worker-1",
  "status": "running",
  "last_heartbeat": "2025-11-07T10:30:00Z",
  "current_job": "job-uuid-123",
  "jobs_processed": 42,
  "jobs_succeeded": 38,
  "jobs_failed": 4,
  "uptime_seconds": 3600
}
```

### Monitoring Worker Health

**Check all workers**:
```bash
redis-cli KEYS "botrix:worker:health:*"
```

**Get worker details**:
```bash
redis-cli GET "botrix:worker:health:worker-1"
```

**Python script**:
```python
import redis
import json

r = redis.Redis()
workers = r.keys("botrix:worker:health:*")

for worker_key in workers:
    data = json.loads(r.get(worker_key))
    print(f"Worker: {data['worker_id']}")
    print(f"  Status: {data['status']}")
    print(f"  Jobs: {data['jobs_processed']} (✓{data['jobs_succeeded']} ✗{data['jobs_failed']})")
    print(f"  Uptime: {data['uptime_seconds']}s")
```

---

## Integration Testing

### Overview

The integration test suite (`tests/test_full_flow.py`) provides end-to-end testing of:
- Job queuing (simulates Go backend)
- Worker processing (simulates Python worker)
- Job status updates
- Result storage
- Pub/Sub notifications

### Test Coverage

- ✅ Single account creation
- ✅ Multiple accounts per job
- ✅ Sequential job processing
- ✅ Concurrent worker simulation
- ✅ Job failure handling
- ✅ Status progression tracking
- ✅ Pub/Sub event verification
- ✅ Queue persistence
- ✅ Empty queue timeout
- ✅ Health check mechanism
- ✅ High volume processing (50+ jobs)

### Running Tests

**Run all tests**:
```bash
pytest tests/test_full_flow.py -v
```

**Run specific test**:
```bash
pytest tests/test_full_flow.py::test_single_account_creation -v
```

**Run with coverage**:
```bash
pytest tests/test_full_flow.py --cov=workers --cov-report=html
```

**Run slow tests**:
```bash
pytest tests/test_full_flow.py -v -m slow
```

### Integration Test Runner

**Linux/macOS**:
```bash
chmod +x scripts/run_integration_tests.sh
./scripts/run_integration_tests.sh
```

**Windows**:
```powershell
.\scripts\run_integration_tests.ps1
```

**Options**:
- `--keep-alive` / `-KeepAlive`: Keep services running after tests
- `--verbose` / `-Verbose`: Show detailed output

**Example**:
```bash
# Run tests and keep services for debugging
./scripts/run_integration_tests.sh --keep-alive --verbose

# Access services after tests
curl http://localhost:8080/health
redis-cli ping
```

### Test Environment

The integration tests use:
- **Redis DB 1** (separate from production DB 0)
- **Mock Account Creator** (no real API calls)
- **Simulated Worker** (simplified processing logic)
- **In-memory Job Queue** (Redis-based)

---

## Docker Deployment

### Overview

Docker Compose configuration for complete Botrix stack:
- **Redis**: Job queue and cache
- **PostgreSQL**: Database (optional, can use SQLite)
- **Go Backend**: REST API server
- **Python Workers**: Account creation workers
- **Dev Tools**: Redis Commander, pgAdmin (optional)

### Quick Start

**Start all services**:
```bash
docker-compose up -d
```

**Start with 3 workers**:
```bash
docker-compose --profile scale up -d
```

**Start with dev tools**:
```bash
docker-compose --profile dev up -d
```

**View logs**:
```bash
docker-compose logs -f
docker-compose logs -f worker
docker-compose logs -f backend
```

**Stop services**:
```bash
docker-compose down
```

**Stop and remove volumes**:
```bash
docker-compose down -v
```

### Service URLs

- **Backend API**: http://localhost:8080
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432
- **Redis Commander**: http://localhost:8081 (dev profile)
- **pgAdmin**: http://localhost:5050 (dev profile)

### Scaling Workers

**Add more workers**:
```bash
docker-compose up -d --scale worker=5
```

**Check worker status**:
```bash
docker-compose ps
```

### Environment Configuration

Create `.env` file:
```env
# Database
DB_DRIVER=sqlite
DB_DSN=./data/botrix.db

# PostgreSQL (if using)
POSTGRES_PASSWORD=your-secure-password
DB_DRIVER=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=botrix
DB_USER=botrix
DB_PASSWORD=your-secure-password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Worker
MAX_RETRIES=3
HEALTH_CHECK_INTERVAL=30
```

### Health Checks

All services include health checks:

**Backend**:
```bash
curl http://localhost:8080/health
```

**Redis**:
```bash
redis-cli ping
```

**PostgreSQL**:
```bash
docker-compose exec postgres pg_isready -U botrix
```

**Workers**:
```bash
docker-compose exec worker python3 -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.get('botrix:worker:health:worker-1'))"
```

---

## Production Deployment

### systemd Service (Linux)

**1. Install**:
```bash
# Copy service file
sudo cp deployment/botrix-worker@.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

**2. Configure**:
```bash
# Create environment file
sudo mkdir -p /etc/botrix
sudo cp deployment/worker.env.example /etc/botrix/worker.env
sudo vim /etc/botrix/worker.env
```

**3. Start Workers**:
```bash
# Start single worker
sudo systemctl start botrix-worker@1
sudo systemctl enable botrix-worker@1

# Start multiple workers
sudo systemctl start botrix-worker@{1..4}
sudo systemctl enable botrix-worker@{1..4}
```

**4. Monitor**:
```bash
# Check status
sudo systemctl status botrix-worker@1

# View logs
sudo journalctl -u botrix-worker@1 -f

# All workers
sudo journalctl -u 'botrix-worker@*' -f
```

### Deployment Checklist

- [ ] Redis installed and secured
- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Log directories created
- [ ] systemd services installed
- [ ] Workers started and enabled
- [ ] Health checks verified
- [ ] Monitoring configured
- [ ] Log rotation configured
- [ ] Firewall rules set
- [ ] Backup strategy implemented

---

## Monitoring & Health Checks

### Worker Monitoring

**Check all workers**:
```python
import redis
import json
from datetime import datetime

r = redis.Redis()
workers = r.keys("botrix:worker:health:*")

print(f"Active Workers: {len(workers)}\n")

for worker_key in workers:
    data = json.loads(r.get(worker_key))
    
    # Calculate stats
    success_rate = 0
    if data['jobs_processed'] > 0:
        success_rate = (data['jobs_succeeded'] / data['jobs_processed']) * 100
    
    print(f"┌─ {data['worker_id']}")
    print(f"│  Status: {data['status']}")
    print(f"│  Current Job: {data['current_job'] or 'None'}")
    print(f"│  Jobs Processed: {data['jobs_processed']}")
    print(f"│  Success Rate: {success_rate:.1f}%")
    print(f"│  Uptime: {data['uptime_seconds']}s")
    print(f"│  Last Heartbeat: {data['last_heartbeat']}")
    print(f"└─")
```

### Queue Monitoring

```python
import redis

r = redis.Redis()

# Queue length
queue_length = r.llen("botrix:jobs:queue")
print(f"Jobs in Queue: {queue_length}")

# Processing jobs
processing = r.llen("botrix:jobs:processing")
print(f"Jobs Processing: {processing}")

# Peek at next job
if queue_length > 0:
    next_job = r.lindex("botrix:jobs:queue", 0)
    print(f"Next Job: {next_job}")
```

### Prometheus Metrics (Future)

Export worker metrics to Prometheus:
```python
from prometheus_client import Counter, Gauge, start_http_server

jobs_processed = Counter('botrix_jobs_processed_total', 'Total jobs processed')
jobs_succeeded = Counter('botrix_jobs_succeeded_total', 'Total successful jobs')
jobs_failed = Counter('botrix_jobs_failed_total', 'Total failed jobs')
queue_length = Gauge('botrix_queue_length', 'Current queue length')
active_workers = Gauge('botrix_active_workers', 'Number of active workers')

# Start metrics server on port 9090
start_http_server(9090)
```

---

## Troubleshooting

### Worker Not Processing Jobs

**Check worker is running**:
```bash
# systemd
sudo systemctl status botrix-worker@1

# Docker
docker-compose ps worker
```

**Check Redis connection**:
```bash
redis-cli ping
```

**Check queue has jobs**:
```bash
redis-cli LLEN botrix:jobs:queue
```

**Check worker logs**:
```bash
# systemd
sudo journalctl -u botrix-worker@1 -n 50

# Docker
docker-compose logs --tail=50 worker
```

### Jobs Stuck in Queue

**Possible causes**:
1. No workers running
2. Workers crashed
3. Redis connection issue
4. Job data corrupted

**Solutions**:
```bash
# Check workers
redis-cli KEYS "botrix:worker:health:*"

# Restart workers
sudo systemctl restart botrix-worker@{1..4}

# Clear stuck job (carefully!)
redis-cli LPOP botrix:jobs:queue
```

### High Failure Rate

**Check error messages**:
```bash
redis-cli KEYS "botrix:jobs:status:*:error"
redis-cli GET "botrix:jobs:status:job-123:error"
```

**Check account creator logs**:
```bash
# Look for Kasada/API errors
docker-compose logs worker | grep ERROR
```

**Common issues**:
- Kasada solver failing
- Email verification timeouts
- API rate limiting
- Network connectivity

### Memory Issues

**Check worker memory**:
```bash
# Docker
docker stats botrix-worker-1

# systemd
sudo systemctl status botrix-worker@1
```

**Increase memory limit**:
```yaml
# docker-compose.yml
services:
  worker:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Redis Connection Errors

**Test connection**:
```bash
redis-cli -u redis://localhost:6379/0 ping
```

**Check Redis logs**:
```bash
# Docker
docker-compose logs redis

# systemd
sudo journalctl -u redis -n 50
```

**Verify configuration**:
```bash
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET maxmemory-policy
```

---

## Best Practices

### Production Deployment

1. **Use Multiple Workers**: At least 2-3 for redundancy
2. **Monitor Health Checks**: Alert on stale heartbeats
3. **Log Aggregation**: Use ELK, Loki, or similar
4. **Resource Limits**: Set memory/CPU limits
5. **Graceful Shutdown**: Always use SIGTERM, not SIGKILL
6. **Regular Restarts**: Restart workers daily to clear memory
7. **Rate Limiting**: Implement job rate limiting if needed
8. **Backup Strategy**: Backup Redis regularly
9. **Monitoring**: Use Prometheus + Grafana
10. **Alerting**: Alert on high failure rates

### Development

1. **Use Docker Compose**: Consistent environment
2. **Run Integration Tests**: Before each deployment
3. **Monitor Logs**: Real-time log viewing
4. **Test Failures**: Simulate failures in tests
5. **Local Redis**: Use Redis DB 1 for testing

### Security

1. **Redis Password**: Always use password in production
2. **Network Isolation**: Use Docker networks
3. **Resource Limits**: Prevent DoS
4. **Input Validation**: Validate all job data
5. **Error Messages**: Don't expose sensitive data in errors

---

## Summary

✅ **Worker Daemon**: Robust, production-ready worker with health checks, retries, and graceful shutdown  
✅ **Integration Tests**: Comprehensive test suite covering all scenarios  
✅ **Docker Deployment**: Complete containerized stack with scaling support  
✅ **systemd Service**: Production deployment with automatic restart and logging  
✅ **Monitoring**: Health checks, metrics, and logging infrastructure  
✅ **Documentation**: Complete guide for deployment and troubleshooting  

The Botrix worker infrastructure is ready for production deployment!
