package models

import (
	"time"

	"gorm.io/gorm"
)

// JobStatus represents the status of an account creation job
type JobStatus string

const (
	JobStatusPending   JobStatus = "pending"
	JobStatusRunning   JobStatus = "running"
	JobStatusCompleted JobStatus = "completed"
	JobStatusFailed    JobStatus = "failed"
	JobStatusCancelled JobStatus = "cancelled"
)

// Job represents an account creation job
type Job struct {
	ID        string         `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`

	// Job configuration
	Count    int    `gorm:"not null" json:"count"`
	Username string `json:"username,omitempty"`
	Password string `json:"password,omitempty"`

	// Job status
	Status   JobStatus `gorm:"default:'pending'" json:"status"`
	Progress int       `gorm:"default:0" json:"progress"`

	// Results
	Successful int `gorm:"default:0" json:"successful"`
	Failed     int `gorm:"default:0" json:"failed"`

	// Timing
	StartedAt   *time.Time `json:"started_at,omitempty"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`

	// Error tracking
	ErrorMsg string `gorm:"type:text" json:"error_msg,omitempty"`

	// Job metadata
	TestMode bool `gorm:"default:false" json:"test_mode"`
	Priority int  `gorm:"default:0" json:"priority"`
}

// JobCreateRequest represents a request to create a new job
type JobCreateRequest struct {
	Count    int    `json:"count" validate:"required,min=1,max=100"`
	Username string `json:"username,omitempty"`
	Password string `json:"password,omitempty"`
	TestMode bool   `json:"test_mode,omitempty"`
	Priority int    `json:"priority,omitempty"`
}

// JobResponse represents the response for job operations
type JobResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message,omitempty"`
	Job     *Job   `json:"job,omitempty"`
	Jobs    []Job  `json:"jobs,omitempty"`
	Error   string `json:"error,omitempty"`
}

// JobStats represents statistics about jobs
type JobStats struct {
	Total     int64 `json:"total"`
	Pending   int64 `json:"pending"`
	Running   int64 `json:"running"`
	Completed int64 `json:"completed"`
	Failed    int64 `json:"failed"`
	Cancelled int64 `json:"cancelled"`
}

// TableName specifies the table name for Job model
func (Job) TableName() string {
	return "jobs"
}

// IsCompleted checks if the job is in a terminal state
func (j *Job) IsCompleted() bool {
	return j.Status == JobStatusCompleted ||
		j.Status == JobStatusFailed ||
		j.Status == JobStatusCancelled
}

// CanBeCancelled checks if the job can be cancelled
func (j *Job) CanBeCancelled() bool {
	return j.Status == JobStatusPending || j.Status == JobStatusRunning
}

// GetDuration returns the duration of the job
func (j *Job) GetDuration() time.Duration {
	if j.StartedAt == nil {
		return 0
	}

	endTime := time.Now()
	if j.CompletedAt != nil {
		endTime = *j.CompletedAt
	}

	return endTime.Sub(*j.StartedAt)
}

// GetProgress returns the progress percentage (0-100)
func (j *Job) GetProgress() float64 {
	if j.Count == 0 {
		return 0
	}
	return (float64(j.Progress) / float64(j.Count)) * 100
}

// GetSuccessRate returns the success rate percentage
func (j *Job) GetSuccessRate() float64 {
	total := j.Successful + j.Failed
	if total == 0 {
		return 0
	}
	return (float64(j.Successful) / float64(total)) * 100
}

// Start marks the job as started
func (j *Job) Start() {
	j.Status = JobStatusRunning
	now := time.Now()
	j.StartedAt = &now
}

// Complete marks the job as completed
func (j *Job) Complete() {
	j.Status = JobStatusCompleted
	now := time.Now()
	j.CompletedAt = &now
}

// Fail marks the job as failed with an error message
func (j *Job) Fail(errorMsg string) {
	j.Status = JobStatusFailed
	j.ErrorMsg = errorMsg
	now := time.Now()
	j.CompletedAt = &now
}

// Cancel marks the job as cancelled
func (j *Job) Cancel() {
	j.Status = JobStatusCancelled
	now := time.Now()
	j.CompletedAt = &now
}

// IncrementProgress increments the progress counter
func (j *Job) IncrementProgress(successful bool) {
	j.Progress++
	if successful {
		j.Successful++
	} else {
		j.Failed++
	}
}

// ToJSON converts job to JSON-safe representation
func (j *Job) ToJSON() map[string]interface{} {
	result := map[string]interface{}{
		"id":         j.ID,
		"count":      j.Count,
		"status":     j.Status,
		"progress":   j.Progress,
		"successful": j.Successful,
		"failed":     j.Failed,
		"priority":   j.Priority,
		"created_at": j.CreatedAt,
		"updated_at": j.UpdatedAt,
	}

	if j.StartedAt != nil {
		result["started_at"] = j.StartedAt
		result["duration"] = j.GetDuration().String()
	}

	if j.CompletedAt != nil {
		result["completed_at"] = j.CompletedAt
	}

	if j.ErrorMsg != "" {
		result["error_msg"] = j.ErrorMsg
	}

	result["progress_percent"] = j.GetProgress()
	result["success_rate"] = j.GetSuccessRate()

	return result
}
