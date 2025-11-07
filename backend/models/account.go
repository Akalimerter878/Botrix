package models

import (
	"fmt"
	"time"

	"gorm.io/gorm"
)

// Account represents a generated Kick.com account
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

// AccountCreateRequest represents the request to create a new account
type AccountCreateRequest struct {
	Username string `json:"username,omitempty"`
	Password string `json:"password,omitempty"`
	Count    int    `json:"count" validate:"min=1,max=100"` // For batch creation
}

// AccountResponse represents the response for account operations
type AccountResponse struct {
	Success  bool      `json:"success"`
	Message  string    `json:"message,omitempty"`
	Account  *Account  `json:"account,omitempty"`
	Accounts []Account `json:"accounts,omitempty"`
	Error    string    `json:"error,omitempty"`
}

// AccountStats represents statistics about accounts
type AccountStats struct {
	Total     int64 `json:"total"`
	Active    int64 `json:"active"`
	Banned    int64 `json:"banned"`
	Suspended int64 `json:"suspended"`
	Today     int64 `json:"created_today"`
}

// TableName specifies the table name for Account model
func (Account) TableName() string {
	return "accounts"
}

// ToJSON converts account to JSON-safe representation (hides sensitive data)
func (a *Account) ToJSON() map[string]interface{} {
	return map[string]interface{}{
		"id":         a.ID,
		"email":      a.Email,
		"username":   a.Username,
		"status":     a.Status,
		"created_at": a.CreatedAt,
		"updated_at": a.UpdatedAt,
		"job_id":     a.JobID,
	}
}

// HidePasswords masks sensitive password information
func (a *Account) HidePasswords() {
	if a.Password != "" {
		a.Password = "********"
	}
	if a.EmailPassword != "" {
		a.EmailPassword = "********"
	}
}

// Validate checks if the account has all required fields
func (a *Account) Validate() error {
	if a.Email == "" {
		return fmt.Errorf("email is required")
	}
	if a.Username == "" {
		return fmt.Errorf("username is required")
	}
	if a.Password == "" {
		return fmt.Errorf("password is required")
	}
	if a.EmailPassword == "" {
		return fmt.Errorf("email_password is required")
	}
	return nil
}

// IsActive checks if the account is in active status
func (a *Account) IsActive() bool {
	return a.Status == "active"
}

// IsBanned checks if the account is banned
func (a *Account) IsBanned() bool {
	return a.Status == "banned"
}

// IsSuspended checks if the account is suspended
func (a *Account) IsSuspended() bool {
	return a.Status == "suspended"
}
