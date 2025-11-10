package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"sync"
	"time"

	"botrix-backend/utils"

	"github.com/gofiber/fiber/v2"
)

// EnhancedLogger middleware provides detailed request/response logging (legacy)
func EnhancedLogger() fiber.Handler {
	logger := utils.GetDefaultLogger().WithComponent("API")
	return EnhancedLoggerWithLogger(logger)
}

// EnhancedLoggerWithLogger middleware provides detailed request/response logging with custom logger
func EnhancedLoggerWithLogger(logger *utils.Logger) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Start timer
		start := time.Now()
		requestID := c.Locals("requestid")

		// Log request
		logRequestWithLogger(c, requestID, logger)

		// Process request
		err := c.Next()

		// Calculate latency
		latency := time.Since(start)

		// Log response
		logResponseWithLogger(c, requestID, latency, err, logger)

		return err
	}
}

// logRequestWithLogger logs incoming request details
func logRequestWithLogger(c *fiber.Ctx, requestID interface{}, logger *utils.Logger) {
	fields := map[string]interface{}{
		"method": c.Method(),
		"path":   c.Path(),
		"ip":     c.IP(),
	}

	if requestID != nil {
		fields["request_id"] = requestID
	}

	logger.WithFields(fields).Info("→ Incoming request")

	// Log query parameters
	if len(c.Queries()) > 0 {
		logger.WithField("query", c.Queries()).Debug("Request query parameters")
	}

	// Log request body for POST/PUT/PATCH (but redact sensitive data)
	if c.Method() == "POST" || c.Method() == "PUT" || c.Method() == "PATCH" {
		bodyBytes := c.Body()
		if len(bodyBytes) > 0 && len(bodyBytes) < 10000 { // Only log bodies < 10KB
			// Try to parse as JSON for pretty printing
			var jsonBody interface{}
			if err := json.Unmarshal(bodyBytes, &jsonBody); err == nil {
				// Redact sensitive fields
				redactSensitiveFields(jsonBody)
				logger.WithField("body", jsonBody).Debug("Request body")
			}
		}
	}
}

// logResponseWithLogger logs response details
func logResponseWithLogger(c *fiber.Ctx, requestID interface{}, latency time.Duration, err error, logger *utils.Logger) {
	statusCode := c.Response().StatusCode()

	fields := map[string]interface{}{
		"method":  c.Method(),
		"path":    c.Path(),
		"status":  statusCode,
		"latency": latency.String(),
	}

	if requestID != nil {
		fields["request_id"] = requestID
	}

	// Log error if present
	if err != nil {
		fields["error"] = err.Error()
	}

	// Log response size
	responseSize := len(c.Response().Body())
	if responseSize > 0 {
		fields["response_size"] = formatBytes(responseSize)
	}

	// Determine log level based on status code
	logWithFields := logger.WithFields(fields)

	if statusCode >= 500 {
		logWithFields.Error("✗ Request completed with server error")
	} else if statusCode >= 400 {
		logWithFields.Warn("⚠ Request completed with client error")
	} else {
		logWithFields.Info("✓ Request completed successfully")
	}
}

// redactSensitiveFields removes sensitive data from logs
func redactSensitiveFields(data interface{}) {
	switch v := data.(type) {
	case map[string]interface{}:
		for key, value := range v {
			lowerKey := key
			// Redact password fields
			if lowerKey == "password" || lowerKey == "email_password" || lowerKey == "token" || lowerKey == "secret" {
				v[key] = "***REDACTED***"
			} else {
				redactSensitiveFields(value)
			}
		}
	case []interface{}:
		for _, item := range v {
			redactSensitiveFields(item)
		}
	}
}

// formatBytes formats byte count as human-readable string
func formatBytes(bytes int) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

// BodyLogger middleware captures response body for logging (use sparingly)
type bodyLogWriter struct {
	io.Writer
	body *bytes.Buffer
}

func (w bodyLogWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.Writer.Write(b)
}

// RequestValidator middleware validates common request parameters
func RequestValidator() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Validate Content-Type for POST/PUT requests
		if c.Method() == "POST" || c.Method() == "PUT" {
			contentType := c.Get("Content-Type")
			if contentType != "" && contentType != "application/json" {
				return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
					"success": false,
					"error":   "Content-Type must be application/json",
				})
			}
		}

		return c.Next()
	}
}

// RateLimiter is a simple in-memory rate limiter
type RateLimiter struct {
	requests map[string]*clientRequests
	mu       sync.RWMutex
	limit    int
	window   time.Duration
	logger   *utils.Logger
}

type clientRequests struct {
	count     int
	resetTime time.Time
}

// NewRateLimiter creates a new rate limiter (legacy)
func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	return NewRateLimiterWithLogger(limit, window, utils.GetDefaultLogger().WithComponent("RATELIMIT"))
}

// NewRateLimiterWithLogger creates a new rate limiter with custom logger
func NewRateLimiterWithLogger(limit int, window time.Duration, logger *utils.Logger) *RateLimiter {
	rl := &RateLimiter{
		requests: make(map[string]*clientRequests),
		limit:    limit,
		window:   window,
		logger:   logger,
	}

	// Cleanup goroutine to remove expired entries
	go func() {
		ticker := time.NewTicker(window)
		defer ticker.Stop()

		for range ticker.C {
			rl.cleanup()
		}
	}()

	return rl
}

// Middleware returns a Fiber middleware handler
func (rl *RateLimiter) Middleware() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Use IP address as client identifier
		clientIP := c.IP()

		rl.mu.Lock()
		defer rl.mu.Unlock()

		now := time.Now()
		client, exists := rl.requests[clientIP]

		if !exists || now.After(client.resetTime) {
			// First request or window expired, reset
			rl.requests[clientIP] = &clientRequests{
				count:     1,
				resetTime: now.Add(rl.window),
			}

			rl.logger.WithFields(map[string]interface{}{
				"ip":     clientIP,
				"count":  1,
				"limit":  rl.limit,
				"window": rl.window.String(),
			}).Debug("New rate limit window")

			return c.Next()
		}

		// Check if limit exceeded
		if client.count >= rl.limit {
			retryAfter := int(time.Until(client.resetTime).Seconds())

			rl.logger.WithFields(map[string]interface{}{
				"ip":          clientIP,
				"count":       client.count,
				"limit":       rl.limit,
				"retry_after": retryAfter,
			}).Warn("Rate limit exceeded")

			c.Set("Retry-After", string(rune(retryAfter)))
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"success":             false,
				"error":               "Rate limit exceeded",
				"message":             "Too many requests, please try again later",
				"retry_after_seconds": retryAfter,
			})
		}

		// Increment count
		client.count++
		rl.logger.WithFields(map[string]interface{}{
			"ip":    clientIP,
			"count": client.count,
			"limit": rl.limit,
		}).Debug("Rate limit check passed")

		return c.Next()
	}
}

// cleanup removes expired entries
func (rl *RateLimiter) cleanup() {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	removed := 0
	for ip, client := range rl.requests {
		if now.After(client.resetTime) {
			delete(rl.requests, ip)
			removed++
		}
	}

	if removed > 0 {
		rl.logger.WithFields(map[string]interface{}{
			"removed":   removed,
			"remaining": len(rl.requests),
		}).Debug("Rate limiter cleanup completed")
	}
}

// GetStats returns current rate limiter statistics
func (rl *RateLimiter) GetStats() map[string]interface{} {
	rl.mu.RLock()
	defer rl.mu.RUnlock()

	totalClients := len(rl.requests)
	activeClients := 0

	for _, client := range rl.requests {
		if time.Now().Before(client.resetTime) {
			activeClients++
		}
	}

	return map[string]interface{}{
		"total_clients":  totalClients,
		"active_clients": activeClients,
		"limit":          rl.limit,
		"window_seconds": rl.window.Seconds(),
	}
}
