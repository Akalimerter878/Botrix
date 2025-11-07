# QueueService Quick Reference

## Initialization
```go
queue, err := services.NewQueueService(cfg)
defer queue.Close()
```

## Core Operations

### Add Job
```go
job := models.Job{ID: uuid.New().String(), Priority: 1}
jobID, err := queue.AddJob(job)
```

### Get Status
```go
status, err := queue.GetJobStatus(jobID)
```

### Update Status
```go
err := queue.UpdateJobStatus(jobID, "running")
```

### Get Pending Jobs
```go
jobs, err := queue.GetPendingJobs()
```

### Subscribe to Updates
```go
pubsub, err := queue.Subscribe("")
defer pubsub.Close()
ch := pubsub.Channel()
for msg := range ch {
    log.Println(msg.Payload)
}
```

## Job Processing

### Dequeue
```go
job, err := queue.DequeueJob()
if job == nil {
    // Queue empty
}
```

### Complete
```go
err := queue.CompleteJob(jobID)
```

### Fail (with re-queue)
```go
err := queue.FailJob(jobID, true, job)
```

### Cancel
```go
err := queue.CancelJob(jobID)
```

## Statistics

### Queue Length
```go
count, _ := queue.GetQueueLength()
```

### Processing Count
```go
count, _ := queue.GetProcessingCount()
```

### Full Stats
```go
stats, _ := queue.GetQueueStats()
// Returns: queue_length, processing_count, high_priority, normal_priority, low_priority
```

## Job States
- `pending` → `running` → `completed`
- `pending` → `running` → `failed`
- `pending` → `running` → `cancelled`
- Failed jobs can be re-queued

## Priority Levels
- `PriorityHigh = 2` (processed first)
- `PriorityNormal = 1` (default)
- `PriorityLow = 0` (processed last)

## TTL
- All jobs expire after **1 hour** (3600 seconds)
- Applies to: job data, status, results

## Pub/Sub Events
- `job_added`
- `status_updated`
- `job_completed`
- `job_failed`
- `job_cancelled`

## Redis Keys
```
botrix:jobs:queue         → Sorted Set (priority queue)
botrix:jobs:processing    → Set (active jobs)
botrix:jobs:status:<id>   → String (status)
botrix:jobs:data:<id>     → String (job JSON)
botrix:jobs:results:<id>  → String (results)
botrix:jobs:updates       → Pub/Sub channel
```

## Error Handling
```go
if err == redis.Nil {
    // Not found
}
if err != nil {
    // Redis error
}
```

## Common Patterns

### Worker Loop
```go
for {
    job, _ := queue.DequeueJob()
    if job == nil {
        time.Sleep(10 * time.Second)
        continue
    }
    
    if err := process(job); err != nil {
        queue.FailJob(job.ID, true, job)
    } else {
        queue.CompleteJob(job.ID)
    }
}
```

### Monitoring
```go
go func() {
    pubsub, _ := queue.Subscribe("")
    defer pubsub.Close()
    
    for msg := range pubsub.Channel() {
        log.Printf("Update: %s", msg.Payload)
    }
}()
```

## Health Check
```go
if err := queue.Health(); err != nil {
    return fiber.NewError(503, "Queue unavailable")
}
```

## Documentation
See `QUEUE_DOCUMENTATION.md` for complete API reference (800+ lines)
