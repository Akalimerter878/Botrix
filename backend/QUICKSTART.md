# Botrix Backend - Quick Start Guide

## Prerequisites

- Go 1.21+ installed
- Redis server (for job queue)
- PowerShell or terminal access

## Step 1: Install Dependencies

Navigate to the backend directory and download all Go dependencies:

```powershell
cd backend
go mod download
```

This will fetch all required packages:
- Fiber web framework
- GORM (database ORM)
- Redis client
- SQLite driver
- godotenv (environment variables)
- UUID generator

## Step 2: Configure Environment

Copy the example environment file:

```powershell
copy .env.example ..\.env
```

Edit `.env` in the project root if needed. Default values:
- Server runs on `http://localhost:8080`
- Database file: `botrix.db` (auto-created)
- Redis on `localhost:6379` (no password)

## Step 3: Start Redis

**Option 1: Using Docker**
```powershell
docker run -d -p 6379:6379 redis:alpine
```

**Option 2: Install Redis locally**
- Windows: Download from https://redis.io/download or use WSL
- Run: `redis-server`

**Option 3: Skip Redis for now**
The API will start but job queue features won't work until Redis is available.

## Step 4: Run the Backend

**Using Make (recommended):**
```powershell
make run
```

**Or directly with Go:**
```powershell
go run main.go
```

**Or build and run:**
```powershell
make build
.\botrix-backend.exe
```

You should see:
```
[Botrix] Database initialized successfully
[Botrix] Queue service initialized successfully
[Botrix] Server starting on 0.0.0.0:8080
```

## Step 5: Test the API

Open a new terminal and test the health endpoint:

```powershell
curl http://localhost:8080/health/ping
# Response: {"message":"pong"}
```

Test the main health check:
```powershell
curl http://localhost:8080/health
```

Response should show all services as healthy:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

## Common Make Commands

```powershell
make help          # Show all available commands
make deps          # Download dependencies
make run           # Run the application
make build         # Build binary
make dev           # Format, vet, and run
make test          # Run tests
make fmt           # Format code
make clean         # Clean build artifacts
```

## API Endpoints

### Health Checks
- `GET /health` - Full health check
- `GET /health/ping` - Simple ping/pong
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Accounts (under `/api`)
- `GET /api/accounts` - List all accounts (with pagination)
- `POST /api/accounts` - Create account (creates job)
- `GET /api/accounts/:id` - Get account details
- `PUT /api/accounts/:id` - Update account
- `DELETE /api/accounts/:id` - Delete account
- `GET /api/accounts/stats` - Get account statistics

### Jobs (under `/api`)
- `GET /api/jobs` - List all jobs (with pagination)
- `GET /api/jobs/:id` - Get job details
- `POST /api/jobs/:id/cancel` - Cancel a job
- `GET /api/jobs/stats` - Get job statistics

## Example Requests

### Create an Account (Job)
```powershell
curl -X POST http://localhost:8080/api/accounts `
  -H "Content-Type: application/json" `
  -d '{
    "count": 5,
    "priority": 1,
    "verification_enabled": true
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "count": 5,
  "message": "Job created successfully"
}
```

### Get Job Status
```powershell
curl http://localhost:8080/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

### List Accounts with Pagination
```powershell
curl "http://localhost:8080/api/accounts?page=1&limit=10&status=verified"
```

### Cancel a Job
```powershell
curl -X POST http://localhost:8080/api/jobs/550e8400-e29b-41d4-a716-446655440000/cancel
```

## Troubleshooting

### Import errors in VS Code
Run `go mod download` in the backend directory. VS Code should auto-detect the packages.

### Redis connection failed
- Make sure Redis is running: `redis-cli ping` should return `PONG`
- Check `.env` file has correct Redis host/port
- On Windows, use Docker or WSL for Redis

### Database errors
- The SQLite database is auto-created on first run
- Delete `botrix.db` to reset: `make db-reset`

### Port already in use
Change `SERVER_PORT` in `.env` file to use a different port (e.g., 8081).

## Next Steps

1. **Implement Worker**: Create a worker service to process queued jobs
2. **Connect Python Scripts**: Integrate with existing account creation code
3. **Add Authentication**: Implement API key or JWT authentication
4. **Production Deploy**: Use Docker, set `SERVER_ENV=production`
5. **Add Tests**: Write unit and integration tests

## Development Workflow

```powershell
# Format code before committing
make fmt

# Run linter
make vet

# Run tests
make test

# Full check (format, vet, test)
make check

# Hot reload during development (requires air)
make watch
```

## Project Structure

```
backend/
├── main.go              # Application entry point
├── config/              # Configuration management
│   └── config.go
├── models/              # Data models
│   ├── account.go
│   └── job.go
├── services/            # Business logic
│   ├── database.go
│   └── queue.go
├── handlers/            # HTTP handlers
│   ├── health.go
│   └── accounts.go
├── Makefile            # Build automation
├── go.mod              # Go dependencies
├── .env.example        # Environment template
└── README.md           # Full documentation
```

## Support

For detailed API documentation, see `README.md` in the backend directory.

For issues or questions, check the main project documentation in the root directory.
