# Botrix Backend API

Go backend API for the Botrix Kick.com account generator.

## Tech Stack

- **Framework**: Fiber v2 (Express-like web framework)
- **Database**: SQLite (GORM ORM) - can switch to PostgreSQL
- **Queue**: Redis
- **Language**: Go 1.21+

## Project Structure

```
backend/
├── main.go              # Application entry point
├── config/
│   └── config.go        # Configuration management
├── handlers/
│   ├── health.go        # Health check endpoints
│   └── accounts.go      # Account & job handlers
├── models/
│   ├── account.go       # Account model & DTOs
│   └── job.go           # Job model & DTOs
├── services/
│   ├── database.go      # Database service (GORM)
│   └── queue.go         # Redis queue service
└── go.mod               # Go dependencies
```

## Setup

### Prerequisites

- Go 1.21 or higher
- Redis server running
- (Optional) PostgreSQL for production

### Installation

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Download dependencies**:
   ```bash
   go mod download
   ```

3. **Set environment variables** (or use parent .env file):
   ```bash
   # Server
   SERVER_PORT=8080
   SERVER_HOST=0.0.0.0
   ENVIRONMENT=development

   # Database (SQLite)
   DB_DRIVER=sqlite
   DB_DSN=./botrix.db

   # Redis
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=
   ```

4. **Run the server**:
   ```bash
   go run main.go
   ```

## API Endpoints

### Health Checks

- `GET /health` - Full health check
- `GET /ping` - Simple ping/pong
- `GET /ready` - Kubernetes readiness probe
- `GET /live` - Kubernetes liveness probe

### Accounts

- `GET /api/accounts` - List all accounts (paginated)
- `GET /api/accounts/:id` - Get account by ID
- `GET /api/accounts/stats` - Get account statistics
- `POST /api/accounts` - Create account(s) (queues job)
- `PUT /api/accounts/:id` - Update account
- `DELETE /api/accounts/:id` - Delete account

### Jobs

- `GET /api/jobs` - List all jobs (paginated)
- `GET /api/jobs/:id` - Get job by ID
- `GET /api/jobs/stats` - Get job statistics
- `POST /api/jobs/:id/cancel` - Cancel a job

## Example Requests

### Create Accounts

```bash
# Create 5 accounts
curl -X POST http://localhost:8080/api/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "count": 5
  }'
```

### List Accounts

```bash
# Get first 10 accounts
curl http://localhost:8080/api/accounts?limit=10&offset=0
```

### Get Account Stats

```bash
curl http://localhost:8080/api/accounts/stats
```

### Check Job Status

```bash
curl http://localhost:8080/api/jobs/{job-id}
```

## Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "message": "Optional message",
  "data": {},
  "error": "Error message if success=false"
}
```

## Database Schema

### Accounts Table

```sql
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at DATETIME,
  updated_at DATETIME,
  deleted_at DATETIME,
  email VARCHAR UNIQUE NOT NULL,
  username VARCHAR UNIQUE NOT NULL,
  password VARCHAR NOT NULL,
  email_password VARCHAR NOT NULL,
  birthdate VARCHAR,
  verification_code VARCHAR,
  status VARCHAR DEFAULT 'active',
  job_id VARCHAR,
  kick_account_id VARCHAR,
  kick_data TEXT,
  notes TEXT
);
```

### Jobs Table

```sql
CREATE TABLE jobs (
  id VARCHAR PRIMARY KEY,
  created_at DATETIME,
  updated_at DATETIME,
  deleted_at DATETIME,
  count INTEGER NOT NULL,
  username VARCHAR,
  password VARCHAR,
  status VARCHAR DEFAULT 'pending',
  progress INTEGER DEFAULT 0,
  successful INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0,
  started_at DATETIME,
  completed_at DATETIME,
  error_msg TEXT,
  test_mode BOOLEAN DEFAULT FALSE,
  priority INTEGER DEFAULT 0
);
```

## Redis Queue

Jobs are queued in Redis using a sorted set for priority:

- **Queue Key**: `botrix:jobs:queue`
- **Processing Set**: `botrix:jobs:processing`
- **Results Key**: `botrix:jobs:results:{job_id}`

## Development

### Build

```bash
go build -o botrix-backend
```

### Run

```bash
./botrix-backend
```

### Format Code

```bash
go fmt ./...
```

### Run Tests

```bash
go test ./...
```

## Production Deployment

### Build for Production

```bash
# Build optimized binary
go build -ldflags="-s -w" -o botrix-backend

# Or with version info
go build -ldflags="-s -w -X main.Version=1.0.0" -o botrix-backend
```

### Environment Variables

```bash
ENVIRONMENT=production
SERVER_PORT=8080
DB_DRIVER=postgres
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=botrix
DB_USER=your-user
DB_PASSWORD=your-password
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```

### Docker (Future)

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o botrix-backend

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/botrix-backend .
EXPOSE 8080
CMD ["./botrix-backend"]
```

## Features

✅ RESTful API with Fiber framework  
✅ GORM ORM with SQLite (PostgreSQL ready)  
✅ Redis job queue  
✅ CORS support  
✅ Request logging  
✅ Error handling  
✅ Graceful shutdown  
✅ Health check endpoints  
✅ Pagination support  
✅ Statistics endpoints  

## Next Steps

- [ ] Implement job worker to process queued jobs
- [ ] Add authentication/authorization
- [ ] Add rate limiting
- [ ] Add WebSocket support for real-time updates
- [ ] Add Swagger/OpenAPI documentation
- [ ] Add unit tests
- [ ] Add Docker support
- [ ] Add CI/CD pipeline
- [ ] Switch to PostgreSQL for production

## License

MIT
