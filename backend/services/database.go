package services

import (
	"fmt"
	"log"
	"time"

	"botrix-backend/config"
	"botrix-backend/models"

	"github.com/glebarez/sqlite" // Pure Go SQLite driver based on modernc.org/sqlite
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// Database service handles all database operations
type Database struct {
	db     *gorm.DB
	config *config.Config
}

// NewDatabase creates a new database service
func NewDatabase(cfg *config.Config) (*Database, error) {
	var db *gorm.DB
	var err error

	// Configure GORM logger
	logLevel := logger.Silent
	if cfg.IsDevelopment() {
		logLevel = logger.Info
	}

	gormConfig := &gorm.Config{
		Logger: logger.Default.LogMode(logLevel),
	}

	// Connect based on driver type
	switch cfg.Database.Driver {
	case "sqlite":
		// Use glebarez/sqlite (pure Go, no CGO required, based on modernc.org/sqlite)
		db, err = gorm.Open(sqlite.Open(cfg.Database.DSN), gormConfig)
		if err != nil {
			return nil, fmt.Errorf("failed to connect to SQLite database: %w", err)
		}
	case "postgres":
		// PostgreSQL support (for future use)
		// dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		// 	cfg.Database.Host, cfg.Database.Port, cfg.Database.Username,
		// 	cfg.Database.Password, cfg.Database.Database)
		// db, err = gorm.Open(postgres.Open(dsn), gormConfig)
		return nil, fmt.Errorf("PostgreSQL driver not yet implemented")
	default:
		return nil, fmt.Errorf("unsupported database driver: %s", cfg.Database.Driver)
	}

	log.Printf("Successfully connected to database (%s)", cfg.Database.Driver)

	// Configure connection pooling
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get database instance: %w", err)
	}

	// Set maximum number of open connections
	sqlDB.SetMaxOpenConns(25)

	// Set maximum number of idle connections
	sqlDB.SetMaxIdleConns(5)

	// Set maximum lifetime of a connection (15 minutes)
	sqlDB.SetConnMaxLifetime(15 * time.Minute)

	// Set maximum idle time for a connection (5 minutes)
	sqlDB.SetConnMaxIdleTime(5 * time.Minute)

	log.Println("Database connection pooling configured")

	// Auto-migrate models
	if err := db.AutoMigrate(
		&models.Account{},
		&models.Job{},
	); err != nil {
		return nil, fmt.Errorf("failed to migrate database: %w", err)
	}

	log.Println("Database migration completed")

	return &Database{
		db:     db,
		config: cfg,
	}, nil
}

// GetDB returns the underlying GORM database instance
func (d *Database) GetDB() *gorm.DB {
	return d.db
}

// Close closes the database connection
func (d *Database) Close() error {
	sqlDB, err := d.db.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

// Health checks the database connection
func (d *Database) Health() error {
	sqlDB, err := d.db.DB()
	if err != nil {
		return err
	}
	return sqlDB.Ping()
}

// Account operations

// CreateAccount creates a new account in the database
func (d *Database) CreateAccount(account *models.Account) error {
	return d.db.Create(account).Error
}

// GetAccount retrieves an account by ID
func (d *Database) GetAccount(id uint) (*models.Account, error) {
	var account models.Account
	if err := d.db.First(&account, id).Error; err != nil {
		return nil, err
	}
	return &account, nil
}

// GetAccountByEmail retrieves an account by email
func (d *Database) GetAccountByEmail(email string) (*models.Account, error) {
	var account models.Account
	if err := d.db.Where("email = ?", email).First(&account).Error; err != nil {
		return nil, err
	}
	return &account, nil
}

// GetAccountByUsername retrieves an account by username
func (d *Database) GetAccountByUsername(username string) (*models.Account, error) {
	var account models.Account
	if err := d.db.Where("username = ?", username).First(&account).Error; err != nil {
		return nil, err
	}
	return &account, nil
}

// ListAccounts retrieves all accounts with pagination
func (d *Database) ListAccounts(limit, offset int) ([]models.Account, error) {
	var accounts []models.Account
	err := d.db.Limit(limit).Offset(offset).Order("created_at DESC").Find(&accounts).Error
	return accounts, err
}

// UpdateAccount updates an account
func (d *Database) UpdateAccount(account *models.Account) error {
	return d.db.Save(account).Error
}

// DeleteAccount deletes an account (soft delete)
func (d *Database) DeleteAccount(id uint) error {
	return d.db.Delete(&models.Account{}, id).Error
}

// GetAccountStats retrieves statistics about accounts
func (d *Database) GetAccountStats() (*models.AccountStats, error) {
	var stats models.AccountStats

	// Total count
	d.db.Model(&models.Account{}).Count(&stats.Total)

	// Status counts
	d.db.Model(&models.Account{}).Where("status = ?", "active").Count(&stats.Active)
	d.db.Model(&models.Account{}).Where("status = ?", "banned").Count(&stats.Banned)
	d.db.Model(&models.Account{}).Where("status = ?", "suspended").Count(&stats.Suspended)

	// Today's count
	d.db.Model(&models.Account{}).
		Where("DATE(created_at) = DATE('now')").
		Count(&stats.Today)

	return &stats, nil
}

// Job operations

// CreateJob creates a new job in the database
func (d *Database) CreateJob(job *models.Job) error {
	return d.db.Create(job).Error
}

// GetJob retrieves a job by ID
func (d *Database) GetJob(id string) (*models.Job, error) {
	var job models.Job
	if err := d.db.First(&job, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &job, nil
}

// ListJobs retrieves all jobs with pagination
func (d *Database) ListJobs(limit, offset int) ([]models.Job, error) {
	var jobs []models.Job
	err := d.db.Limit(limit).Offset(offset).Order("created_at DESC").Find(&jobs).Error
	return jobs, err
}

// UpdateJob updates a job
func (d *Database) UpdateJob(job *models.Job) error {
	return d.db.Save(job).Error
}

// DeleteJob deletes a job (soft delete)
func (d *Database) DeleteJob(id string) error {
	return d.db.Delete(&models.Job{}, "id = ?", id).Error
}

// GetJobStats retrieves statistics about jobs
func (d *Database) GetJobStats() (*models.JobStats, error) {
	var stats models.JobStats

	// Total count
	d.db.Model(&models.Job{}).Count(&stats.Total)

	// Status counts
	d.db.Model(&models.Job{}).Where("status = ?", models.JobStatusPending).Count(&stats.Pending)
	d.db.Model(&models.Job{}).Where("status = ?", models.JobStatusRunning).Count(&stats.Running)
	d.db.Model(&models.Job{}).Where("status = ?", models.JobStatusCompleted).Count(&stats.Completed)
	d.db.Model(&models.Job{}).Where("status = ?", models.JobStatusFailed).Count(&stats.Failed)
	d.db.Model(&models.Job{}).Where("status = ?", models.JobStatusCancelled).Count(&stats.Cancelled)

	return &stats, nil
}

// GetPendingJobs retrieves all pending jobs
func (d *Database) GetPendingJobs() ([]models.Job, error) {
	var jobs []models.Job
	err := d.db.Where("status = ?", models.JobStatusPending).
		Order("priority DESC, created_at ASC").
		Find(&jobs).Error
	return jobs, err
}

// WithTransaction executes a function within a database transaction
// If the function returns an error, the transaction is rolled back
// Otherwise, the transaction is committed
func (d *Database) WithTransaction(fn func(*gorm.DB) error) error {
	tx := d.db.Begin()
	if tx.Error != nil {
		return tx.Error
	}

	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
			log.Printf("Transaction rolled back due to panic: %v", r)
		}
	}()

	if err := fn(tx); err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit().Error
}

// CreateAccountsBatch creates multiple accounts in a single transaction
func (d *Database) CreateAccountsBatch(accounts []*models.Account) error {
	return d.WithTransaction(func(tx *gorm.DB) error {
		for _, account := range accounts {
			if err := tx.Create(account).Error; err != nil {
				return fmt.Errorf("failed to create account %s: %w", account.Email, err)
			}
		}
		log.Printf("Successfully created %d accounts in batch", len(accounts))
		return nil
	})
}

// GetAccountsByJobID retrieves all accounts associated with a job
func (d *Database) GetAccountsByJobID(jobID string) ([]models.Account, error) {
	var accounts []models.Account
	err := d.db.Where("job_id = ?", jobID).Order("created_at ASC").Find(&accounts).Error
	return accounts, err
}

// GetAccountsByStatus retrieves accounts filtered by status with pagination
func (d *Database) GetAccountsByStatus(status string, limit, offset int) ([]models.Account, error) {
	var accounts []models.Account
	err := d.db.Where("status = ?", status).
		Limit(limit).
		Offset(offset).
		Order("created_at DESC").
		Find(&accounts).Error
	return accounts, err
}

// CountAccounts returns the total count of accounts (excluding soft-deleted)
func (d *Database) CountAccounts() (int64, error) {
	var count int64
	err := d.db.Model(&models.Account{}).Count(&count).Error
	return count, err
}

// CountAccountsByStatus returns the count of accounts by status
func (d *Database) CountAccountsByStatus(status string) (int64, error) {
	var count int64
	err := d.db.Model(&models.Account{}).Where("status = ?", status).Count(&count).Error
	return count, err
}

// UpdateAccountStatus updates the status of an account
func (d *Database) UpdateAccountStatus(id uint, status string) error {
	return d.db.Model(&models.Account{}).Where("id = ?", id).Update("status", status).Error
}

// BulkUpdateAccountStatus updates status for multiple accounts in a transaction
func (d *Database) BulkUpdateAccountStatus(ids []uint, status string) error {
	return d.WithTransaction(func(tx *gorm.DB) error {
		result := tx.Model(&models.Account{}).Where("id IN ?", ids).Update("status", status)
		if result.Error != nil {
			return result.Error
		}
		log.Printf("Updated status to '%s' for %d accounts", status, result.RowsAffected)
		return nil
	})
}

// GetJobsByStatus retrieves jobs filtered by status with pagination
func (d *Database) GetJobsByStatus(status models.JobStatus, limit, offset int) ([]models.Job, error) {
	var jobs []models.Job
	err := d.db.Where("status = ?", status).
		Limit(limit).
		Offset(offset).
		Order("created_at DESC").
		Find(&jobs).Error
	return jobs, err
}

// CountJobs returns the total count of jobs (excluding soft-deleted)
func (d *Database) CountJobs() (int64, error) {
	var count int64
	err := d.db.Model(&models.Job{}).Count(&count).Error
	return count, err
}

// UpdateJobProgress updates the progress of a job
func (d *Database) UpdateJobProgress(id string, progress, successful, failed int) error {
	return d.db.Model(&models.Job{}).
		Where("id = ?", id).
		Updates(map[string]interface{}{
			"progress":   progress,
			"successful": successful,
			"failed":     failed,
		}).Error
}
