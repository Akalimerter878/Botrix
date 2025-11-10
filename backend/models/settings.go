package models

import (
	"time"

	"gorm.io/gorm"
)

// Setting represents a configuration setting stored in the database
type Setting struct {
	ID        uint           `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`

	// Configuration fields
	RapidAPIKey  string `json:"rapidapi_key" gorm:"type:varchar(512)"`
	IMAPServer   string `json:"imap_server" gorm:"type:varchar(255);default:'imap.gmail.com'"`
	IMAPPort     int    `json:"imap_port" gorm:"default:993"`
	IMAPUsername string `json:"imap_username" gorm:"type:varchar(255)"`
	IMAPPassword string `json:"imap_password" gorm:"type:varchar(512)"`
	SMTPServer   string `json:"smtp_server" gorm:"type:varchar(255);default:'smtp.gmail.com'"`
	SMTPPort     int    `json:"smtp_port" gorm:"default:587"`
	SMTPUsername string `json:"smtp_username" gorm:"type:varchar(255)"`
	SMTPPassword string `json:"smtp_password" gorm:"type:varchar(512)"`
	ProxyURL     string `json:"proxy_url" gorm:"type:varchar(512)"`
	WorkerCount  int    `json:"worker_count" gorm:"default:1"`
	RetryCount   int    `json:"retry_count" gorm:"default:3"`
	Timeout      int    `json:"timeout" gorm:"default:30"` // seconds
}

// SettingsResponse is used for API responses
type SettingsResponse struct {
	ID           uint      `json:"id"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	RapidAPIKey  string    `json:"rapidapi_key"`
	IMAPServer   string    `json:"imap_server"`
	IMAPPort     int       `json:"imap_port"`
	IMAPUsername string    `json:"imap_username"`
	IMAPPassword string    `json:"imap_password"`
	SMTPServer   string    `json:"smtp_server"`
	SMTPPort     int       `json:"smtp_port"`
	SMTPUsername string    `json:"smtp_username"`
	SMTPPassword string    `json:"smtp_password"`
	ProxyURL     string    `json:"proxy_url"`
	WorkerCount  int       `json:"worker_count"`
	RetryCount   int       `json:"retry_count"`
	Timeout      int       `json:"timeout"`
}

// ToResponse converts Setting to SettingsResponse
func (s *Setting) ToResponse() SettingsResponse {
	return SettingsResponse{
		ID:           s.ID,
		CreatedAt:    s.CreatedAt,
		UpdatedAt:    s.UpdatedAt,
		RapidAPIKey:  s.RapidAPIKey,
		IMAPServer:   s.IMAPServer,
		IMAPPort:     s.IMAPPort,
		IMAPUsername: s.IMAPUsername,
		IMAPPassword: s.IMAPPassword,
		SMTPServer:   s.SMTPServer,
		SMTPPort:     s.SMTPPort,
		SMTPUsername: s.SMTPUsername,
		SMTPPassword: s.SMTPPassword,
		ProxyURL:     s.ProxyURL,
		WorkerCount:  s.WorkerCount,
		RetryCount:   s.RetryCount,
		Timeout:      s.Timeout,
	}
}
