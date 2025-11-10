package handlers

import (
	"botrix-backend/models"
	"botrix-backend/services"
	"botrix-backend/utils"

	"github.com/gofiber/fiber/v2"
)

// SettingsHandler handles settings-related HTTP requests
type SettingsHandler struct {
	db     *services.Database
	logger *utils.Logger
}

// NewSettingsHandler creates a new settings handler
func NewSettingsHandler(db *services.Database) *SettingsHandler {
	return &SettingsHandler{
		db:     db,
		logger: utils.GetDefaultLogger().WithComponent("SETTINGS"),
	}
}

// GetSettings returns the current application settings
// GET /api/settings
func (h *SettingsHandler) GetSettings(c *fiber.Ctx) error {
	settings, err := h.db.GetSettings()
	if err != nil {
		h.logger.WithField("error", err.Error()).Error("Failed to get settings")
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"success": false,
			"error":   "Failed to retrieve settings",
			"message": err.Error(),
		})
	}

	h.logger.Debug("Settings retrieved successfully")

	return c.JSON(fiber.Map{
		"success": true,
		"data":    settings.ToResponse(),
	})
}

// SaveSettings updates the application settings
// POST /api/settings
func (h *SettingsHandler) SaveSettings(c *fiber.Ctx) error {
	var input models.Setting

	// Parse request body
	if err := c.BodyParser(&input); err != nil {
		h.logger.WithField("error", err.Error()).Warn("Invalid request body")
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"success": false,
			"error":   "Invalid request body",
			"message": err.Error(),
		})
	}

	// Validate required fields (optional - add your validation logic here)
	// For example, validate RapidAPI key format, email credentials, etc.

	// Save settings to database
	if err := h.db.SaveSettings(&input); err != nil {
		h.logger.WithFields(map[string]interface{}{
			"error": err.Error(),
		}).Error("Failed to save settings")
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"success": false,
			"error":   "Failed to save settings",
			"message": err.Error(),
		})
	}

	h.logger.Info("Settings saved successfully")

	// Fetch updated settings to return
	updatedSettings, err := h.db.GetSettings()
	if err != nil {
		h.logger.WithField("error", err.Error()).Warn("Failed to fetch updated settings")
		// Still return success since the save operation succeeded
		return c.JSON(fiber.Map{
			"success": true,
			"message": "Settings saved successfully",
		})
	}

	return c.JSON(fiber.Map{
		"success": true,
		"message": "Settings saved successfully",
		"data":    updatedSettings.ToResponse(),
	})
}
