package services

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"botrix-backend/config"
	"botrix-backend/models"

	"github.com/go-redis/redis/v8"
)

// QueueService handles job queue operations using Redis
type QueueService struct {
	client *redis.Client
	ctx    context.Context
	config *config.Config
}

// JobPriority represents job priority levels
type JobPriority int

const (
	PriorityLow    JobPriority = 0
	PriorityNormal JobPriority = 1
	PriorityHigh   JobPriority = 2
)

const (
	// Queue keys
	JobQueueKey       = "botrix:jobs:queue"
	JobProcessingKey  = "botrix:jobs:processing"
	JobStatusKey      = "botrix:jobs:status:"
	JobDataKey        = "botrix:jobs:data:"
	JobResultsKey     = "botrix:jobs:results:"
	JobUpdatesChannel = "botrix:jobs:updates"

	// Job TTL in seconds (1 hour)
	JobTTL = 3600
)

// NewQueueService creates a new queue service
func NewQueueService(cfg *config.Config) (*QueueService, error) {
	ctx := context.Background()

	client := redis.NewClient(&redis.Options{
		Addr:     cfg.GetRedisAddress(),
		Password: cfg.Redis.Password,
		DB:       cfg.Redis.DB,
	})

	// Test connection
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	log.Printf("[QueueService] Successfully connected to Redis at %s", cfg.GetRedisAddress())

	return &QueueService{
		client: client,
		ctx:    ctx,
		config: cfg,
	}, nil
}

// Close closes the Redis connection
func (q *QueueService) Close() error {
	log.Println("[QueueService] Closing Redis connection")
	return q.client.Close()
}

// GetRedisClient returns the underlying Redis client for WebSocket subscriptions
func (q *QueueService) GetRedisClient() *redis.Client {
	return q.client
}

// Health checks the Redis connection
func (q *QueueService) Health() error {
	return q.client.Ping(q.ctx).Err()
}

// AddJob adds a job to the queue and returns the job ID
func (q *QueueService) AddJob(job models.Job) (string, error) {
	if job.ID == "" {
		return "", fmt.Errorf("job ID cannot be empty")
	}

	// Marshal job data
	jobData, err := json.Marshal(job)
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to marshal job %s: %v", job.ID, err)
		return "", fmt.Errorf("failed to marshal job: %w", err)
	}

	// Store job data with TTL
	jobDataKey := fmt.Sprintf("%s%s", JobDataKey, job.ID)
	if err := q.client.Set(q.ctx, jobDataKey, jobData, time.Duration(JobTTL)*time.Second).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to store job data %s: %v", job.ID, err)
		return "", fmt.Errorf("failed to store job data: %w", err)
	}

	// Set initial status
	if err := q.UpdateJobStatus(job.ID, string(models.JobStatusPending)); err != nil {
		log.Printf("[QueueService] ERROR: Failed to set initial status for job %s: %v", job.ID, err)
		return "", err
	}

	// Calculate priority score (lower score = higher priority)
	// High priority: -2, Normal: -1, Low: 0
	priorityScore := float64(-job.Priority)

	// Add to priority queue (sorted set)
	if err := q.client.ZAdd(q.ctx, JobQueueKey, &redis.Z{
		Score:  priorityScore,
		Member: job.ID,
	}).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to enqueue job %s: %v", job.ID, err)
		return "", fmt.Errorf("failed to enqueue job: %w", err)
	}

	// Set TTL on queue entry
	q.client.Expire(q.ctx, JobQueueKey, time.Duration(JobTTL)*time.Second)

	log.Printf("[QueueService] Job %s added to queue with priority %d (score: %.1f)",
		job.ID, job.Priority, priorityScore)

	// Publish update notification
	q.publishUpdate(job.ID, "job_added", map[string]interface{}{
		"job_id":   job.ID,
		"status":   string(models.JobStatusPending),
		"priority": job.Priority,
	})

	return job.ID, nil
}

// GetJobStatus returns the current status of a job
func (q *QueueService) GetJobStatus(jobID string) (string, error) {
	if jobID == "" {
		return "", fmt.Errorf("job ID cannot be empty")
	}

	statusKey := fmt.Sprintf("%s%s", JobStatusKey, jobID)
	status, err := q.client.Get(q.ctx, statusKey).Result()

	if err == redis.Nil {
		log.Printf("[QueueService] Job %s status not found", jobID)
		return "", fmt.Errorf("job status not found")
	}

	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to get status for job %s: %v", jobID, err)
		return "", fmt.Errorf("failed to get job status: %w", err)
	}

	return status, nil
}

// UpdateJobStatus updates the status of a job
func (q *QueueService) UpdateJobStatus(jobID, status string) error {
	if jobID == "" {
		return fmt.Errorf("job ID cannot be empty")
	}

	// Validate status
	validStatuses := map[string]bool{
		string(models.JobStatusPending):   true,
		string(models.JobStatusRunning):   true,
		string(models.JobStatusCompleted): true,
		string(models.JobStatusFailed):    true,
		string(models.JobStatusCancelled): true,
		"processing":                      true, // Alias for running
	}

	if !validStatuses[status] {
		return fmt.Errorf("invalid job status: %s", status)
	}

	// Normalize "processing" to "running"
	if status == "processing" {
		status = string(models.JobStatusRunning)
	}

	statusKey := fmt.Sprintf("%s%s", JobStatusKey, jobID)

	// Set status with TTL
	if err := q.client.Set(q.ctx, statusKey, status, time.Duration(JobTTL)*time.Second).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to update status for job %s: %v", jobID, err)
		return fmt.Errorf("failed to update job status: %w", err)
	}

	log.Printf("[QueueService] Job %s status updated to: %s", jobID, status)

	// Publish status update
	q.publishUpdate(jobID, "status_updated", map[string]interface{}{
		"job_id": jobID,
		"status": status,
	})

	// If job is completed/failed/cancelled, clean up queue entries
	if status == string(models.JobStatusCompleted) ||
		status == string(models.JobStatusFailed) ||
		status == string(models.JobStatusCancelled) {
		q.removeFromQueues(jobID)
	}

	return nil
}

// GetPendingJobs retrieves all pending jobs from the queue
func (q *QueueService) GetPendingJobs() ([]models.Job, error) {
	// Get all job IDs from the queue (sorted by priority)
	jobIDs, err := q.client.ZRange(q.ctx, JobQueueKey, 0, -1).Result()
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to get pending jobs: %v", err)
		return nil, fmt.Errorf("failed to get pending jobs: %w", err)
	}

	if len(jobIDs) == 0 {
		log.Println("[QueueService] No pending jobs in queue")
		return []models.Job{}, nil
	}

	// Retrieve job data for each ID
	jobs := make([]models.Job, 0, len(jobIDs))
	for _, jobID := range jobIDs {
		job, err := q.getJobData(jobID)
		if err != nil {
			log.Printf("[QueueService] WARNING: Failed to get data for job %s: %v", jobID, err)
			continue
		}

		// Verify job is actually pending
		status, err := q.GetJobStatus(jobID)
		if err == nil && status == string(models.JobStatusPending) {
			jobs = append(jobs, *job)
		}
	}

	log.Printf("[QueueService] Retrieved %d pending jobs", len(jobs))
	return jobs, nil
}

// Subscribe creates a pub/sub subscription for real-time job updates
func (q *QueueService) Subscribe(channel string) (*redis.PubSub, error) {
	if channel == "" {
		channel = JobUpdatesChannel
	}

	pubsub := q.client.Subscribe(q.ctx, channel)

	// Wait for confirmation
	_, err := pubsub.Receive(q.ctx)
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to subscribe to channel %s: %v", channel, err)
		return nil, fmt.Errorf("failed to subscribe: %w", err)
	}

	log.Printf("[QueueService] Subscribed to channel: %s", channel)
	return pubsub, nil
}

// EnqueueJob adds a job to the queue (wrapper for AddJob for backward compatibility)
func (q *QueueService) EnqueueJob(job *models.Job) error {
	if job == nil {
		return fmt.Errorf("job cannot be nil")
	}
	_, err := q.AddJob(*job)
	return err
}

// DequeueJob retrieves the next job from the queue (highest priority)
func (q *QueueService) DequeueJob() (*models.Job, error) {
	// Get the job with the lowest score (highest priority)
	result, err := q.client.ZPopMin(q.ctx, JobQueueKey, 1).Result()

	if err == redis.Nil || len(result) == 0 {
		return nil, nil // Queue is empty
	}

	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to dequeue job: %v", err)
		return nil, fmt.Errorf("failed to dequeue job: %w", err)
	}

	// Get job ID from the result
	jobID, ok := result[0].Member.(string)
	if !ok {
		log.Printf("[QueueService] ERROR: Invalid job ID type in queue")
		return nil, fmt.Errorf("invalid job ID type")
	}

	// Retrieve job data
	job, err := q.getJobData(jobID)
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to get job data for %s: %v", jobID, err)
		return nil, err
	}

	// Move to processing set
	if err := q.client.SAdd(q.ctx, JobProcessingKey, job.ID).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to add job %s to processing set: %v", job.ID, err)
		return nil, fmt.Errorf("failed to add to processing set: %w", err)
	}

	// Update status to running
	if err := q.UpdateJobStatus(job.ID, string(models.JobStatusRunning)); err != nil {
		log.Printf("[QueueService] WARNING: Failed to update job status to running: %v", err)
	}

	log.Printf("[QueueService] Job %s dequeued for processing", job.ID)
	return job, nil
}

// CompleteJob marks a job as completed
func (q *QueueService) CompleteJob(jobID string) error {
	if jobID == "" {
		return fmt.Errorf("job ID cannot be empty")
	}

	// Update status to completed
	if err := q.UpdateJobStatus(jobID, string(models.JobStatusCompleted)); err != nil {
		return err
	}

	// Remove from processing set
	if err := q.client.SRem(q.ctx, JobProcessingKey, jobID).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to remove job %s from processing set: %v", jobID, err)
	}

	log.Printf("[QueueService] Job %s marked as completed", jobID)

	// Publish completion notification
	q.publishUpdate(jobID, "job_completed", map[string]interface{}{
		"job_id": jobID,
		"status": string(models.JobStatusCompleted),
	})

	return nil
}

// FailJob marks a job as failed and optionally re-queues it
func (q *QueueService) FailJob(jobID string, requeue bool, job *models.Job) error {
	if jobID == "" {
		return fmt.Errorf("job ID cannot be empty")
	}

	// Update status to failed
	if err := q.UpdateJobStatus(jobID, string(models.JobStatusFailed)); err != nil {
		return err
	}

	// Remove from processing set
	if err := q.client.SRem(q.ctx, JobProcessingKey, jobID).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to remove job %s from processing set: %v", jobID, err)
	}

	if requeue && job != nil {
		// Re-queue the job with lower priority
		log.Printf("[QueueService] Re-queuing failed job %s with reduced priority", jobID)
		job.Priority = job.Priority - 1
		if job.Priority < 0 {
			job.Priority = 0
		}
		return q.EnqueueJob(job)
	}

	log.Printf("[QueueService] Job %s marked as failed", jobID)

	// Publish failure notification
	q.publishUpdate(jobID, "job_failed", map[string]interface{}{
		"job_id": jobID,
		"status": string(models.JobStatusFailed),
	})

	return nil
}

// CancelJob marks a job as cancelled
func (q *QueueService) CancelJob(jobID string) error {
	if jobID == "" {
		return fmt.Errorf("job ID cannot be empty")
	}

	// Update status to cancelled
	if err := q.UpdateJobStatus(jobID, string(models.JobStatusCancelled)); err != nil {
		return err
	}

	// Remove from processing set
	if err := q.client.SRem(q.ctx, JobProcessingKey, jobID).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to remove job %s from processing set: %v", jobID, err)
	}

	// Remove from queue
	if err := q.client.ZRem(q.ctx, JobQueueKey, jobID).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to remove job %s from queue: %v", jobID, err)
	}

	log.Printf("[QueueService] Job %s cancelled", jobID)

	// Publish cancellation notification
	q.publishUpdate(jobID, "job_cancelled", map[string]interface{}{
		"job_id": jobID,
		"status": string(models.JobStatusCancelled),
	})

	return nil
}

// GetQueueLength returns the number of jobs in the queue
func (q *QueueService) GetQueueLength() (int64, error) {
	count, err := q.client.ZCard(q.ctx, JobQueueKey).Result()
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to get queue length: %v", err)
		return 0, err
	}
	return count, nil
}

// GetProcessingCount returns the number of jobs being processed
func (q *QueueService) GetProcessingCount() (int64, error) {
	count, err := q.client.SCard(q.ctx, JobProcessingKey).Result()
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to get processing count: %v", err)
		return 0, err
	}
	return count, nil
}

// IsJobProcessing checks if a job is currently being processed
func (q *QueueService) IsJobProcessing(jobID string) (bool, error) {
	if jobID == "" {
		return false, fmt.Errorf("job ID cannot be empty")
	}

	isProcessing, err := q.client.SIsMember(q.ctx, JobProcessingKey, jobID).Result()
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to check if job %s is processing: %v", jobID, err)
		return false, err
	}
	return isProcessing, nil
}

// SaveJobResult saves the result of a job execution with TTL
func (q *QueueService) SaveJobResult(jobID string, result interface{}) error {
	if jobID == "" {
		return fmt.Errorf("job ID cannot be empty")
	}

	resultData, err := json.Marshal(result)
	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to marshal result for job %s: %v", jobID, err)
		return fmt.Errorf("failed to marshal result: %w", err)
	}

	key := fmt.Sprintf("%s%s", JobResultsKey, jobID)
	if err := q.client.Set(q.ctx, key, resultData, time.Duration(JobTTL)*time.Second).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to save result for job %s: %v", jobID, err)
		return fmt.Errorf("failed to save result: %w", err)
	}

	log.Printf("[QueueService] Result saved for job %s", jobID)
	return nil
}

// GetJobResult retrieves the result of a job
func (q *QueueService) GetJobResult(jobID string) (string, error) {
	if jobID == "" {
		return "", fmt.Errorf("job ID cannot be empty")
	}

	key := fmt.Sprintf("%s%s", JobResultsKey, jobID)
	result, err := q.client.Get(q.ctx, key).Result()

	if err == redis.Nil {
		log.Printf("[QueueService] Result not found for job %s", jobID)
		return "", fmt.Errorf("job result not found")
	}

	if err != nil {
		log.Printf("[QueueService] ERROR: Failed to get result for job %s: %v", jobID, err)
		return "", err
	}

	return result, nil
}

// ClearQueue removes all jobs from the queue
func (q *QueueService) ClearQueue() error {
	if err := q.client.Del(q.ctx, JobQueueKey).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to clear queue: %v", err)
		return fmt.Errorf("failed to clear queue: %w", err)
	}
	log.Println("[QueueService] Queue cleared")
	return nil
}

// ClearProcessing removes all jobs from the processing set
func (q *QueueService) ClearProcessing() error {
	if err := q.client.Del(q.ctx, JobProcessingKey).Err(); err != nil {
		log.Printf("[QueueService] ERROR: Failed to clear processing set: %v", err)
		return fmt.Errorf("failed to clear processing set: %w", err)
	}
	log.Println("[QueueService] Processing set cleared")
	return nil
}

// GetQueueStats returns statistics about the queue
func (q *QueueService) GetQueueStats() (map[string]interface{}, error) {
	queueLength, err := q.GetQueueLength()
	if err != nil {
		return nil, err
	}

	processingCount, err := q.GetProcessingCount()
	if err != nil {
		return nil, err
	}

	// Get priority distribution
	highPriority, _ := q.client.ZCount(q.ctx, JobQueueKey, "-inf", "-2").Result()
	normalPriority, _ := q.client.ZCount(q.ctx, JobQueueKey, "-2", "-1").Result()
	lowPriority, _ := q.client.ZCount(q.ctx, JobQueueKey, "-1", "inf").Result()

	return map[string]interface{}{
		"queue_length":     queueLength,
		"processing_count": processingCount,
		"high_priority":    highPriority,
		"normal_priority":  normalPriority,
		"low_priority":     lowPriority,
		"ttl_seconds":      JobTTL,
	}, nil
}

// Helper methods

// getJobData retrieves job data from Redis
func (q *QueueService) getJobData(jobID string) (*models.Job, error) {
	key := fmt.Sprintf("%s%s", JobDataKey, jobID)
	jobData, err := q.client.Get(q.ctx, key).Result()

	if err == redis.Nil {
		return nil, fmt.Errorf("job data not found for job %s", jobID)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to get job data: %w", err)
	}

	var job models.Job
	if err := json.Unmarshal([]byte(jobData), &job); err != nil {
		return nil, fmt.Errorf("failed to unmarshal job data: %w", err)
	}

	return &job, nil
}

// removeFromQueues removes a job from all queue structures
func (q *QueueService) removeFromQueues(jobID string) {
	// Remove from queue
	if err := q.client.ZRem(q.ctx, JobQueueKey, jobID).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to remove job %s from queue: %v", jobID, err)
	}

	// Remove from processing set
	if err := q.client.SRem(q.ctx, JobProcessingKey, jobID).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to remove job %s from processing set: %v", jobID, err)
	}
}

// publishUpdate publishes a job update to the pub/sub channel
func (q *QueueService) publishUpdate(jobID, eventType string, data map[string]interface{}) {
	message := map[string]interface{}{
		"event":     eventType,
		"job_id":    jobID,
		"timestamp": time.Now().Unix(),
		"data":      data,
	}

	messageData, err := json.Marshal(message)
	if err != nil {
		log.Printf("[QueueService] WARNING: Failed to marshal update message: %v", err)
		return
	}

	if err := q.client.Publish(q.ctx, JobUpdatesChannel, messageData).Err(); err != nil {
		log.Printf("[QueueService] WARNING: Failed to publish update: %v", err)
	}
}
