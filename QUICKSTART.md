# Botrix Quick Start Guide

**Setup Date**: 2025-11-07 17:45:01 UTC  
**User**: Akalimerter878

## ✅ Setup Completed

All required files and dependencies have been configured.

**Verification Results**: ✓ 22/22 checks passed

## 🚀 How to Test

### Option 1: Quick Test (Mock Mode - No API calls)

```bash
# Run Python tests
pytest tests/ -v

# Test CLI
python cli.py test-kasada --dry-run
python cli.py validate-pool
```

### Option 2: Full Test (Requires Redis)

```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Run full test suite
pytest tests/ -v --cov=workers

# Test integration
python -m workers.worker_daemon --test-mode
```

## 📋 Before Production

### 1. Add RAPIDAPI Key

Edit `.env` file:
```bash
RAPIDAPI_KEY=your_actual_rapidapi_key_here
```

### 2. Add Email Accounts

Edit `shared/livelive.txt`:
```
your_email@hotmail.com:your_password
another_email@outlook.com:another_password
```

### 3. Verify Setup

```bash
python verify_setup.py
```

## 🎯 Start the System

### Backend (Go)

```bash
cd backend
go mod download
go run main.go
```

Backend will start on `http://localhost:8080`

### Worker (Python)

```bash
# Using Python module
python -m workers.worker_daemon

# Or using CLI
python workers/worker_daemon.py
```

### Docker Compose (All Services)

```bash
docker-compose up -d
```

This starts:
- Redis
- Backend API
- Worker processes

## 📊 Create Your First Account

### Using CLI

```bash
# Create one account
python cli.py create-one --verbose

# Create multiple accounts
python cli.py create-batch --count 5

# Check queue status
python cli.py queue-stats
```

### Using API

```bash
# Submit account creation job
curl -X POST http://localhost:8080/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{}'

# Check job status
curl http://localhost:8080/api/v1/jobs/{job_id}
```

## 🔍 Monitor System

### WebSocket (Real-time Updates)

Open `test_websocket.html` in browser to see live job updates.

### Logs

```powershell
# View worker logs
Get-Content logs/worker.log -Wait -Tail 50

# View backend logs
Get-Content backend/logs/app.log -Wait -Tail 50
```

### Health Check

```bash
# Backend health
curl http://localhost:8080/health

# Worker health (via Redis)
redis-cli GET worker:worker-1:heartbeat
```

## 📁 Important Files

| File | Purpose |
|------|---------|
| `.env` | Environment configuration |
| `shared/livelive.txt` | Email pool (input) |
| `shared/kicks.json` | Generated accounts (output) |
| `verify_setup.py` | Setup verification |
| `cli.py` | Command-line interface |
| `docker-compose.yml` | Multi-service orchestration |

## 🐛 Troubleshooting

### Redis Connection Error

```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Test connection
redis-cli ping
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
python verify_setup.py
```

### Backend Won't Start

```bash
# Install Go dependencies
cd backend
go mod download
go mod tidy

# Check for errors
go run main.go
```

### Email Pool Empty

Edit `shared/livelive.txt` and add emails:
```
email@hotmail.com:password
```

## 📚 Documentation

- `README.md` - Project overview
- `WEBSOCKET_README.md` - WebSocket API docs
- `CLI_DOCUMENTATION.md` - CLI command reference
- `TESTING.md` - Test suite guide
- `TEST_RESULTS.md` - Latest test results
- `SETUP_COMPLETE.md` - Detailed setup summary

## 🎉 Next Steps

1. ✅ Verify setup: `python verify_setup.py`
2. 📝 Add RAPIDAPI_KEY to `.env`
3. 📧 Add emails to `shared/livelive.txt`
4. 🚀 Start Redis: `docker run -d -p 6379:6379 redis:alpine`
5. 🔧 Start backend: `cd backend && go run main.go`
6. 🤖 Start worker: `python -m workers.worker_daemon`
7. 🎯 Create account: `python cli.py create-one --verbose`

## 💡 Tips

- Use `--dry-run` flag for testing without API calls
- Monitor `shared/kicks.json` for created accounts
- Check logs/ directory for troubleshooting
- Use WebSocket for real-time monitoring
- Run `pytest` regularly during development

---

**Need Help?** See full documentation in project README or check GitHub issues.
