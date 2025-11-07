# Botrix Quick Start - Worker & Integration Testing

## 🚀 Quick Start (5 Minutes)

### Option 1: Docker (Recommended)

```bash
# 1. Start all services
docker-compose up -d

# 2. Check health
curl http://localhost:8080/health

# 3. Submit a test job (using the backend API)
curl -X POST http://localhost:8080/api/accounts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 1, "priority": "normal"}'

# 4. Check worker logs
docker-compose logs -f worker

# 5. Stop services
docker-compose down
```

### Option 2: Local Development

```bash
# 1. Start Redis
redis-server

# 2. Start Go backend (in terminal 1)
cd backend
go run main.go

# 3. Start Python worker (in terminal 2)
python -m workers.worker_daemon --worker-id worker-1

# 4. Submit test job
curl -X POST http://localhost:8080/api/accounts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 1, "priority": "high"}'
```

---

## 🧪 Running Integration Tests

### Automated (Recommended)

**Linux/macOS**:
```bash
chmod +x scripts/run_integration_tests.sh
./scripts/run_integration_tests.sh
```

**Windows**:
```powershell
.\scripts\run_integration_tests.ps1
```

**With options**:
```bash
# Keep services running after tests
./scripts/run_integration_tests.sh --keep-alive

# Verbose output
./scripts/run_integration_tests.sh --verbose

# Both
./scripts/run_integration_tests.sh --keep-alive --verbose
```

### Manual

```bash
# 1. Start Redis on test DB
redis-server --port 6379

# 2. Run tests
pytest tests/test_full_flow.py -v

# 3. Run specific test
pytest tests/test_full_flow.py::test_single_account_creation -v

# 4. Run with coverage
pytest tests/test_full_flow.py --cov=workers --cov-report=html
```

---

## 📊 Monitoring Workers

### Check Worker Health

```bash
# Redis CLI
redis-cli
> KEYS botrix:worker:health:*
> GET botrix:worker:health:worker-1
```

### Python Script

```python
import redis
import json

r = redis.Redis()
workers = r.keys("botrix:worker:health:*")

for worker_key in workers:
    data = json.loads(r.get(worker_key))
    print(f"Worker: {data['worker_id']}")
    print(f"  Jobs Processed: {data['jobs_processed']}")
    print(f"  Success: {data['jobs_succeeded']}")
    print(f"  Failed: {data['jobs_failed']}")
```

### Docker

```bash
# View all containers
docker-compose ps

# Check worker logs
docker-compose logs -f worker

# Check backend logs
docker-compose logs -f backend

# Check all logs
docker-compose logs -f
```

---

## 🔧 Common Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Start with 3 workers
docker-compose --profile scale up -d

# Start with dev tools (Redis Commander, pgAdmin)
docker-compose --profile dev up -d

# View logs
docker-compose logs -f
docker-compose logs -f worker
docker-compose logs -f backend

# Restart service
docker-compose restart worker
docker-compose restart backend

# Stop services
docker-compose stop

# Stop and remove volumes
docker-compose down -v

# Rebuild containers
docker-compose build
docker-compose up -d --build
```

### Worker Management

```bash
# Start worker
python -m workers.worker_daemon --worker-id worker-1

# With custom config
python -m workers.worker_daemon \
  --worker-id worker-1 \
  --redis-url redis://localhost:6379/0 \
  --max-retries 5 \
  --health-check-interval 60

# Multiple workers (different terminals)
python -m workers.worker_daemon --worker-id worker-1
python -m workers.worker_daemon --worker-id worker-2
python -m workers.worker_daemon --worker-id worker-3
```

### Redis Queue Operations

```bash
redis-cli

# Check queue length
> LLEN botrix:jobs:queue

# View all jobs in queue
> LRANGE botrix:jobs:queue 0 -1

# View job status
> GET botrix:jobs:status:job-uuid-123

# View job results
> GET botrix:jobs:results:job-uuid-123

# Clear queue (careful!)
> DEL botrix:jobs:queue

# View all job statuses
> KEYS botrix:jobs:status:*
```

### Backend API

```bash
# Health check
curl http://localhost:8080/health

# Generate accounts
curl -X POST http://localhost:8080/api/accounts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "priority": "high"}'

# Get job status
curl http://localhost:8080/api/jobs/JOB_ID

# Get statistics
curl http://localhost:8080/api/stats

# List accounts
curl http://localhost:8080/api/accounts?limit=20

# Filter by status
curl http://localhost:8080/api/accounts?status=active
```

---

## 🐛 Troubleshooting

### Worker Not Starting

```bash
# Check Python dependencies
pip install -r requirements.txt

# Check Redis connection
redis-cli ping

# Check worker logs
docker-compose logs worker
```

### Jobs Not Processing

```bash
# Check queue has jobs
redis-cli LLEN botrix:jobs:queue

# Check workers are running
docker-compose ps
redis-cli KEYS "botrix:worker:health:*"

# Check worker logs for errors
docker-compose logs --tail=50 worker
```

### Redis Connection Errors

```bash
# Test Redis
redis-cli ping

# Check Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis
```

### Backend Not Responding

```bash
# Check backend health
curl http://localhost:8080/health

# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

---

## 📁 File Structure

```
Botrix/
├── workers/
│   ├── worker_daemon.py          # Main worker daemon
│   ├── account_creator.py        # Account creation logic
│   ├── email_handler.py          # Email verification
│   └── kasada_solver.py          # Kasada bypass
├── backend/
│   ├── main.go                   # Go backend entry point
│   ├── handlers/                 # API handlers
│   ├── services/                 # Business logic
│   │   ├── database.go           # Database operations
│   │   └── queue.go              # Redis queue service
│   ├── models/                   # Data models
│   └── Dockerfile                # Backend Docker image
├── tests/
│   └── test_full_flow.py         # Integration tests
├── scripts/
│   ├── run_integration_tests.sh  # Test runner (Linux/macOS)
│   └── run_integration_tests.ps1 # Test runner (Windows)
├── deployment/
│   ├── botrix-worker@.service    # systemd service file
│   ├── worker.env.example        # Environment template
│   └── README.md                 # Deployment guide
├── docker-compose.yml            # Docker Compose config
├── Dockerfile.worker             # Worker Docker image
└── WORKER_INTEGRATION_GUIDE.md  # Complete documentation
```

---

## 🎯 Next Steps

1. **Run Integration Tests**: Verify everything works
   ```bash
   ./scripts/run_integration_tests.sh
   ```

2. **Start Development Environment**: 
   ```bash
   docker-compose --profile dev up -d
   ```

3. **Monitor Workers**: 
   - Redis Commander: http://localhost:8081
   - Backend API: http://localhost:8080

4. **Deploy to Production**: See `deployment/README.md`

5. **Scale Workers**:
   ```bash
   docker-compose up -d --scale worker=5
   ```

---

## 📚 Documentation

- **Worker Guide**: `WORKER_INTEGRATION_GUIDE.md`
- **Deployment**: `deployment/README.md`
- **API Documentation**: `backend/API_DOCUMENTATION.md`
- **Database**: `backend/DATABASE_DOCUMENTATION.md`
- **Queue Service**: `backend/services/QUEUE_DOCUMENTATION.md`

---

## 💡 Tips

- **Development**: Use `--profile dev` for Redis Commander and pgAdmin
- **Scaling**: Use `--profile scale` to start additional workers
- **Testing**: Use Redis DB 1 (separate from production DB 0)
- **Logs**: Use `docker-compose logs -f` for real-time monitoring
- **Health**: Check `/health` endpoint and Redis health keys regularly

---

## 🆘 Support

- Check logs: `docker-compose logs -f`
- Check Redis: `redis-cli monitor`
- Check queue: `redis-cli LLEN botrix:jobs:queue`
- Check workers: `redis-cli KEYS "botrix:worker:health:*"`
- Check backend: `curl http://localhost:8080/health`
