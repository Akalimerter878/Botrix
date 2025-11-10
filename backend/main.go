package main

import (
	"os"
	"os/signal"
	"syscall"
	"time"

	"botrix-backend/config"
	"botrix-backend/handlers"
	"botrix-backend/services"
	"botrix-backend/utils"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/fiber/v2/middleware/requestid"
	"github.com/gofiber/websocket/v2"
)

var logger *utils.Logger

func main() {
	// Initialize logger
	var err error
	logger, err = utils.InitFileLogger("./logs", utils.INFO)
	if err != nil {
		utils.Fatal("Failed to initialize logger: %v", err)
	}

	// Redirect standard logger
	utils.RedirectStandardLogger()

	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		logger.Fatal("Failed to load configuration: %v", err)
	}

	logger.WithComponent("STARTUP").Info("Starting Botrix Backend API...")
	logger.WithComponent("STARTUP").Info("Environment: %s", cfg.Server.Environment)

	// Set log level based on environment
	if cfg.IsDevelopment() {
		logger.SetLevel(utils.DEBUG)
		logger.WithComponent("STARTUP").Info("Debug logging enabled (development mode)")
	}

	// Initialize database
	dbLogger := logger.WithComponent("DATABASE")
	db, err := services.NewDatabase(cfg)
	if err != nil {
		dbLogger.Fatal("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Initialize queue (Redis)
	queueLogger := logger.WithComponent("QUEUE")
	queue, err := services.NewQueueService(cfg)
	if err != nil {
		queueLogger.Fatal("Failed to initialize queue: %v", err)
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
	app.Use(recover.New(recover.Config{
		EnableStackTrace: cfg.IsDevelopment(),
	}))
	app.Use(requestid.New())

	// Enhanced logging middleware
	app.Use(handlers.EnhancedLoggerWithLogger(logger.WithComponent("API")))

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
	wsHandler := handlers.NewWebSocketHandlerWithLogger(queue.GetRedisClient(), logger.WithComponent("WEBSOCKET"))

	// Initialize middleware
	rateLimiter := handlers.NewRateLimiterWithLogger(10, 1*time.Minute, logger.WithComponent("RATELIMIT"))
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

		logger.WithComponent("SHUTDOWN").Warn("Received shutdown signal...")

		if err := app.Shutdown(); err != nil {
			logger.WithComponent("SHUTDOWN").Error("Error during shutdown: %v", err)
		}

		logger.WithComponent("SHUTDOWN").Info("Server shutdown complete")
	}()

	// Start server
	addr := cfg.GetServerAddress()
	logger.WithComponent("SERVER").Info("Server starting on %s", addr)

	if err := app.Listen(addr); err != nil {
		logger.WithComponent("SERVER").Fatal("Failed to start server: %v", err)
	}
}

// customErrorHandler handles errors globally
func customErrorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError

	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}

	logger.WithComponent("ERROR").WithFields(map[string]interface{}{
		"path":   c.Path(),
		"method": c.Method(),
		"ip":     c.IP(),
		"error":  err.Error(),
	}).Error("Request error occurred")

	return c.Status(code).JSON(fiber.Map{
		"error":   true,
		"message": err.Error(),
		"code":    code,
	})
}

// getAllowedOrigins returns CORS allowed origins based on environment
func getAllowedOrigins(cfg *config.Config) string {
	if cfg.IsDevelopment() {
		// Allow common development origins
		return "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
	}

	// In production, specify exact origins from environment or config
	allowedOrigins := os.Getenv("ALLOWED_ORIGINS")
	if allowedOrigins != "" {
		return allowedOrigins
	}

	// Fallback to default production domain
	logger.WithComponent("CORS").Warn("Using default production origins. Set ALLOWED_ORIGINS environment variable.")
	return "https://yourdomain.com,https://www.yourdomain.com"
}
