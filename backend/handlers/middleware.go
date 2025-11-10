package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
)

// EnhancedLogger middleware provides detailed request/response logging
func EnhancedLogger() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Start timer
		start := time.Now()
		requestID := c.Locals("requestid")

		// Log request
		logRequest(c, requestID)

		// Process request
		err := c.Next()

		// Calculate latency
		latency := time.Since(start)

		// Log response
		logResponse(c, requestID, latency, err)

		return err
	}
}

// logRequest logs incoming request details
func logRequest(c *fiber.Ctx, requestID interface{}) {
	timestamp := time.Now().Format("2006-01-02 15:04:05.000")

	log.Printf("[API %s] → %s %s %s",
		timestamp,
		c.Method(),
		c.Path(),
		c.IP(),
	)

	// Log request ID if available
	if requestID != nil {
		log.Printf("[API %s]   Request-ID: %v", timestamp, requestID)
	}

	// Log query parameters
	if len(c.Queries()) > 0 {
		log.Printf("[API %s]   Query: %v", timestamp, c.Queries())
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
				prettyJSON, _ := json.MarshalIndent(jsonBody, "         ", "  ")
				log.Printf("[API %s]   Body: %s", timestamp, string(prettyJSON))
			}
		}
	}
}

// logResponse logs response details
func logResponse(c *fiber.Ctx, requestID interface{}, latency time.Duration, err error) {
	timestamp := time.Now().Format("2006-01-02 15:04:05.000")
	statusCode := c.Response().StatusCode()

	// Determine log level based on status code
	statusEmoji := "✓"
	if statusCode >= 400 && statusCode < 500 {
		statusEmoji = "⚠"
	} else if statusCode >= 500 {
		statusEmoji = "✗"
	}

	log.Printf("[API %s] %s %d %s %s (%s)",
		timestamp,
		statusEmoji,
		statusCode,
		c.Method(),
		c.Path(),
		latency,
	)

	// Log error if present
	if err != nil {
		log.Printf("[API %s]   Error: %v", timestamp, err)
	}

	// Log response size
	responseSize := len(c.Response().Body())
	if responseSize > 0 {
		log.Printf("[API %s]   Response Size: %s", timestamp, formatBytes(responseSize))
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
}

type clientRequests struct {
	count     int
	resetTime time.Time
}

// NewRateLimiter creates a new rate limiter
// limit: maximum requests per window
// window: time window duration (e.g., 1 minute)
func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		requests: make(map[string]*clientRequests),
		limit:    limit,
		window:   window,
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

			log.Printf("[RateLimiter] New window for %s: 1/%d requests", clientIP, rl.limit)
			return c.Next()
		}

		// Check if limit exceeded
		if client.count >= rl.limit {
			retryAfter := int(time.Until(client.resetTime).Seconds())

			log.Printf("[RateLimiter] Rate limit exceeded for %s: %d/%d requests",
				clientIP, client.count, rl.limit)

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
		log.Printf("[RateLimiter] Request from %s: %d/%d requests",
			clientIP, client.count, rl.limit)

		return c.Next()
	}
}

// cleanup removes expired entries
func (rl *RateLimiter) cleanup() {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	for ip, client := range rl.requests {
		if now.After(client.resetTime) {
			delete(rl.requests, ip)
		}
	}

	log.Printf("[RateLimiter] Cleanup completed, %d clients in memory", len(rl.requests))
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
