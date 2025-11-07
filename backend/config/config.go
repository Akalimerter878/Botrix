package config

import (
	"fmt"
	"log"
	"os"

	"github.com/joho/godotenv"
)

// Config holds all configuration for the application
type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
}

// ServerConfig holds server-specific configuration
type ServerConfig struct {
	Port        string
	Host        string
	Environment string
}

// DatabaseConfig holds database-specific configuration
type DatabaseConfig struct {
	Driver   string
	DSN      string
	Host     string
	Port     string
	Database string
	Username string
	Password string
}

// RedisConfig holds Redis-specific configuration
type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

// LoadConfig loads configuration from environment variables
func LoadConfig() (*Config, error) {
	// Load .env file from parent directory (project root)
	// This allows the backend to use the same .env as the Python code
	if err := godotenv.Load("../.env"); err != nil {
		log.Printf("Warning: .env file not found in parent directory, using system environment variables")
	}

	config := &Config{
		Server: ServerConfig{
			Port:        getEnv("SERVER_PORT", "8080"),
			Host:        getEnv("SERVER_HOST", "0.0.0.0"),
			Environment: getEnv("ENVIRONMENT", "development"),
		},
		Database: DatabaseConfig{
			Driver:   getEnv("DB_DRIVER", "sqlite"),
			DSN:      getEnv("DB_DSN", "./botrix.db"),
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnv("DB_PORT", "5432"),
			Database: getEnv("DB_NAME", "botrix"),
			Username: getEnv("DB_USER", ""),
			Password: getEnv("DB_PASSWORD", ""),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       0,
		},
	}

	return config, nil
}

// getEnv retrieves an environment variable or returns a default value
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

// GetServerAddress returns the full server address
func (c *Config) GetServerAddress() string {
	return fmt.Sprintf("%s:%s", c.Server.Host, c.Server.Port)
}

// GetRedisAddress returns the full Redis address
func (c *Config) GetRedisAddress() string {
	return fmt.Sprintf("%s:%s", c.Redis.Host, c.Redis.Port)
}

// IsDevelopment checks if the environment is development
func (c *Config) IsDevelopment() bool {
	return c.Server.Environment == "development"
}

// IsProduction checks if the environment is production
func (c *Config) IsProduction() bool {
	return c.Server.Environment == "production"
}
