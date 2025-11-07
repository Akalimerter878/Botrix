# REST API Endpoints Documentation

## Overview

Complete REST API documentation for the Botrix Backend API with request validation and rate limiting.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, no authentication is required. **TODO**: Implement API key or JWT authentication for production.

## Rate Limiting

The `/api/accounts/generate` endpoint is rate-limited to **10 requests per minute** per IP address.

**Rate Limit Response** (429 Too Many Requests):
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "message": "Too many requests, please try again later",
  "retry_after_seconds": 45
}
```

**Headers**:
- `Retry-After`: Seconds until rate limit resets

## Request Validation

All POST/PUT requests must have `Content-Type: application/json` header.

**Validation Error Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "Content-Type must be application/json"
}
```

---

## Endpoints

### 1. POST /api/accounts/generate

Generate multiple Kick.com accounts asynchronously.

**Rate Limit**: 10 requests/minute

**Request Body**:
```json
{
  "count": 5,
  "priority": "normal"
}
```

**Parameters**:
- `count` (required): Number of accounts to generate (1-100)
- `priority` (optional): Job priority - `"low"`, `"normal"`, or `"high"` (default: `"normal"`)

**Success Response** (201 Created):
```json
{
  "success": true,
  "job_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  ],
  "message": "Jobs queued successfully"
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "success": false,
  "error": "Count must be between 1 and 100"
}
```

```json
{
  "success": false,
  "error": "Priority must be 'low', 'normal', or 'high'"
}
```

500 Internal Server Error:
```json
{
  "success": false,
  "error": "Failed to create any jobs"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/api/accounts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "priority": "high"}'
```

---

### 2. GET /api/accounts

Retrieve generated accounts with pagination and filtering.

**Query Parameters**:
- `limit` (optional): Results per page (1-100, default: 20)
- `offset` (optional): Number of results to skip (default: 0)
- `status` (optional): Filter by status - `"active"`, `"banned"`, `"suspended"`, or `"completed"`

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "created_at": "2025-11-07T10:30:00Z",
      "updated_at": "2025-11-07T10:30:00Z",
      "email": "user@hotmail.com",
      "username": "kickuser123",
      "password": "SecurePass123!",
      "email_password": "EmailPass456!",
      "birthdate": "1995-06-15",
      "verification_code": "123456",
      "status": "active",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "kick_account_id": "123456",
      "notes": ""
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 150,
    "count": 20
  }
}
```

**Error Response** (500):
```json
{
  "success": false,
  "error": "Failed to retrieve accounts"
}
```

**Examples**:
```bash
# Get first 20 accounts
curl http://localhost:8080/api/accounts

# Get next 20 accounts
curl http://localhost:8080/api/accounts?limit=20&offset=20

# Filter by status
curl http://localhost:8080/api/accounts?status=completed

# Custom pagination
curl http://localhost:8080/api/accounts?limit=50&offset=100
```

---

### 3. GET /api/jobs/:jobId

Get job status and progress details.

**URL Parameters**:
- `jobId` (required): Job UUID

**Success Response** (200 OK):
```json
{
  "success": true,
  "job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-11-07T10:30:00Z",
    "updated_at": "2025-11-07T10:35:00Z",
    "count": 5,
    "status": "running",
    "progress": 3,
    "successful": 3,
    "failed": 0,
    "priority": 1,
    "started_at": "2025-11-07T10:31:00Z",
    "completed_at": null,
    "error_msg": ""
  },
  "progress": {
    "current": 3,
    "total": 5,
    "percentage": 60.0,
    "successful": 3,
    "failed": 0
  },
  "duration": "4m30s",
  "status": "running"
}
```

**Job Statuses**:
- `pending`: Waiting in queue
- `running`: Currently processing
- `completed`: Finished successfully
- `failed`: Failed with errors
- `cancelled`: Cancelled by user

**Error Responses**:

400 Bad Request:
```json
{
  "success": false,
  "error": "Job ID is required"
}
```

404 Not Found:
```json
{
  "success": false,
  "error": "Job not found"
}
```

**Example**:
```bash
curl http://localhost:8080/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

---

### 4. GET /api/stats

Get comprehensive statistics about account generation.

**Success Response** (200 OK):
```json
{
  "success": true,
  "total_accounts": 150,
  "success_rate": 95.5,
  "failure_rate": 4.5,
  "account_stats": {
    "total": 150,
    "active": 145,
    "banned": 3,
    "suspended": 2,
    "created_today": 25
  },
  "job_stats": {
    "total": 30,
    "pending": 2,
    "running": 1,
    "completed": 25,
    "failed": 2,
    "cancelled": 0
  },
  "queue_stats": {
    "queue_length": 2,
    "processing_count": 1,
    "high_priority": 1,
    "normal_priority": 1,
    "low_priority": 0,
    "ttl_seconds": 3600
  },
  "hotmail_pool_remaining": 0
}
```

**Fields**:
- `total_accounts`: Total accounts in database
- `success_rate`: Percentage of successful jobs
- `failure_rate`: Percentage of failed jobs
- `account_stats`: Account breakdown by status
- `job_stats`: Job breakdown by status
- `queue_stats`: Redis queue statistics
- `hotmail_pool_remaining`: Available email accounts (TODO: integrate with email pool)

**Error Response** (500):
```json
{
  "success": false,
  "error": "Failed to retrieve account statistics"
}
```

**Example**:
```bash
curl http://localhost:8080/api/stats
```

---

### 5. DELETE /api/accounts/:accountId

Soft delete an account (sets DeletedAt timestamp).

**URL Parameters**:
- `accountId` (required): Account ID (integer)

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Account deleted successfully",
  "account": {
    "id": 123,
    "username": "kickuser123",
    "email": "user@hotmail.com"
  }
}
```

**Error Responses**:

400 Bad Request:
```json
{
  "success": false,
  "error": "Invalid account ID"
}
```

404 Not Found:
```json
{
  "success": false,
  "error": "Account not found"
}
```

500 Internal Server Error:
```json
{
  "success": false,
  "error": "Failed to delete account"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8080/api/accounts/123
```

---

## Additional Endpoints

### GET /api/accounts/:id

Get a single account by ID.

**Example**:
```bash
curl http://localhost:8080/api/accounts/123
```

### POST /api/accounts

Create a single account job (legacy endpoint, use `/generate` instead).

### PUT /api/accounts/:id

Update account details.

### GET /api/jobs

List all jobs with pagination.

**Example**:
```bash
curl http://localhost:8080/api/jobs?limit=20&offset=0
```

### POST /api/jobs/:id/cancel

Cancel a pending or running job.

### GET /api/jobs/stats

Get job statistics with queue info.

---

## Health Check Endpoints

### GET /health

Full health check with service status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

### GET /health/ping

Simple ping/pong endpoint.

**Response**:
```json
{
  "message": "pong",
  "time": {
    "timestamp": 1699363800
  }
}
```

### GET /health/ready

Kubernetes readiness probe.

### GET /health/live

Kubernetes liveness probe.

---

## Error Handling

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message here",
  "message": "Additional context (optional)"
}
```

**HTTP Status Codes**:
- `200 OK`: Successful GET request
- `201 Created`: Successful POST request
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Middleware

### Request Validator

Validates:
- Content-Type header for POST/PUT requests
- Request format

### Rate Limiter

- **Endpoint**: `/api/accounts/generate`
- **Limit**: 10 requests per minute per IP
- **Window**: 1 minute (60 seconds)
- **Response**: 429 with `Retry-After` header

---

## Complete API Flow Example

### 1. Generate Accounts

```bash
curl -X POST http://localhost:8080/api/accounts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 10, "priority": "high"}'
```

Response:
```json
{
  "success": true,
  "job_ids": ["uuid1", "uuid2", "uuid3", ...],
  "message": "Jobs queued successfully"
}
```

### 2. Check Job Status

```bash
curl http://localhost:8080/api/jobs/uuid1
```

Response:
```json
{
  "success": true,
  "job": {...},
  "progress": {
    "current": 5,
    "total": 10,
    "percentage": 50.0
  },
  "status": "running"
}
```

### 3. Get Generated Accounts

```bash
curl http://localhost:8080/api/accounts?limit=10&status=completed
```

Response:
```json
{
  "success": true,
  "data": [...],
  "pagination": {...}
}
```

### 4. Get Statistics

```bash
curl http://localhost:8080/api/stats
```

Response:
```json
{
  "success": true,
  "total_accounts": 150,
  "success_rate": 95.5,
  ...
}
```

### 5. Delete Account

```bash
curl -X DELETE http://localhost:8080/api/accounts/123
```

Response:
```json
{
  "success": true,
  "message": "Account deleted successfully"
}
```

---

## Testing with cURL

### Generate 5 accounts
```bash
curl -X POST http://localhost:8080/api/accounts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "priority": "normal"}'
```

### List accounts (paginated)
```bash
curl "http://localhost:8080/api/accounts?limit=20&offset=0"
```

### Filter by status
```bash
curl "http://localhost:8080/api/accounts?status=completed"
```

### Get job status
```bash
curl http://localhost:8080/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

### Get statistics
```bash
curl http://localhost:8080/api/stats
```

### Delete account
```bash
curl -X DELETE http://localhost:8080/api/accounts/123
```

### Test rate limiting (run 11 times quickly)
```bash
for i in {1..11}; do
  curl -X POST http://localhost:8080/api/accounts/generate \
    -H "Content-Type: application/json" \
    -d '{"count": 1, "priority": "normal"}'
  sleep 0.1
done
```

---

## WebSocket/Real-time Updates (Future)

**TODO**: Implement WebSocket endpoint for real-time job updates

```
ws://localhost:8080/api/jobs/:jobId/stream
```

---

## Notes

1. **Soft Delete**: DELETE operations use GORM's soft delete (sets `deleted_at` timestamp)
2. **Pagination**: Default limit is 20, maximum is 100
3. **Rate Limiting**: Only applies to `/api/accounts/generate`
4. **TTL**: Jobs in Redis expire after 1 hour (3600 seconds)
5. **Priority Queue**: High priority jobs are processed first

---

## TODO

- [ ] Implement authentication (API keys or JWT)
- [ ] Add WebSocket support for real-time updates
- [ ] Integrate hotmail pool service
- [ ] Add bulk delete endpoint
- [ ] Add export endpoint (CSV/JSON)
- [ ] Add filtering by date range
- [ ] Add search by username/email
- [ ] Add account verification endpoint
- [ ] Add retry failed jobs endpoint
- [ ] Implement Redis-based rate limiting (instead of in-memory)
