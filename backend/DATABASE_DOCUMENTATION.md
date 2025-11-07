# Database Models and Operations Documentation

## Overview

Complete documentation for the Botrix backend database models, services, and operations.

---

## Database Architecture

### Technology Stack
- **ORM**: GORM v1.25.5
- **Primary Database**: SQLite (Development)
- **Future Support**: PostgreSQL (Production)
- **Connection Pooling**: Enabled with optimized settings
- **Transaction Support**: Full ACID compliance

### Connection Pool Configuration
```go
MaxOpenConns:      25              // Maximum open connections
MaxIdleConns:      5               // Maximum idle connections
ConnMaxLifetime:   15 minutes      // Connection lifetime
ConnMaxIdleTime:   5 minutes       // Maximum idle time
```

---

## Models

### 1. Account Model (`models/account.go`)

Represents a generated Kick.com account.

**Fields**:
```go
type Account struct {
    ID        uint           `gorm:"primarykey" json:"id"`
    CreatedAt time.Time      `json:"created_at"`
    UpdatedAt time.Time      `json:"updated_at"`
    DeletedAt gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`
    
    // Account credentials
    Email         string `gorm:"uniqueIndex;not null" json:"email"`
    Username      string `gorm:"uniqueIndex;not null" json:"username"`
    Password      string `gorm:"not null" json:"password"`
    EmailPassword string `gorm:"not null" json:"email_password"`
    
    // Account metadata
    Birthdate        string `json:"birthdate"`
    VerificationCode string `json:"verification_code,omitempty"`
    
    // Status tracking
    Status string `gorm:"default:'active'" json:"status"` // active, banned, suspended
    JobID  string `gorm:"index" json:"job_id,omitempty"`
    
    // Additional data
    KickAccountID string `json:"kick_account_id,omitempty"`
    KickData      string `gorm:"type:text" json:"kick_data,omitempty"` // JSON string
    Notes         string `gorm:"type:text" json:"notes,omitempty"`
}
```

**Methods**:

| Method | Description | Returns |
|--------|-------------|---------|
| `ToJSON()` | Converts account to JSON-safe map (hides passwords) | `map[string]interface{}` |
| `HidePasswords()` | Masks password and email_password fields | `void` |
| `Validate()` | Validates all required fields are present | `error` |
| `IsActive()` | Checks if account status is active | `bool` |
| `IsBanned()` | Checks if account is banned | `bool` |
| `IsSuspended()` | Checks if account is suspended | `bool` |

**Example Usage**:
```go
account := &models.Account{
    Email:         "user@hotmail.com",
    Username:      "kickuser123",
    Password:      "SecurePass123!",
    EmailPassword: "EmailPass456!",
    Status:        "active",
}

// Validate before saving
if err := account.Validate(); err != nil {
    return err
}

// Create in database
db.CreateAccount(account)

// Get JSON-safe representation
jsonData := account.ToJSON()

// Hide passwords for logging
account.HidePasswords()
log.Printf("Account: %+v", account)
```

---

### 2. Job Model (`models/job.go`)

Represents an account creation job.

**Fields**:
```go
type Job struct {
    ID        string         `gorm:"primarykey" json:"id"`
    CreatedAt time.Time      `json:"created_at"`
    UpdatedAt time.Time      `json:"updated_at"`
    DeletedAt gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`
    
    // Job configuration
    Count    int    `gorm:"not null" json:"count"`
    Username string `json:"username,omitempty"`
    Password string `json:"password,omitempty"`
    
    // Job status
    Status   JobStatus `gorm:"default:'pending'" json:"status"`
    Progress int       `gorm:"default:0" json:"progress"`
    
    // Results
    Successful int `gorm:"default:0" json:"successful"`
    Failed     int `gorm:"default:0" json:"failed"`
    
    // Timing
    StartedAt   *time.Time `json:"started_at,omitempty"`
    CompletedAt *time.Time `json:"completed_at,omitempty"`
    
    // Error tracking
    ErrorMsg string `gorm:"type:text" json:"error_msg,omitempty"`
    
    // Job metadata
    TestMode bool `gorm:"default:false" json:"test_mode"`
    Priority int  `gorm:"default:0" json:"priority"`
}
```

**Job Status Types**:
- `pending`: Waiting in queue
- `running`: Currently processing
- `completed`: Finished successfully
- `failed`: Failed with errors
- `cancelled`: Cancelled by user

**Methods**:

| Method | Description | Returns |
|--------|-------------|---------|
| `IsCompleted()` | Checks if job is in terminal state | `bool` |
| `CanBeCancelled()` | Checks if job can be cancelled | `bool` |
| `GetDuration()` | Returns job execution duration | `time.Duration` |
| `GetProgress()` | Returns progress percentage (0-100) | `float64` |
| `GetSuccessRate()` | Returns success rate percentage | `float64` |
| `Start()` | Marks job as started | `void` |
| `Complete()` | Marks job as completed | `void` |
| `Fail(msg)` | Marks job as failed with error message | `void` |
| `Cancel()` | Marks job as cancelled | `void` |
| `IncrementProgress(successful)` | Increments progress counter | `void` |
| `ToJSON()` | Converts job to JSON-safe map with stats | `map[string]interface{}` |

**Example Usage**:
```go
job := &models.Job{
    ID:       uuid.New().String(),
    Count:    10,
    Status:   models.JobStatusPending,
    Priority: 1,
}

// Start job
job.Start()
db.UpdateJob(job)

// Process accounts
for i := 0; i < job.Count; i++ {
    success := processAccount()
    job.IncrementProgress(success)
    db.UpdateJobProgress(job.ID, job.Progress, job.Successful, job.Failed)
}

// Complete job
job.Complete()
db.UpdateJob(job)

// Get JSON representation with stats
stats := job.ToJSON()
fmt.Printf("Progress: %.2f%%, Success Rate: %.2f%%\n", 
    job.GetProgress(), job.GetSuccessRate())
```

---

## Database Service (`services/database.go`)

### Initialization

```go
db, err := services.NewDatabase(cfg)
if err != nil {
    log.Fatal(err)
}
defer db.Close()
```

### Core Operations

#### Account Operations

**Create Account**:
```go
account := &models.Account{
    Email:    "user@hotmail.com",
    Username: "kickuser123",
    Password: "pass123",
}
err := db.CreateAccount(account)
```

**Get Account by ID**:
```go
account, err := db.GetAccount(123)
```

**Get Account by Email**:
```go
account, err := db.GetAccountByEmail("user@hotmail.com")
```

**Get Account by Username**:
```go
account, err := db.GetAccountByUsername("kickuser123")
```

**List Accounts** (with pagination):
```go
accounts, err := db.ListAccounts(limit, offset)
```

**Get Accounts by Status**:
```go
accounts, err := db.GetAccountsByStatus("active", 20, 0)
```

**Get Accounts by Job ID**:
```go
accounts, err := db.GetAccountsByJobID("job-uuid-123")
```

**Update Account**:
```go
account.Status = "banned"
err := db.UpdateAccount(account)
```

**Update Account Status**:
```go
err := db.UpdateAccountStatus(123, "suspended")
```

**Delete Account** (soft delete):
```go
err := db.DeleteAccount(123)
```

**Get Account Statistics**:
```go
stats, err := db.GetAccountStats()
fmt.Printf("Total: %d, Active: %d, Banned: %d\n", 
    stats.Total, stats.Active, stats.Banned)
```

**Count Operations**:
```go
total, err := db.CountAccounts()
activeCount, err := db.CountAccountsByStatus("active")
```

---

#### Job Operations

**Create Job**:
```go
job := &models.Job{
    ID:       uuid.New().String(),
    Count:    5,
    Status:   models.JobStatusPending,
    Priority: 1,
}
err := db.CreateJob(job)
```

**Get Job by ID**:
```go
job, err := db.GetJob("job-uuid-123")
```

**List Jobs** (with pagination):
```go
jobs, err := db.ListJobs(limit, offset)
```

**Get Jobs by Status**:
```go
jobs, err := db.GetJobsByStatus(models.JobStatusRunning, 20, 0)
```

**Get Pending Jobs** (ordered by priority):
```go
jobs, err := db.GetPendingJobs()
```

**Update Job**:
```go
job.Status = models.JobStatusCompleted
err := db.UpdateJob(job)
```

**Update Job Progress**:
```go
err := db.UpdateJobProgress(jobID, progress, successful, failed)
```

**Delete Job** (soft delete):
```go
err := db.DeleteJob("job-uuid-123")
```

**Get Job Statistics**:
```go
stats, err := db.GetJobStats()
fmt.Printf("Total: %d, Completed: %d, Failed: %d\n", 
    stats.Total, stats.Completed, stats.Failed)
```

**Count Jobs**:
```go
total, err := db.CountJobs()
```

---

### Transaction Support

The database service provides full transaction support with automatic rollback on errors.

**WithTransaction Method**:
```go
err := db.WithTransaction(func(tx *gorm.DB) error {
    // All operations within this function are in a transaction
    
    account := &models.Account{...}
    if err := tx.Create(account).Error; err != nil {
        return err // Automatically rolls back
    }
    
    job := &models.Job{...}
    if err := tx.Create(job).Error; err != nil {
        return err // Automatically rolls back
    }
    
    return nil // Commits transaction
})
```

**Batch Operations** (use transactions internally):

**Create Accounts Batch**:
```go
accounts := []*models.Account{
    {Email: "user1@hotmail.com", Username: "user1", ...},
    {Email: "user2@hotmail.com", Username: "user2", ...},
    {Email: "user3@hotmail.com", Username: "user3", ...},
}

err := db.CreateAccountsBatch(accounts)
// All accounts created atomically or none
```

**Bulk Update Account Status**:
```go
accountIDs := []uint{1, 2, 3, 4, 5}
err := db.BulkUpdateAccountStatus(accountIDs, "banned")
// All statuses updated atomically or none
```

---

### Advanced Usage Examples

#### 1. Process Job with Transaction Safety

```go
func ProcessJob(db *services.Database, jobID string) error {
    return db.WithTransaction(func(tx *gorm.DB) error {
        // Get job
        var job models.Job
        if err := tx.First(&job, "id = ?", jobID).Error; err != nil {
            return err
        }
        
        // Start job
        job.Start()
        if err := tx.Save(&job).Error; err != nil {
            return err
        }
        
        // Create accounts
        for i := 0; i < job.Count; i++ {
            account := generateAccount()
            account.JobID = jobID
            
            if err := tx.Create(account).Error; err != nil {
                job.Fail(err.Error())
                tx.Save(&job)
                return err
            }
            
            job.IncrementProgress(true)
        }
        
        // Complete job
        job.Complete()
        return tx.Save(&job).Error
    })
}
```

#### 2. Batch Account Creation with Error Handling

```go
func CreateAccountsForJob(db *services.Database, jobID string, count int) error {
    accounts := make([]*models.Account, count)
    
    for i := 0; i < count; i++ {
        accounts[i] = &models.Account{
            Email:         fmt.Sprintf("user%d@hotmail.com", i),
            Username:      fmt.Sprintf("user%d", i),
            Password:      generatePassword(),
            EmailPassword: generatePassword(),
            JobID:         jobID,
            Status:        "active",
        }
        
        // Validate before creating
        if err := accounts[i].Validate(); err != nil {
            return fmt.Errorf("validation failed for account %d: %w", i, err)
        }
    }
    
    // Create all accounts atomically
    return db.CreateAccountsBatch(accounts)
}
```

#### 3. Get Comprehensive Statistics

```go
func GetDashboardStats(db *services.Database) (map[string]interface{}, error) {
    accountStats, err := db.GetAccountStats()
    if err != nil {
        return nil, err
    }
    
    jobStats, err := db.GetJobStats()
    if err != nil {
        return nil, err
    }
    
    totalAccounts, _ := db.CountAccounts()
    totalJobs, _ := db.CountJobs()
    
    return map[string]interface{}{
        "accounts": map[string]interface{}{
            "total":     totalAccounts,
            "active":    accountStats.Active,
            "banned":    accountStats.Banned,
            "suspended": accountStats.Suspended,
            "today":     accountStats.Today,
        },
        "jobs": map[string]interface{}{
            "total":     totalJobs,
            "pending":   jobStats.Pending,
            "running":   jobStats.Running,
            "completed": jobStats.Completed,
            "failed":    jobStats.Failed,
        },
    }, nil
}
```

---

## Database Health Checks

```go
// Check database connection health
if err := db.Health(); err != nil {
    log.Printf("Database health check failed: %v", err)
}
```

---

## Migration

Models are automatically migrated on initialization:

```go
db.AutoMigrate(
    &models.Account{},
    &models.Job{},
)
```

**Manual Migration** (if needed):
```go
sqlDB, _ := db.GetDB().DB()
// Run custom SQL migrations
```

---

## Best Practices

### 1. Always Use Transactions for Multi-Step Operations
```go
// ✅ Good
err := db.WithTransaction(func(tx *gorm.DB) error {
    // Multiple operations
    return nil
})

// ❌ Bad
db.CreateAccount(account1)
db.CreateAccount(account2) // What if this fails?
```

### 2. Validate Before Creating
```go
// ✅ Good
if err := account.Validate(); err != nil {
    return err
}
db.CreateAccount(account)

// ❌ Bad
db.CreateAccount(account) // May fail with cryptic error
```

### 3. Use Batch Operations for Multiple Records
```go
// ✅ Good
db.CreateAccountsBatch(accounts) // Single transaction

// ❌ Bad
for _, account := range accounts {
    db.CreateAccount(account) // Multiple transactions
}
```

### 4. Always Handle Errors
```go
// ✅ Good
account, err := db.GetAccount(id)
if err != nil {
    if errors.Is(err, gorm.ErrRecordNotFound) {
        return fiber.NewError(404, "Account not found")
    }
    return err
}

// ❌ Bad
account, _ := db.GetAccount(id)
```

### 5. Use Soft Delete for Data Retention
```go
// Soft delete (recommended)
db.DeleteAccount(id) // Sets DeletedAt timestamp

// Hard delete (use with caution)
db.GetDB().Unscoped().Delete(&models.Account{}, id)
```

---

## Performance Optimization

### 1. Connection Pooling
Already configured with optimal settings:
- Max open connections: 25
- Max idle connections: 5
- Connection lifetime: 15 minutes

### 2. Indexing
Key fields are indexed:
- `email` (unique index)
- `username` (unique index)
- `job_id` (index)
- `deleted_at` (index for soft deletes)

### 3. Pagination
Always use pagination for large datasets:
```go
limit := 20
offset := 0
accounts, err := db.ListAccounts(limit, offset)
```

### 4. Query Optimization
```go
// ✅ Good: Specific query
db.GetAccountsByStatus("active", 20, 0)

// ❌ Bad: Load all and filter
accounts, _ := db.ListAccounts(1000, 0)
// Filter in memory
```

---

## Error Handling

Common GORM errors:
```go
import "errors"
import "gorm.io/gorm"

if errors.Is(err, gorm.ErrRecordNotFound) {
    // Record not found
}

if errors.Is(err, gorm.ErrInvalidTransaction) {
    // Transaction error
}

if errors.Is(err, gorm.ErrDuplicatedKey) {
    // Unique constraint violation
}
```

---

## Testing

Example test setup:
```go
func setupTestDB() (*services.Database, error) {
    cfg := &config.Config{
        Database: config.DatabaseConfig{
            Driver: "sqlite",
            DSN:    ":memory:", // In-memory database for tests
        },
    }
    return services.NewDatabase(cfg)
}

func TestCreateAccount(t *testing.T) {
    db, err := setupTestDB()
    require.NoError(t, err)
    defer db.Close()
    
    account := &models.Account{
        Email:    "test@example.com",
        Username: "testuser",
        Password: "pass123",
    }
    
    err = db.CreateAccount(account)
    assert.NoError(t, err)
    assert.NotZero(t, account.ID)
}
```

---

## Complete Method Reference

### Database Service Methods

**Account Operations**:
- `CreateAccount(account *Account) error`
- `GetAccount(id uint) (*Account, error)`
- `GetAccountByEmail(email string) (*Account, error)`
- `GetAccountByUsername(username string) (*Account, error)`
- `ListAccounts(limit, offset int) ([]Account, error)`
- `GetAccountsByStatus(status string, limit, offset int) ([]Account, error)`
- `GetAccountsByJobID(jobID string) ([]Account, error)`
- `UpdateAccount(account *Account) error`
- `UpdateAccountStatus(id uint, status string) error`
- `DeleteAccount(id uint) error`
- `GetAccountStats() (*AccountStats, error)`
- `CountAccounts() (int64, error)`
- `CountAccountsByStatus(status string) (int64, error)`
- `CreateAccountsBatch(accounts []*Account) error`
- `BulkUpdateAccountStatus(ids []uint, status string) error`

**Job Operations**:
- `CreateJob(job *Job) error`
- `GetJob(id string) (*Job, error)`
- `ListJobs(limit, offset int) ([]Job, error)`
- `GetJobsByStatus(status JobStatus, limit, offset int) ([]Job, error)`
- `GetPendingJobs() ([]Job, error)`
- `UpdateJob(job *Job) error`
- `UpdateJobProgress(id string, progress, successful, failed int) error`
- `DeleteJob(id string) error`
- `GetJobStats() (*JobStats, error)`
- `CountJobs() (int64, error)`

**Utility Operations**:
- `GetDB() *gorm.DB`
- `Close() error`
- `Health() error`
- `WithTransaction(fn func(*gorm.DB) error) error`

---

## Summary

✅ **Complete database layer** with Account and Job models  
✅ **Connection pooling** configured for optimal performance  
✅ **Transaction support** for atomic operations  
✅ **Batch operations** for efficient bulk updates  
✅ **Comprehensive CRUD operations** for all models  
✅ **Advanced helper methods** for common queries  
✅ **Soft delete** support for data retention  
✅ **Proper indexing** on frequently queried fields  
✅ **Error handling** with GORM error types  
✅ **Production-ready** with best practices

The database layer is fully implemented, tested, and ready for production use!
