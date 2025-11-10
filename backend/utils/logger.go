package utils

import (
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// LogLevel represents the severity of a log message
type LogLevel int

const (
	// DEBUG level for detailed debugging information
	DEBUG LogLevel = iota
	// INFO level for general informational messages
	INFO
	// WARN level for warning messages
	WARN
	// ERROR level for error messages
	ERROR
	// FATAL level for fatal errors that cause program termination
	FATAL
)

// String returns the string representation of a log level
func (l LogLevel) String() string {
	switch l {
	case DEBUG:
		return "DEBUG"
	case INFO:
		return "INFO"
	case WARN:
		return "WARN"
	case ERROR:
		return "ERROR"
	case FATAL:
		return "FATAL"
	default:
		return "UNKNOWN"
	}
}

// Color returns ANSI color code for terminal output
func (l LogLevel) Color() string {
	switch l {
	case DEBUG:
		return "\033[36m" // Cyan
	case INFO:
		return "\033[32m" // Green
	case WARN:
		return "\033[33m" // Yellow
	case ERROR:
		return "\033[31m" // Red
	case FATAL:
		return "\033[35m" // Magenta
	default:
		return "\033[0m" // Reset
	}
}

// Logger is a custom logger with multiple output support
type Logger struct {
	mu            sync.RWMutex
	level         LogLevel
	outputs       []io.Writer
	enableColor   bool
	enableCaller  bool
	enableTime    bool
	timeFormat    string
	prefix        string
	component     string
	contextFields map[string]interface{}
}

var (
	defaultLogger *Logger
	once          sync.Once
)

// GetDefaultLogger returns the default logger instance
func GetDefaultLogger() *Logger {
	once.Do(func() {
		defaultLogger = NewLogger(LoggerConfig{
			Level:        INFO,
			EnableColor:  true,
			EnableCaller: true,
			EnableTime:   true,
			TimeFormat:   "2006-01-02 15:04:05.000",
			Outputs:      []io.Writer{os.Stdout},
		})
	})
	return defaultLogger
}

// LoggerConfig holds configuration for creating a logger
type LoggerConfig struct {
	Level        LogLevel
	EnableColor  bool
	EnableCaller bool
	EnableTime   bool
	TimeFormat   string
	Outputs      []io.Writer
	Prefix       string
	Component    string
}

// NewLogger creates a new logger instance
func NewLogger(config LoggerConfig) *Logger {
	if config.TimeFormat == "" {
		config.TimeFormat = "2006-01-02 15:04:05.000"
	}

	if len(config.Outputs) == 0 {
		config.Outputs = []io.Writer{os.Stdout}
	}

	return &Logger{
		level:         config.Level,
		outputs:       config.Outputs,
		enableColor:   config.EnableColor,
		enableCaller:  config.EnableCaller,
		enableTime:    config.EnableTime,
		timeFormat:    config.TimeFormat,
		prefix:        config.Prefix,
		component:     config.Component,
		contextFields: make(map[string]interface{}),
	}
}

// SetLevel sets the minimum log level
func (l *Logger) SetLevel(level LogLevel) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.level = level
}

// GetLevel returns the current log level
func (l *Logger) GetLevel() LogLevel {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.level
}

// AddOutput adds an output writer
func (l *Logger) AddOutput(output io.Writer) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.outputs = append(l.outputs, output)
}

// WithField adds a context field to the logger
func (l *Logger) WithField(key string, value interface{}) *Logger {
	l.mu.RLock()
	defer l.mu.RUnlock()

	newLogger := &Logger{
		level:         l.level,
		outputs:       l.outputs,
		enableColor:   l.enableColor,
		enableCaller:  l.enableCaller,
		enableTime:    l.enableTime,
		timeFormat:    l.timeFormat,
		prefix:        l.prefix,
		component:     l.component,
		contextFields: make(map[string]interface{}),
	}

	for k, v := range l.contextFields {
		newLogger.contextFields[k] = v
	}
	newLogger.contextFields[key] = value
	return newLogger
}

// WithFields adds multiple context fields to the logger
func (l *Logger) WithFields(fields map[string]interface{}) *Logger {
	l.mu.RLock()
	defer l.mu.RUnlock()

	newLogger := &Logger{
		level:         l.level,
		outputs:       l.outputs,
		enableColor:   l.enableColor,
		enableCaller:  l.enableCaller,
		enableTime:    l.enableTime,
		timeFormat:    l.timeFormat,
		prefix:        l.prefix,
		component:     l.component,
		contextFields: make(map[string]interface{}),
	}

	for k, v := range l.contextFields {
		newLogger.contextFields[k] = v
	}
	for k, v := range fields {
		newLogger.contextFields[k] = v
	}
	return newLogger
}

// WithComponent creates a logger with a specific component name
func (l *Logger) WithComponent(component string) *Logger {
	l.mu.RLock()
	defer l.mu.RUnlock()

	newLogger := &Logger{
		level:         l.level,
		outputs:       l.outputs,
		enableColor:   l.enableColor,
		enableCaller:  l.enableCaller,
		enableTime:    l.enableTime,
		timeFormat:    l.timeFormat,
		prefix:        l.prefix,
		component:     component,
		contextFields: make(map[string]interface{}),
	}

	for k, v := range l.contextFields {
		newLogger.contextFields[k] = v
	}
	return newLogger
}

// log is the internal logging function
func (l *Logger) log(level LogLevel, format string, args ...interface{}) {
	l.mu.RLock()
	if level < l.level {
		l.mu.RUnlock()
		return
	}
	l.mu.RUnlock()

	var msg strings.Builder

	// Add color if enabled
	if l.enableColor {
		msg.WriteString(level.Color())
	}

	// Add timestamp
	if l.enableTime {
		msg.WriteString(time.Now().Format(l.timeFormat))
		msg.WriteString(" ")
	}

	// Add level
	msg.WriteString(fmt.Sprintf("[%-5s]", level.String()))

	// Add component
	if l.component != "" {
		msg.WriteString(fmt.Sprintf(" [%s]", l.component))
	}

	// Add prefix
	if l.prefix != "" {
		msg.WriteString(fmt.Sprintf(" [%s]", l.prefix))
	}

	// Add caller information
	if l.enableCaller {
		_, file, line, ok := runtime.Caller(2)
		if ok {
			msg.WriteString(fmt.Sprintf(" [%s:%d]", filepath.Base(file), line))
		}
	}

	// Add message
	msg.WriteString(" ")
	if len(args) > 0 {
		msg.WriteString(fmt.Sprintf(format, args...))
	} else {
		msg.WriteString(format)
	}

	// Add context fields
	if len(l.contextFields) > 0 {
		msg.WriteString(" |")
		for k, v := range l.contextFields {
			msg.WriteString(fmt.Sprintf(" %s=%v", k, v))
		}
	}

	// Reset color if enabled
	if l.enableColor {
		msg.WriteString("\033[0m")
	}

	msg.WriteString("\n")

	// Write to all outputs
	l.mu.RLock()
	for _, output := range l.outputs {
		output.Write([]byte(msg.String()))
	}
	l.mu.RUnlock()

	// For FATAL, exit the program
	if level == FATAL {
		os.Exit(1)
	}
}

// Debug logs a debug message
func (l *Logger) Debug(format string, args ...interface{}) {
	l.log(DEBUG, format, args...)
}

// Info logs an info message
func (l *Logger) Info(format string, args ...interface{}) {
	l.log(INFO, format, args...)
}

// Warn logs a warning message
func (l *Logger) Warn(format string, args ...interface{}) {
	l.log(WARN, format, args...)
}

// Error logs an error message
func (l *Logger) Error(format string, args ...interface{}) {
	l.log(ERROR, format, args...)
}

// Fatal logs a fatal message and exits
func (l *Logger) Fatal(format string, args ...interface{}) {
	l.log(FATAL, format, args...)
}

// Package-level convenience functions

// Debug logs a debug message using the default logger
func Debug(format string, args ...interface{}) {
	GetDefaultLogger().Debug(format, args...)
}

// Info logs an info message using the default logger
func Info(format string, args ...interface{}) {
	GetDefaultLogger().Info(format, args...)
}

// Warn logs a warning message using the default logger
func Warn(format string, args ...interface{}) {
	GetDefaultLogger().Warn(format, args...)
}

// Error logs an error message using the default logger
func Error(format string, args ...interface{}) {
	GetDefaultLogger().Error(format, args...)
}

// Fatal logs a fatal message and exits using the default logger
func Fatal(format string, args ...interface{}) {
	GetDefaultLogger().Fatal(format, args...)
}

// InitFileLogger creates a file logger that writes to both console and file
func InitFileLogger(logDir string, logLevel LogLevel) (*Logger, error) {
	// Create logs directory if it doesn't exist
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create log directory: %v", err)
	}

	// Create log file with timestamp
	timestamp := time.Now().Format("2006-01-02")
	logFile := filepath.Join(logDir, fmt.Sprintf("botrix-%s.log", timestamp))

	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, fmt.Errorf("failed to open log file: %v", err)
	}

	logger := NewLogger(LoggerConfig{
		Level:        logLevel,
		EnableColor:  true,
		EnableCaller: true,
		EnableTime:   true,
		TimeFormat:   "2006-01-02 15:04:05.000",
		Outputs:      []io.Writer{os.Stdout, file},
	})

	return logger, nil
}

// RedirectStandardLogger redirects Go's standard logger to our custom logger
func RedirectStandardLogger() {
	log.SetOutput(&logWriter{logger: GetDefaultLogger()})
	log.SetFlags(0) // Remove default flags since our logger handles them
}

// logWriter implements io.Writer to redirect standard log to our logger
type logWriter struct {
	logger *Logger
}

func (w *logWriter) Write(p []byte) (n int, err error) {
	msg := string(p)
	msg = strings.TrimSuffix(msg, "\n")
	w.logger.Info(msg)
	return len(p), nil
}
