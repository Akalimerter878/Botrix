# QueueService Documentation

## Overview

The `QueueService` is a Redis-based job queue system for managing account creation jobs in the Botrix backend. It provides a priority queue with TTL, real-time updates via pub/sub, and comprehensive job lifecycle management.

## Features

- ✅ **Priority Queue**: Jobs are processed based on priority (High, Normal, Low)
- ✅ **Job TTL**: Jobs expire after 1 hour if not processed
- ✅ **Job States**: `pending`, `running`, `completed`, `failed`, `cancelled`
- ✅ **Real-time Updates**: Pub/Sub notifications for job status changes
- ✅ **Comprehensive Logging**: Detailed logs with `[QueueService]` prefix
- ✅ **Error Handling**: Graceful error handling with descriptive messages
- ✅ **Statistics**: Queue metrics and priority distribution

## Architecture

### Data Structures

The queue uses several Redis data structures:

1. **Sorted Set** (`botrix:jobs:queue`): Priority queue of pending jobs
   - Score: `-priority` (lower score = higher priority)
   - Member: Job ID

2. **Set** (`botrix:jobs:processing`): Currently processing jobs
   - Members: Job IDs

3. **Strings** with TTL:
   - `botrix:jobs:status:<job_id>`: Current job status
   - `botrix:jobs:data:<job_id>`: Complete job data (JSON)
   - `botrix:jobs:results:<job_id>`: Job execution results

4. **Pub/Sub** (`botrix:jobs:updates`): Real-time notifications

### Job Priority Levels

```go
const (
    PriorityLow    JobPriority = 0  // Score: 0
    PriorityNormal JobPriority = 1  // Score: -1
    PriorityHigh   JobPriority = 2  // Score: -2
)
```

Higher priority jobs are dequeued first.

## API Reference

### Initialization

#### NewQueueService

```go
func NewQueueService(cfg *config.Config) (*QueueService, error)
```

Creates a new queue service and tests Redis connection.

**Parameters:**
- `cfg`: Configuration object with Redis settings

**Returns:**
- `*QueueService`: Queue service instance
- `error`: Connection error, if any

**Example:**
```go
cfg, _ := config.LoadConfig()
queue, err := services.NewQueueService(cfg)
if err != nil {
    log.Fatalf("Failed to initialize queue: %v", err)
}
defer queue.Close()
```

### Core Operations

#### AddJob

```go
func (q *QueueService) AddJob(job models.Job) (string, error)
```

Adds a job to the queue with priority and TTL.

**Parameters:**
- `job`: Job object with ID, priority, and configuration

**Returns:**
- `string`: Job ID (same as input)
- `error`: Validation or Redis error

**Features:**
- Stores job data with 1-hour TTL
- Sets initial status to `pending`
- Adds to priority queue
- Publishes `job_added` event

**Example:**
```go
job := models.Job{
    ID:       uuid.New().String(),
    Count:    10,
    Priority: 2, // High priority
    Status:   models.JobStatusPending,
}

jobID, err := queue.AddJob(job)
if err != nil {
    log.Printf("Failed to add job: %v", err)
}
```

#### GetJobStatus

```go
func (q *QueueService) GetJobStatus(jobID string) (string, error)
```

Returns the current status of a job.

**Parameters:**
- `jobID`: Job identifier

**Returns:**
- `string`: Current status (`pending`, `running`, etc.)
- `error`: Not found or Redis error

**Example:**
```go
status, err := queue.GetJobStatus("job-123")
if err != nil {
    log.Printf("Job not found: %v", err)
} else {
    log.Printf("Job status: %s", status)
}
```

#### UpdateJobStatus

```go
func (q *QueueService) UpdateJobStatus(jobID, status string) error
```

Updates the status of a job with validation and notifications.

**Parameters:**
- `jobID`: Job identifier
- `status`: New status (`pending`, `running`, `completed`, `failed`, `cancelled`, `processing`)

**Returns:**
- `error`: Validation or Redis error

**Features:**
- Validates status values
- Normalizes `processing` → `running`
- Publishes `status_updated` event
- Cleans up queues for terminal states

**Example:**
```go
err := queue.UpdateJobStatus("job-123", "running")
if err != nil {
    log.Printf("Failed to update status: %v", err)
}
```

#### GetPendingJobs

```go
func (q *QueueService) GetPendingJobs() ([]models.Job, error)
```

Retrieves all pending jobs sorted by priority.

**Returns:**
- `[]models.Job`: Array of pending jobs (highest priority first)
- `error`: Redis error

**Example:**
```go
jobs, err := queue.GetPendingJobs()
if err != nil {
    log.Printf("Failed to get pending jobs: %v", err)
} else {
    log.Printf("Found %d pending jobs", len(jobs))
    for _, job := range jobs {
        log.Printf("Job %s: priority=%d", job.ID, job.Priority)
    }
}
```

#### Subscribe

```go
func (q *QueueService) Subscribe(channel string) (*redis.PubSub, error)
```

Creates a pub/sub subscription for real-time job updates.

**Parameters:**
- `channel`: Channel name (default: `botrix:jobs:updates`)

**Returns:**
- `*redis.PubSub`: Subscription object
- `error`: Redis error

**Example:**
```go
pubsub, err := queue.Subscribe("")
if err != nil {
    log.Fatalf("Failed to subscribe: %v", err)
}
defer pubsub.Close()

ch := pubsub.Channel()
for msg := range ch {
    log.Printf("Received update: %s", msg.Payload)
}
```

**Message Format:**
```json
{
  "event": "job_added|status_updated|job_completed|job_failed|job_cancelled",
  "job_id": "uuid",
  "timestamp": 1699999999,
  "data": {
    "job_id": "uuid",
    "status": "pending",
    "priority": 1
  }
}
```

### Queue Management

#### EnqueueJob (Backward Compatible)

```go
func (q *QueueService) EnqueueJob(job *models.Job) error
```

Wrapper around `AddJob` for backward compatibility.

**Parameters:**
- `job`: Pointer to job object

**Returns:**
- `error`: Validation or Redis error

**Example:**
```go
job := &models.Job{ID: "job-123", Priority: 1}
err := queue.EnqueueJob(job)
```

#### DequeueJob

```go
func (q *QueueService) DequeueJob() (*models.Job, error)
```

Retrieves and removes the highest priority job from the queue.

**Returns:**
- `*models.Job`: Job object (nil if queue is empty)
- `error`: Redis error

**Features:**
- Pops job with lowest score (highest priority)
- Moves job to processing set
- Updates status to `running`
- Returns `nil` if queue is empty (not an error)

**Example:**
```go
job, err := queue.DequeueJob()
if err != nil {
    log.Printf("Error: %v", err)
} else if job == nil {
    log.Println("Queue is empty")
} else {
    log.Printf("Processing job %s", job.ID)
    // Process job...
}
```

#### CompleteJob

```go
func (q *QueueService) CompleteJob(jobID string) error
```

Marks a job as completed.

**Parameters:**
- `jobID`: Job identifier

**Returns:**
- `error`: Redis error

**Features:**
- Updates status to `completed`
- Removes from processing set
- Publishes `job_completed` event
- Cleans up queue entries

**Example:**
```go
err := queue.CompleteJob("job-123")
if err != nil {
    log.Printf("Failed to complete job: %v", err)
}
```

#### FailJob

```go
func (q *QueueService) FailJob(jobID string, requeue bool, job *models.Job) error
```

Marks a job as failed with optional re-queuing.

**Parameters:**
- `jobID`: Job identifier
- `requeue`: Whether to re-queue the job
- `job`: Job object (required if requeue=true)

**Returns:**
- `error`: Redis error

**Features:**
- Updates status to `failed`
- Removes from processing set
- Optionally re-queues with reduced priority
- Publishes `job_failed` event

**Example:**
```go
// Fail without re-queue
err := queue.FailJob("job-123", false, nil)

// Fail and re-queue with lower priority
job := &models.Job{ID: "job-123", Priority: 2}
err := queue.FailJob("job-123", true, job)
```

#### CancelJob

```go
func (q *QueueService) CancelJob(jobID string) error
```

Cancels a pending or running job.

**Parameters:**
- `jobID`: Job identifier

**Returns:**
- `error`: Redis error

**Features:**
- Updates status to `cancelled`
- Removes from both queue and processing set
- Publishes `job_cancelled` event

**Example:**
```go
err := queue.CancelJob("job-123")
if err != nil {
    log.Printf("Failed to cancel job: %v", err)
}
```

### Statistics and Monitoring

#### GetQueueLength

```go
func (q *QueueService) GetQueueLength() (int64, error)
```

Returns the number of jobs in the queue.

**Example:**
```go
count, err := queue.GetQueueLength()
log.Printf("Queue length: %d", count)
```

#### GetProcessingCount

```go
func (q *QueueService) GetProcessingCount() (int64, error)
```

Returns the number of jobs currently being processed.

**Example:**
```go
count, err := queue.GetProcessingCount()
log.Printf("Processing: %d jobs", count)
```

#### IsJobProcessing

```go
func (q *QueueService) IsJobProcessing(jobID string) (bool, error)
```

Checks if a specific job is currently being processed.

**Example:**
```go
processing, err := queue.IsJobProcessing("job-123")
if processing {
    log.Println("Job is being processed")
}
```

#### GetQueueStats

```go
func (q *QueueService) GetQueueStats() (map[string]interface{}, error)
```

Returns comprehensive queue statistics.

**Returns:**
```json
{
  "queue_length": 10,
  "processing_count": 3,
  "high_priority": 2,
  "normal_priority": 5,
  "low_priority": 3,
  "ttl_seconds": 3600
}
```

**Example:**
```go
stats, err := queue.GetQueueStats()
if err != nil {
    log.Printf("Failed to get stats: %v", err)
} else {
    log.Printf("Queue stats: %+v", stats)
}
```

### Results Storage

#### SaveJobResult

```go
func (q *QueueService) SaveJobResult(jobID string, result interface{}) error
```

Saves job execution results with TTL.

**Parameters:**
- `jobID`: Job identifier
- `result`: Any JSON-serializable data

**Returns:**
- `error`: Marshaling or Redis error

**Example:**
```go
result := map[string]interface{}{
    "accounts_created": 10,
    "accounts_failed": 0,
    "duration_seconds": 120,
}

err := queue.SaveJobResult("job-123", result)
```

#### GetJobResult

```go
func (q *QueueService) GetJobResult(jobID string) (string, error)
```

Retrieves job execution results.

**Returns:**
- `string`: JSON-encoded result
- `error`: Not found or Redis error

**Example:**
```go
resultJSON, err := queue.GetJobResult("job-123")
if err != nil {
    log.Printf("Result not found: %v", err)
} else {
    var result map[string]interface{}
    json.Unmarshal([]byte(resultJSON), &result)
    log.Printf("Result: %+v", result)
}
```

### Cleanup Operations

#### ClearQueue

```go
func (q *QueueService) ClearQueue() error
```

Removes all jobs from the pending queue. **Use with caution!**

#### ClearProcessing

```go
func (q *QueueService) ClearProcessing() error
```

Removes all jobs from the processing set. **Use for cleanup only!**

#### Close

```go
func (q *QueueService) Close() error
```

Closes the Redis connection.

**Example:**
```go
defer queue.Close()
```

#### Health

```go
func (q *QueueService) Health() error
```

Checks Redis connection health.

**Example:**
```go
if err := queue.Health(); err != nil {
    log.Printf("Queue is unhealthy: %v", err)
}
```

## Job Lifecycle

### Complete Flow

```
1. CREATE
   AddJob() → Status: pending → Queue: added → Event: job_added

2. DEQUEUE
   DequeueJob() → Status: running → Processing set: added

3. COMPLETE/FAIL/CANCEL
   CompleteJob() → Status: completed → Cleanup → Event: job_completed
   FailJob()     → Status: failed → Optional re-queue → Event: job_failed
   CancelJob()   → Status: cancelled → Cleanup → Event: job_cancelled

4. TTL EXPIRATION (after 1 hour)
   All Redis keys auto-expire
```

### State Transitions

```
         ┌─────────────┐
         │   pending   │ ← AddJob()
         └──────┬──────┘
                │ DequeueJob()
                ▼
         ┌─────────────┐
         │   running   │
         └──────┬──────┘
                │
      ┌─────────┼─────────┬─────────┐
      │         │         │         │
      ▼         ▼         ▼         ▼
┌─────────┐ ┌─────┐ ┌─────────┐ ┌─────────┐
│completed│ │failed│ │cancelled│ │ requeue │
└─────────┘ └─────┘ └─────────┘ └────┬────┘
                                      │
                                      └──→ back to pending
```

## Usage Examples

### Basic Job Processing

```go
package main

import (
    "log"
    "time"
    
    "botrix-backend/config"
    "botrix-backend/models"
    "botrix-backend/services"
    
    "github.com/google/uuid"
)

func main() {
    // Initialize
    cfg, _ := config.LoadConfig()
    queue, err := services.NewQueueService(cfg)
    if err != nil {
        log.Fatalf("Failed to initialize queue: %v", err)
    }
    defer queue.Close()
    
    // Add a job
    job := models.Job{
        ID:       uuid.New().String(),
        Count:    5,
        Priority: 1, // Normal priority
        Status:   models.JobStatusPending,
    }
    
    jobID, err := queue.AddJob(job)
    if err != nil {
        log.Fatalf("Failed to add job: %v", err)
    }
    
    log.Printf("Job added: %s", jobID)
    
    // Process the job
    processingJob, err := queue.DequeueJob()
    if err != nil {
        log.Fatalf("Failed to dequeue: %v", err)
    }
    
    if processingJob != nil {
        log.Printf("Processing job: %s", processingJob.ID)
        
        // Simulate work
        time.Sleep(2 * time.Second)
        
        // Complete the job
        if err := queue.CompleteJob(processingJob.ID); err != nil {
            log.Printf("Failed to complete: %v", err)
        }
    }
}
```

### Real-time Monitoring

```go
func monitorJobs(queue *services.QueueService) {
    pubsub, err := queue.Subscribe("")
    if err != nil {
        log.Fatalf("Failed to subscribe: %v", err)
    }
    defer pubsub.Close()
    
    ch := pubsub.Channel()
    for msg := range ch {
        var update map[string]interface{}
        json.Unmarshal([]byte(msg.Payload), &update)
        
        event := update["event"].(string)
        jobID := update["data"].(map[string]interface{})["job_id"].(string)
        
        log.Printf("Event: %s | Job: %s", event, jobID)
    }
}
```

### Worker Pattern

```go
func worker(queue *services.QueueService) {
    for {
        job, err := queue.DequeueJob()
        if err != nil {
            log.Printf("Error dequeuing: %v", err)
            time.Sleep(5 * time.Second)
            continue
        }
        
        if job == nil {
            // Queue is empty
            time.Sleep(10 * time.Second)
            continue
        }
        
        log.Printf("Processing job %s", job.ID)
        
        // Process the job
        err = processJob(job)
        
        if err != nil {
            // Failed - re-queue with lower priority
            log.Printf("Job failed: %v", err)
            queue.FailJob(job.ID, true, job)
        } else {
            // Success
            log.Printf("Job completed: %s", job.ID)
            queue.CompleteJob(job.ID)
        }
    }
}
```

## Configuration

### Environment Variables

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### Constants

```go
const (
    JobQueueKey       = "botrix:jobs:queue"       // Sorted set
    JobProcessingKey  = "botrix:jobs:processing"  // Set
    JobStatusKey      = "botrix:jobs:status:"     // String prefix
    JobDataKey        = "botrix:jobs:data:"       // String prefix
    JobResultsKey     = "botrix:jobs:results:"    // String prefix
    JobUpdatesChannel = "botrix:jobs:updates"     // Pub/sub channel
    
    JobTTL = 3600  // 1 hour in seconds
)
```

## Error Handling

All methods return descriptive errors:

```go
// Empty values
"job ID cannot be empty"
"job cannot be nil"

// Invalid states
"invalid job status: <status>"

// Not found
"job status not found"
"job data not found for job <id>"
"job result not found"

// Redis errors
"failed to connect to Redis: <error>"
"failed to enqueue job: <error>"
"failed to dequeue job: <error>"
```

## Logging

All logs use the `[QueueService]` prefix with severity levels:

- **INFO**: `Job <id> added to queue with priority <n>`
- **WARNING**: `Failed to remove job <id> from processing set`
- **ERROR**: `Failed to marshal job <id>: <error>`

## Performance Considerations

### Redis Operations

- **AddJob**: 4 operations (SET, SET, ZAdd, EXPIRE)
- **DequeueJob**: 3 operations (ZPopMin, SAdd, SET)
- **GetPendingJobs**: O(n) where n = queue size
- **GetQueueStats**: 5 operations (parallel)

### TTL Management

All job-related keys expire after 1 hour to prevent memory leaks:
- Job data
- Job status
- Job results

The queue itself doesn't expire, but individual job IDs are removed when processed.

### Pub/Sub

Publishing is fire-and-forget. Failed publishes are logged but don't block operations.

## Best Practices

1. **Always defer Close()**
   ```go
   queue, _ := services.NewQueueService(cfg)
   defer queue.Close()
   ```

2. **Check for nil on DequeueJob()**
   ```go
   job, err := queue.DequeueJob()
   if err != nil { /* handle error */ }
   if job == nil { /* queue is empty */ }
   ```

3. **Use Health() for readiness checks**
   ```go
   if err := queue.Health(); err != nil {
       return fiber.NewError(503, "Queue unavailable")
   }
   ```

4. **Subscribe in a goroutine**
   ```go
   go func() {
       pubsub, _ := queue.Subscribe("")
       defer pubsub.Close()
       // Process messages...
   }()
   ```

5. **Handle re-queuing carefully**
   ```go
   if shouldRetry(err) {
       queue.FailJob(jobID, true, job)
   } else {
       queue.FailJob(jobID, false, nil)
   }
   ```

## Troubleshooting

### Connection Issues

```
ERROR: Failed to connect to Redis: connection refused
```
**Solution**: Ensure Redis is running and accessible.

### Jobs Not Dequeuing

```
INFO: No pending jobs in queue
```
**Solution**: Check if jobs were added successfully and haven't expired.

### TTL Expiration

Jobs expire after 1 hour. For long-running jobs:
1. Update TTL in constants
2. Periodically refresh TTL: `client.Expire(ctx, key, newTTL)`

### Memory Issues

```
WARNING: Redis memory usage high
```
**Solution**: Increase TTL or implement result cleanup.

## Testing

### Unit Tests

```go
func TestAddJob(t *testing.T) {
    queue := setupTestQueue(t)
    defer queue.Close()
    
    job := models.Job{ID: "test-123", Priority: 1}
    jobID, err := queue.AddJob(job)
    
    assert.NoError(t, err)
    assert.Equal(t, "test-123", jobID)
}
```

### Integration Tests

```go
func TestCompleteWorkflow(t *testing.T) {
    queue := setupTestQueue(t)
    defer queue.Close()
    
    // Add
    job := models.Job{ID: "test-123"}
    queue.AddJob(job)
    
    // Dequeue
    dequeuedJob, _ := queue.DequeueJob()
    assert.Equal(t, "test-123", dequeuedJob.ID)
    
    // Complete
    err := queue.CompleteJob("test-123")
    assert.NoError(t, err)
    
    // Verify status
    status, _ := queue.GetJobStatus("test-123")
    assert.Equal(t, "completed", status)
}
```

## See Also

- [Database Service Documentation](database.go)
- [Job Model Documentation](../models/job.go)
- [Backend README](../README.md)
