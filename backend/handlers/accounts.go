package handlers

import (
	"log"
	"strconv"
	"strings"
	"time"

	"botrix-backend/models"
	"botrix-backend/services"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// AccountsHandler handles account-related requests
type AccountsHandler struct {
	db    *services.Database
	queue *services.QueueService
}

// GenerateAccountsRequest represents the request to generate accounts
type GenerateAccountsRequest struct {
	Count    int    `json:"count" validate:"required,min=1,max=100"`
	Priority string `json:"priority,omitempty"` // "low", "normal", "high"
}

// GenerateAccountsResponse represents the response for account generation
type GenerateAccountsResponse struct {
	Success bool     `json:"success"`
	JobIDs  []string `json:"job_ids"`
	Message string   `json:"message"`
	Error   string   `json:"error,omitempty"`
}

// StatsResponse represents the comprehensive statistics response
type StatsResponse struct {
	Success          bool                   `json:"success"`
	TotalAccounts    int64                  `json:"total_accounts"`
	SuccessRate      float64                `json:"success_rate"`
	FailureRate      float64                `json:"failure_rate"`
	AccountStats     *models.AccountStats   `json:"account_stats"`
	JobStats         *models.JobStats       `json:"job_stats"`
	QueueStats       map[string]interface{} `json:"queue_stats"`
	HotmailRemaining int                    `json:"hotmail_pool_remaining"`
	Error            string                 `json:"error,omitempty"`
}

// NewAccountsHandler creates a new accounts handler
func NewAccountsHandler(db *services.Database, queue *services.QueueService) *AccountsHandler {
	return &AccountsHandler{
		db:    db,
		queue: queue,
	}
}

// GenerateAccounts handles POST /api/accounts/generate
func (h *AccountsHandler) GenerateAccounts(c *fiber.Ctx) error {
	var req GenerateAccountsRequest

	// Parse request body
	if err := c.BodyParser(&req); err != nil {
		log.Printf("[AccountsHandler] Invalid request body: %v", err)
		return c.Status(fiber.StatusBadRequest).JSON(GenerateAccountsResponse{
			Success: false,
			Error:   "Invalid request body",
		})
	}

	// Validate count
	if req.Count < 1 || req.Count > 100 {
		return c.Status(fiber.StatusBadRequest).JSON(GenerateAccountsResponse{
			Success: false,
			Error:   "Count must be between 1 and 100",
		})
	}

	// Parse priority
	priority := 1 // Default: normal
	switch strings.ToLower(req.Priority) {
	case "low":
		priority = 0
	case "normal", "":
		priority = 1
	case "high":
		priority = 2
	default:
		return c.Status(fiber.StatusBadRequest).JSON(GenerateAccountsResponse{
			Success: false,
			Error:   "Priority must be 'low', 'normal', or 'high'",
		})
	}

	// Create jobs (one job per account for better tracking)
	jobIDs := make([]string, 0, req.Count)

	for i := 0; i < req.Count; i++ {
		job := models.Job{
			ID:       uuid.New().String(),
			Count:    1, // One account per job
			Status:   models.JobStatusPending,
			Priority: priority,
		}

		// Save job to database
		if err := h.db.CreateJob(&job); err != nil {
			log.Printf("[AccountsHandler] Failed to create job: %v", err)
			continue
		}

		// Add to Redis queue
		if _, err := h.queue.AddJob(job); err != nil {
			log.Printf("[AccountsHandler] Failed to enqueue job %s: %v", job.ID, err)
			// Mark job as failed in database
			job.Status = models.JobStatusFailed
			job.ErrorMsg = err.Error()
			h.db.UpdateJob(&job)
			continue
		}

		jobIDs = append(jobIDs, job.ID)
	}

	if len(jobIDs) == 0 {
		return c.Status(fiber.StatusInternalServerError).JSON(GenerateAccountsResponse{
			Success: false,
			Error:   "Failed to create any jobs",
		})
	}

	log.Printf("[AccountsHandler] Created %d jobs for account generation", len(jobIDs))

	return c.Status(fiber.StatusCreated).JSON(GenerateAccountsResponse{
		Success: true,
		JobIDs:  jobIDs,
		Message: "Jobs queued successfully",
	})
}

// ListAccounts handles GET /api/accounts
func (h *AccountsHandler) ListAccounts(c *fiber.Ctx) error {
	// Parse pagination parameters
	limit, _ := strconv.Atoi(c.Query("limit", "20"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))
	status := c.Query("status", "") // Filter by status: active, banned, suspended

	// Validate and cap limit
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}

	// Get accounts from database
	accounts, err := h.db.ListAccounts(limit, offset)
	if err != nil {
		log.Printf("[AccountsHandler] Failed to retrieve accounts: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(models.AccountResponse{
			Success: false,
			Error:   "Failed to retrieve accounts",
		})
	}

	// Filter by status if specified
	if status != "" {
		filtered := make([]models.Account, 0)
		for _, account := range accounts {
			if strings.EqualFold(account.Status, status) {
				filtered = append(filtered, account)
			}
		}
		accounts = filtered
	}

	// Get total count for pagination info
	stats, _ := h.db.GetAccountStats()
	totalCount := stats.Total

	return c.JSON(fiber.Map{
		"success": true,
		"data":    accounts,
		"pagination": fiber.Map{
			"limit":  limit,
			"offset": offset,
			"total":  totalCount,
			"count":  len(accounts),
		},
	})
}

// GetAccount handles GET /api/accounts/:id
func (h *AccountsHandler) GetAccount(c *fiber.Ctx) error {
	id, err := strconv.ParseUint(c.Params("id"), 10, 32)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.AccountResponse{
			Success: false,
			Error:   "Invalid account ID",
		})
	}

	account, err := h.db.GetAccount(uint(id))
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.AccountResponse{
			Success: false,
			Error:   "Account not found",
		})
	}

	return c.JSON(models.AccountResponse{
		Success: true,
		Account: account,
	})
}

// CreateAccount handles POST /api/accounts
func (h *AccountsHandler) CreateAccount(c *fiber.Ctx) error {
	var req models.AccountCreateRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.AccountResponse{
			Success: false,
			Error:   "Invalid request body",
		})
	}

	// Validate count
	if req.Count < 1 {
		req.Count = 1
	}
	if req.Count > 100 {
		return c.Status(fiber.StatusBadRequest).JSON(models.AccountResponse{
			Success: false,
			Error:   "Count must be between 1 and 100",
		})
	}

	// Create a job for account creation
	job := &models.Job{
		ID:       uuid.New().String(),
		Count:    req.Count,
		Username: req.Username,
		Password: req.Password,
		Status:   models.JobStatusPending,
		TestMode: false,
		Priority: 0,
	}

	// Save job to database
	if err := h.db.CreateJob(job); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.JobResponse{
			Success: false,
			Error:   "Failed to create job",
		})
	}

	// Enqueue job
	if err := h.queue.EnqueueJob(job); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.JobResponse{
			Success: false,
			Error:   "Failed to enqueue job",
		})
	}

	return c.Status(fiber.StatusCreated).JSON(models.JobResponse{
		Success: true,
		Message: "Account creation job queued",
		Job:     job,
	})
}

// UpdateAccount handles PUT /api/accounts/:id
func (h *AccountsHandler) UpdateAccount(c *fiber.Ctx) error {
	id, err := strconv.ParseUint(c.Params("id"), 10, 32)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.AccountResponse{
			Success: false,
			Error:   "Invalid account ID",
		})
	}

	account, err := h.db.GetAccount(uint(id))
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.AccountResponse{
			Success: false,
			Error:   "Account not found",
		})
	}

	// Parse update data
	if err := c.BodyParser(account); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(models.AccountResponse{
			Success: false,
			Error:   "Invalid request body",
		})
	}

	// Update in database
	if err := h.db.UpdateAccount(account); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.AccountResponse{
			Success: false,
			Error:   "Failed to update account",
		})
	}

	return c.JSON(models.AccountResponse{
		Success: true,
		Message: "Account updated successfully",
		Account: account,
	})
}

// DeleteAccount handles DELETE /api/accounts/:accountId
func (h *AccountsHandler) DeleteAccount(c *fiber.Ctx) error {
	accountID, err := strconv.ParseUint(c.Params("accountId"), 10, 32)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"success": false,
			"error":   "Invalid account ID",
		})
	}

	// Get account first to verify it exists
	account, err := h.db.GetAccount(uint(accountID))
	if err != nil {
		log.Printf("[AccountsHandler] Account not found: %d", accountID)
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"success": false,
			"error":   "Account not found",
		})
	}

	// Soft delete (GORM automatically sets DeletedAt)
	if err := h.db.DeleteAccount(uint(accountID)); err != nil {
		log.Printf("[AccountsHandler] Failed to delete account %d: %v", accountID, err)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"success": false,
			"error":   "Failed to delete account",
		})
	}

	log.Printf("[AccountsHandler] Account %d (%s) soft deleted", accountID, account.Username)

	return c.JSON(fiber.Map{
		"success": true,
		"message": "Account deleted successfully",
		"account": fiber.Map{
			"id":       accountID,
			"username": account.Username,
			"email":    account.Email,
		},
	})
}

// GetStats handles GET /api/stats
func (h *AccountsHandler) GetStats(c *fiber.Ctx) error {
	// Get account statistics
	accountStats, err := h.db.GetAccountStats()
	if err != nil {
		log.Printf("[AccountsHandler] Failed to get account stats: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(StatsResponse{
			Success: false,
			Error:   "Failed to retrieve account statistics",
		})
	}

	// Get job statistics
	jobStats, err := h.db.GetJobStats()
	if err != nil {
		log.Printf("[AccountsHandler] Failed to get job stats: %v", err)
		return c.Status(fiber.StatusInternalServerError).JSON(StatsResponse{
			Success: false,
			Error:   "Failed to retrieve job statistics",
		})
	}

	// Get queue statistics
	queueStats, err := h.queue.GetQueueStats()
	if err != nil {
		log.Printf("[AccountsHandler] Failed to get queue stats: %v", err)
		queueStats = map[string]interface{}{
			"error": "Queue unavailable",
		}
	}

	// Calculate success/fail ratio
	totalJobs := jobStats.Completed + jobStats.Failed
	var successRate, failureRate float64
	if totalJobs > 0 {
		successRate = (float64(jobStats.Completed) / float64(totalJobs)) * 100
		failureRate = (float64(jobStats.Failed) / float64(totalJobs)) * 100
	}

	// TODO: Get hotmail pool remaining from email pool service
	// For now, return a placeholder
	hotmailRemaining := 0

	response := StatsResponse{
		Success:          true,
		TotalAccounts:    accountStats.Total,
		SuccessRate:      successRate,
		FailureRate:      failureRate,
		AccountStats:     accountStats,
		JobStats:         jobStats,
		QueueStats:       queueStats,
		HotmailRemaining: hotmailRemaining,
	}

	return c.JSON(response)
}

// GetJobs handles GET /api/jobs
func (h *AccountsHandler) GetJobs(c *fiber.Ctx) error {
	limit, _ := strconv.Atoi(c.Query("limit", "50"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	if limit > 100 {
		limit = 100
	}

	jobs, err := h.db.ListJobs(limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.JobResponse{
			Success: false,
			Error:   "Failed to retrieve jobs",
		})
	}

	return c.JSON(models.JobResponse{
		Success: true,
		Jobs:    jobs,
	})
}

// GetJob handles GET /api/jobs/:jobId
func (h *AccountsHandler) GetJob(c *fiber.Ctx) error {
	jobID := c.Params("jobId")

	if jobID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"success": false,
			"error":   "Job ID is required",
		})
	}

	// Get job from database
	job, err := h.db.GetJob(jobID)
	if err != nil {
		log.Printf("[AccountsHandler] Job not found: %s", jobID)
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"success": false,
			"error":   "Job not found",
		})
	}

	// Get status from Redis (more up-to-date than database)
	redisStatus, err := h.queue.GetJobStatus(jobID)
	if err == nil && redisStatus != "" {
		job.Status = models.JobStatus(redisStatus)
	}

	// Calculate progress percentage
	var progressPercent float64
	if job.Count > 0 {
		progressPercent = (float64(job.Progress) / float64(job.Count)) * 100
	}

	// Calculate duration if job has started
	var duration string
	if job.StartedAt != nil {
		if job.CompletedAt != nil {
			duration = job.CompletedAt.Sub(*job.StartedAt).String()
		} else {
			duration = time.Since(*job.StartedAt).String()
		}
	}

	return c.JSON(fiber.Map{
		"success": true,
		"job":     job,
		"progress": fiber.Map{
			"current":    job.Progress,
			"total":      job.Count,
			"percentage": progressPercent,
			"successful": job.Successful,
			"failed":     job.Failed,
		},
		"duration": duration,
		"status":   string(job.Status),
	})
}

// CancelJob handles POST /api/jobs/:id/cancel
func (h *AccountsHandler) CancelJob(c *fiber.Ctx) error {
	id := c.Params("id")

	job, err := h.db.GetJob(id)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(models.JobResponse{
			Success: false,
			Error:   "Job not found",
		})
	}

	if !job.CanBeCancelled() {
		return c.Status(fiber.StatusBadRequest).JSON(models.JobResponse{
			Success: false,
			Error:   "Job cannot be cancelled in current state",
		})
	}

	job.Status = models.JobStatusCancelled
	now := time.Now()
	job.CompletedAt = &now

	if err := h.db.UpdateJob(job); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(models.JobResponse{
			Success: false,
			Error:   "Failed to cancel job",
		})
	}

	return c.JSON(models.JobResponse{
		Success: true,
		Message: "Job cancelled successfully",
		Job:     job,
	})
}

// GetJobStats handles GET /api/jobs/stats
func (h *AccountsHandler) GetJobStats(c *fiber.Ctx) error {
	stats, err := h.db.GetJobStats()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"success": false,
			"error":   "Failed to retrieve job statistics",
		})
	}

	queueStats, err := h.queue.GetQueueStats()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"success": false,
			"error":   "Failed to retrieve queue statistics",
		})
	}

	return c.JSON(fiber.Map{
		"success":     true,
		"job_stats":   stats,
		"queue_stats": queueStats,
	})
}
