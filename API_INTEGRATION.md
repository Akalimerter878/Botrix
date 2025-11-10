# Backend API Integration Documentation

## Overview

The Botrix backend provides a robust REST API with WebSocket support for real-time updates. All endpoints follow consistent response formats and include comprehensive error handling.

## Architecture

### Stack
- **Backend Framework**: Go Fiber v2
- **Frontend Framework**: React 18 + TypeScript + Vite
- **Database**: PostgreSQL with GORM
- **Queue**: Redis
- **Real-time**: WebSocket

### Base URL
- Development: `http://localhost:8080`
- Production: Set via `VITE_API_URL` environment variable

## API Client (`dashboard/src/lib/api.ts`)

### Features
- ✅ TypeScript type safety with backend model matching
- ✅ Custom `ApiError` class for structured error handling
- ✅ Comprehensive request/response logging with timestamps
- ✅ Automatic error parsing from backend responses
- ✅ Success/failure detection via `success` field
- ✅ Axios interceptors for global error handling
- ✅ 30-second timeout with configurable retry logic

### Usage Example

```typescript
import { api, ApiError } from '@/lib/api';

// Fetch accounts
try {
  const accounts = await api.accounts.list();
  console.log('Accounts:', accounts);
} catch (error) {
  if (error instanceof ApiError) {
    console.error('API Error:', error.message);
    console.error('Status Code:', error.statusCode);
    console.error('Data:', error.data);
  }
}
```

## Backend Endpoints

### Health Checks

#### `GET /health`
Basic health check with service status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T12:00:00Z",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

#### `GET /health/ping`
Quick ping for uptime monitoring.

#### `GET /health/ready`
Readiness probe (all services operational).

#### `GET /health/live`
Liveness probe (service is running).

---

### Accounts

#### `GET /api/accounts`
List all accounts with optional pagination.

**Query Parameters:**
- `limit` (optional): Max results (1-100, default: 20)
- `offset` (optional): Offset for pagination (default: 0)
- `status` (optional): Filter by status (`active`, `banned`, `suspended`)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "email": "user@example.com",
      "username": "username123",
      "password": "***",
      "email_password": "***",
      "status": "active",
      "created_at": "2025-11-10T12:00:00Z",
      "updated_at": "2025-11-10T12:00:00Z",
      "job_id": "uuid-here",
      "birthdate": "1990-01-01",
      "kick_account_id": "kick123",
      "kick_data": "{}",
      "notes": ""
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 100,
    "count": 20
  }
}
```

#### `GET /api/accounts/:id`
Get specific account by ID.

**Response:**
```json
{
  "success": true,
  "account": { /* account object */ }
}
```

#### `POST /api/accounts`
Create account creation job.

**Request Body:**
```json
{
  "count": 5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account creation job queued",
  "job": { /* job object */ }
}
```

#### `PUT /api/accounts/:id`
Update account details.

**Request Body:**
```json
{
  "status": "active",
  "notes": "Updated notes"
}
```

#### `DELETE /api/accounts/:id`
Soft delete account (sets DeletedAt timestamp).

**Response:**
```json
{
  "success": true,
  "message": "Account deleted successfully",
  "account": {
    "id": 1,
    "username": "username123",
    "email": "user@example.com"
  }
}
```

---

### Jobs

#### `GET /api/jobs`
List all jobs with pagination.

**Query Parameters:**
- `limit` (optional): Max results (1-100, default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "success": true,
  "jobs": [
    {
      "id": "uuid-here",
      "status": "running",
      "count": 10,
      "progress": 5,
      "successful": 4,
      "failed": 1,
      "created_at": "2025-11-10T12:00:00Z",
      "updated_at": "2025-11-10T12:05:00Z",
      "started_at": "2025-11-10T12:01:00Z",
      "completed_at": null,
      "error_msg": "",
      "test_mode": false,
      "priority": 1
    }
  ]
}
```

#### `GET /api/jobs/:jobId`
Get specific job with detailed progress.

**Response:**
```json
{
  "success": true,
  "job": { /* job object */ },
  "progress": {
    "current": 5,
    "total": 10,
    "percentage": 50.0,
    "successful": 4,
    "failed": 1
  },
  "duration": "4m30s",
  "status": "running"
}
```

#### `POST /api/jobs/:id/cancel`
Cancel a pending or running job.

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled successfully",
  "job": { /* updated job object */ }
}
```

#### `GET /api/jobs/stats`
Get job statistics and queue metrics.

**Response:**
```json
{
  "success": true,
  "job_stats": {
    "total": 100,
    "pending": 10,
    "running": 5,
    "completed": 80,
    "failed": 3,
    "cancelled": 2
  },
  "queue_stats": {
    "pending_jobs": 15,
    "processing_jobs": 5
  }
}
```

#### `POST /api/accounts/generate`
Generate multiple account creation jobs.

**Request Body:**
```json
{
  "count": 10,
  "priority": "normal"
}
```

**Priority Options:** `low`, `normal`, `high`

**Response:**
```json
{
  "success": true,
  "job_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "message": "Jobs queued successfully"
}
```

---

### Statistics

#### `GET /api/stats`
Get comprehensive system statistics.

**Response:**
```json
{
  "success": true,
  "total_accounts": 1500,
  "success_rate": 92.5,
  "failure_rate": 7.5,
  "account_stats": {
    "total": 1500,
    "active": 1400,
    "banned": 50,
    "suspended": 50,
    "created_today": 25
  },
  "job_stats": {
    "total": 200,
    "pending": 10,
    "running": 5,
    "completed": 180,
    "failed": 3,
    "cancelled": 2
  },
  "queue_stats": {
    "pending_jobs": 15,
    "processing_jobs": 5
  },
  "hotmail_pool_remaining": 500
}
```

---

### WebSocket

#### `GET /ws` (WebSocket Upgrade)
Real-time updates for jobs and accounts.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('WebSocket message:', message);
};
```

**Message Types:**
- `job_update`: Job status/progress changed
- `account_created`: New account created
- `error`: Error occurred

**Message Format:**
```json
{
  "type": "job_update",
  "job_id": "uuid-here",
  "status": "running",
  "progress": 5,
  "data": { /* additional data */ }
}
```

#### `GET /ws/stats`
WebSocket connection statistics.

**Response:**
```json
{
  "active_connections": 3,
  "messages_sent": 150,
  "messages_received": 75
}
```

---

## Error Handling

### Error Response Format

All errors follow consistent format:

```json
{
  "success": false,
  "error": "Error message here",
  "message": "Additional context (optional)",
  "code": 400
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request (validation error)
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

### Frontend Error Handling

The `ApiError` class provides structured error information:

```typescript
try {
  await api.jobs.cancel('invalid-id');
} catch (error) {
  if (error instanceof ApiError) {
    switch (error.statusCode) {
      case 404:
        toast.error('Job not found');
        break;
      case 400:
        toast.error(`Invalid request: ${error.message}`);
        break;
      case 429:
        toast.error('Rate limit exceeded. Please try again later.');
        break;
      default:
        toast.error(error.message);
    }
  }
}
```

---

## Request/Response Logging

### Backend Logging

Enhanced logging middleware (`handlers.EnhancedLogger()`) provides:

- ✅ Request/response timestamps (ISO 8601 format)
- ✅ HTTP method, path, and client IP
- ✅ Request ID tracking
- ✅ Query parameters logging
- ✅ Request body logging (JSON pretty-printed)
- ✅ **Sensitive data redaction** (passwords, tokens, secrets)
- ✅ Response status codes with emoji indicators
- ✅ Latency tracking (duration)
- ✅ Response size (human-readable format)

**Example Log Output:**
```
[API 2025-11-10 12:00:00.123] → POST /api/accounts/generate 127.0.0.1
[API 2025-11-10 12:00:00.123]   Request-ID: abc123
[API 2025-11-10 12:00:00.123]   Body: {
           "count": 5,
           "priority": "normal"
         }
[API 2025-11-10 12:00:00.456] ✓ 201 POST /api/accounts/generate (333ms)
[API 2025-11-10 12:00:00.456]   Response Size: 1.2 KB
```

### Frontend Logging

API client logs all requests/responses:

```
[API 2025-11-10T12:00:00.123Z] → POST http://localhost:8080/api/accounts/generate
[API 2025-11-10T12:00:00.123Z] Request Body: { count: 5, priority: "normal" }
[API 2025-11-10T12:00:00.456Z] ← 201 POST /api/accounts/generate
[API 2025-11-10T12:00:00.456Z] Response: { success: true, job_ids: [...] }
```

---

## CORS Configuration

### Development
Allows requests from common development origins:
- `http://localhost:3000`
- `http://localhost:5173`
- `http://localhost:5174`
- `http://127.0.0.1:*`

### Production
Uses environment variable `ALLOWED_ORIGINS` for explicit whitelisting:

```bash
ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
```

**IMPORTANT**: Update `getAllowedOrigins()` in `backend/main.go` with your production domains.

---

## Rate Limiting

Rate limiting is applied to sensitive endpoints (e.g., `/api/accounts/generate`).

**Default Limits:**
- 10 requests per minute per IP
- Returns `429 Too Many Requests` when exceeded

**Rate Limit Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "message": "Too many requests, please try again later",
  "retry_after_seconds": 45
}
```

**Headers:**
- `Retry-After`: Seconds until limit resets

---

## Middleware Stack

1. **Recover**: Panic recovery
2. **Request ID**: Unique ID for each request
3. **Enhanced Logger**: Comprehensive request/response logging
4. **CORS**: Cross-origin resource sharing
5. **Request Validator**: Content-Type validation
6. **Rate Limiter**: Request rate limiting (select endpoints)

---

## Testing

### Manual Testing

Use the provided `backend/test_api_integration.http` file with REST Client extension:

1. Install "REST Client" VS Code extension
2. Open `backend/test_api_integration.http`
3. Click "Send Request" above each endpoint
4. View responses in separate panel

### Automated Testing

```bash
# Backend tests
cd backend
go test ./... -v

# Frontend tests
cd dashboard
npm test
```

---

## Environment Variables

### Backend (`.env`)
```env
# Server
SERVER_HOST=localhost
SERVER_PORT=8080
SERVER_ENVIRONMENT=development

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=botrix
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DATABASE_SSL_MODE=disable

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# CORS (production)
ALLOWED_ORIGINS=https://yourdomain.com
```

### Frontend (`dashboard/.env`)
```env
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080/ws
```

---

## Type Safety

All TypeScript types in `dashboard/src/types/index.ts` match Go models:

- `Account` → `models.Account`
- `Job` → `models.Job`
- `AccountStats` → `models.AccountStats`
- `JobStats` → `models.JobStats`
- `Stats` → `handlers.StatsResponse`

**Fields are synchronized** between backend and frontend for type safety.

---

## Best Practices

### Backend
1. ✅ Always return `{ success: bool }` in responses
2. ✅ Use consistent error format
3. ✅ Log sensitive operations
4. ✅ Validate all inputs
5. ✅ Use appropriate HTTP status codes
6. ✅ Implement rate limiting on write endpoints
7. ✅ Enable CORS only for trusted origins in production

### Frontend
1. ✅ Always check `response.data.success`
2. ✅ Use `ApiError` for error handling
3. ✅ Show user-friendly error messages
4. ✅ Log API calls for debugging
5. ✅ Implement loading states
6. ✅ Handle WebSocket reconnection
7. ✅ Validate user input before API calls

---

## Troubleshooting

### Backend Not Responding
```bash
# Check if backend is running
curl http://localhost:8080/health

# Check logs
tail -f logs/backend.log
```

### CORS Errors
- Verify `ALLOWED_ORIGINS` includes your frontend URL
- Check browser console for specific CORS error
- Ensure credentials are sent if needed

### WebSocket Connection Failed
- Check firewall rules
- Verify WebSocket URL in dashboard `.env`
- Check backend logs for WebSocket errors

### Database Connection Issues
- Verify PostgreSQL is running
- Check database credentials in `.env`
- Test connection: `psql -h localhost -U postgres -d botrix`

### Redis Connection Issues
- Verify Redis is running
- Check Redis credentials
- Test connection: `redis-cli ping`

---

## API Changelog

### v1.0.0 (Current)
- ✅ All CRUD endpoints for accounts
- ✅ Job management and tracking
- ✅ Real-time WebSocket updates
- ✅ Comprehensive statistics
- ✅ Enhanced logging and error handling
- ✅ Rate limiting
- ✅ CORS configuration
- ✅ Health checks

---

## Support

For issues or questions:
1. Check logs: `backend/logs/` and browser console
2. Review this documentation
3. Test with `test_api_integration.http`
4. Check GitHub issues

---

**Last Updated**: November 10, 2025  
**Version**: 1.0.0
