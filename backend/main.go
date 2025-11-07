package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"botrix-backend/config"
	"botrix-backend/handlers"
	"botrix-backend/services"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/fiber/v2/middleware/requestid"
	"github.com/gofiber/websocket/v2"
)

func main() {
	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	log.Printf("Starting Botrix Backend API...")
	log.Printf("Environment: %s", cfg.Server.Environment)

	// Initialize database
	db, err := services.NewDatabase(cfg)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Initialize queue (Redis)
	queue, err := services.NewQueueService(cfg)
	if err != nil {
		log.Fatalf("Failed to initialize queue: %v", err)
	}
	defer queue.Close()

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:      "Botrix Backend API v1.0.0",
		ServerHeader: "Botrix",
		ErrorHandler: customErrorHandler,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	})

	// Middleware
	app.Use(recover.New())
	app.Use(requestid.New())

	// Logger middleware
	if cfg.IsDevelopment() {
		app.Use(logger.New(logger.Config{
			Format: "[${time}] ${status} - ${method} ${path} (${latency})\n",
		}))
	}

	// CORS middleware
	app.Use(cors.New(cors.Config{
		AllowOrigins:     getAllowedOrigins(cfg),
		AllowMethods:     "GET,POST,PUT,DELETE,OPTIONS",
		AllowHeaders:     "Origin, Content-Type, Accept, Authorization",
		AllowCredentials: true,
		MaxAge:           86400, // 24 hours
	}))

	// Initialize handlers
	healthHandler := handlers.NewHealthHandler()
	accountsHandler := handlers.NewAccountsHandler(db, queue)
	wsHandler := handlers.NewWebSocketHandler(queue.GetRedisClient())

	// Initialize middleware
	rateLimiter := handlers.NewRateLimiter(10, 1*time.Minute) // 10 requests per minute
	validator := handlers.RequestValidator()

	// Health check routes (no rate limiting)
	app.Get("/health", healthHandler.Check)
	app.Get("/health/ping", healthHandler.Ping)
	app.Get("/health/ready", healthHandler.Ready)
	app.Get("/health/live", healthHandler.Live)

	// WebSocket routes
	app.Use("/ws", func(c *fiber.Ctx) error {
		// IsWebSocketUpgrade returns true if the client requested upgrade to the WebSocket protocol
		if websocket.IsWebSocketUpgrade(c) {
			c.Locals("allowed", true)
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	})
	app.Get("/ws", websocket.New(wsHandler.HandleWebSocket))
	app.Get("/ws/stats", wsHandler.GetStats)

	// API routes with validation
	api := app.Group("/api", validator)

	// Account generation endpoint with rate limiting
	api.Post("/accounts/generate", rateLimiter.Middleware(), accountsHandler.GenerateAccounts)

	// Account routes
	api.Get("/accounts", accountsHandler.ListAccounts)
	api.Get("/accounts/:id", accountsHandler.GetAccount)
	api.Post("/accounts", accountsHandler.CreateAccount)
	api.Put("/accounts/:id", accountsHandler.UpdateAccount)
	api.Delete("/accounts/:accountId", accountsHandler.DeleteAccount)

	// Stats endpoint
	api.Get("/stats", accountsHandler.GetStats)

	// Job routes
	api.Get("/jobs", accountsHandler.GetJobs)
	api.Get("/jobs/:jobId", accountsHandler.GetJob)
	api.Post("/jobs/:id/cancel", accountsHandler.CancelJob)
	api.Get("/jobs/stats", accountsHandler.GetJobStats)

	// Root route
	app.Get("/", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"name":    "Botrix Backend API",
			"version": "1.0.0",
			"status":  "running",
			"endpoints": fiber.Map{
				"health":    "/health",
				"api":       "/api",
				"accounts":  "/api/accounts",
				"jobs":      "/api/jobs",
				"websocket": "/ws",
			},
		})
	})

	// 404 handler
	app.Use(func(c *fiber.Ctx) error {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "Not Found",
			"message": "The requested resource was not found",
			"path":    c.Path(),
		})
	})

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
		<-sigChan

		log.Println("Shutting down server...")

		if err := app.Shutdown(); err != nil {
			log.Printf("Error during shutdown: %v", err)
		}

		log.Println("Server shutdown complete")
	}()

	// Start server
	addr := cfg.GetServerAddress()
	log.Printf("Server starting on %s", addr)

	if err := app.Listen(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

// customErrorHandler handles errors globally
func customErrorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError

	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}

	return c.Status(code).JSON(fiber.Map{
		"error":   true,
		"message": err.Error(),
		"code":    code,
	})
}

// getAllowedOrigins returns CORS allowed origins based on environment
func getAllowedOrigins(cfg *config.Config) string {
	if cfg.IsDevelopment() {
		return "*" // Allow all in development
	}

	// In production, specify exact origins
	return "https://yourdomain.com,https://www.yourdomain.com"
}
