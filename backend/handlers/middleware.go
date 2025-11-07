package handlers

import (
	"log"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
)

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
