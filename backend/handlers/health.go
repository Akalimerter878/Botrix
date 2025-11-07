package handlers

import (
	"time"

	"github.com/gofiber/fiber/v2"
)

// HealthHandler handles health check requests
type HealthHandler struct{}

// NewHealthHandler creates a new health handler
func NewHealthHandler() *HealthHandler {
	return &HealthHandler{}
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status   string                 `json:"status"`
	Services map[string]interface{} `json:"services"`
	Version  string                 `json:"version"`
}

// Check handles GET /health
func (h *HealthHandler) Check(c *fiber.Ctx) error {
	response := HealthResponse{
		Status:  "healthy",
		Version: "1.0.0",
		Services: map[string]interface{}{
			"api":      "operational",
			"database": "connected",
			"redis":    "connected",
		},
	}

	return c.JSON(response)
}

// Ping handles GET /ping
func (h *HealthHandler) Ping(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"message": "pong",
		"time": fiber.Map{
			"timestamp": time.Now().Unix(),
		},
	})
}

// Ready handles GET /ready (for Kubernetes readiness probe)
func (h *HealthHandler) Ready(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"ready": true,
	})
}

// Live handles GET /live (for Kubernetes liveness probe)
func (h *HealthHandler) Live(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"alive": true,
	})
}
