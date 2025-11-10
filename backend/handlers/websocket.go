package handlers

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"botrix-backend/utils"

	"github.com/go-redis/redis/v8"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/websocket/v2"
)

// WebSocketMessage represents the structure of messages sent to clients
type WebSocketMessage struct {
	Type   string                 `json:"type"`
	JobID  string                 `json:"job_id,omitempty"`
	Status string                 `json:"status,omitempty"`
	Data   map[string]interface{} `json:"data,omitempty"`
}

// Client represents a connected WebSocket client
type Client struct {
	ID         string
	Conn       *websocket.Conn
	SendChan   chan []byte
	DisconnCh  chan bool
	LastActive time.Time
}

// WebSocketHandler manages WebSocket connections and Redis subscriptions
type WebSocketHandler struct {
	clients      map[string]*Client
	clientsMutex sync.RWMutex
	register     chan *Client
	unregister   chan *Client
	broadcast    chan []byte
	redisClient  *redis.Client
	ctx          context.Context
	logger       *utils.Logger
}

// NewWebSocketHandler creates a new WebSocket handler (legacy)
func NewWebSocketHandler(redisClient *redis.Client) *WebSocketHandler {
	return NewWebSocketHandlerWithLogger(redisClient, utils.GetDefaultLogger().WithComponent("WEBSOCKET"))
}

// NewWebSocketHandlerWithLogger creates a new WebSocket handler with custom logger
func NewWebSocketHandlerWithLogger(redisClient *redis.Client, logger *utils.Logger) *WebSocketHandler {
	handler := &WebSocketHandler{
		clients:     make(map[string]*Client),
		register:    make(chan *Client),
		unregister:  make(chan *Client),
		broadcast:   make(chan []byte, 256),
		redisClient: redisClient,
		ctx:         context.Background(),
		logger:      logger,
	}

	// Start the hub goroutine
	go handler.run()

	// Start Redis subscriber
	go handler.subscribeToRedis()

	// Start ping ticker
	go handler.pingClients()

	return handler
}

// run handles client registration, unregistration, and broadcasting
func (h *WebSocketHandler) run() {
	for {
		select {
		case client := <-h.register:
			h.clientsMutex.Lock()
			h.clients[client.ID] = client
			total := len(h.clients)
			h.clientsMutex.Unlock()

			h.logger.WithFields(map[string]interface{}{
				"client_id": client.ID,
				"total":     total,
			}).Info("Client registered")

		case client := <-h.unregister:
			h.clientsMutex.Lock()
			if _, ok := h.clients[client.ID]; ok {
				delete(h.clients, client.ID)
				close(client.SendChan)
				total := len(h.clients)
				h.clientsMutex.Unlock()

				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"total":     total,
				}).Info("Client unregistered")
			} else {
				h.clientsMutex.Unlock()
			}

		case message := <-h.broadcast:
			h.clientsMutex.RLock()
			clientCount := len(h.clients)
			for _, client := range h.clients {
				select {
				case client.SendChan <- message:
					// Message sent successfully
				default:
					// Channel is full, close the client
					close(client.SendChan)
					delete(h.clients, client.ID)
					h.logger.WithField("client_id", client.ID).Warn("Client removed due to slow consumer")
				}
			}
			h.clientsMutex.RUnlock()

			if clientCount > 0 {
				h.logger.WithField("clients", clientCount).Debug("Message broadcasted")
			}
		}
	}
}

// subscribeToRedis subscribes to Redis pub/sub channel for job updates
func (h *WebSocketHandler) subscribeToRedis() {
	pubsub := h.redisClient.Subscribe(h.ctx, "botrix:jobs:updates")
	defer pubsub.Close()

	h.logger.Info("Subscribed to Redis channel: botrix:jobs:updates")

	// Wait for confirmation that subscription is created
	_, err := pubsub.Receive(h.ctx)
	if err != nil {
		h.logger.WithField("error", err.Error()).Error("Failed to subscribe to Redis channel")
		return
	}

	// Listen for messages
	ch := pubsub.Channel()
	for msg := range ch {
		// Parse the Redis message
		var redisData map[string]interface{}
		if err := json.Unmarshal([]byte(msg.Payload), &redisData); err != nil {
			h.logger.WithField("error", err.Error()).Error("Failed to parse Redis message")
			continue
		}

		// Create WebSocket message
		wsMessage := WebSocketMessage{
			Type:   "job_update",
			JobID:  getStringValue(redisData, "job_id"),
			Status: getStringValue(redisData, "status"),
			Data:   redisData,
		}

		// Broadcast to all connected clients
		messageBytes, err := json.Marshal(wsMessage)
		if err != nil {
			h.logger.WithField("error", err.Error()).Error("Failed to marshal WebSocket message")
			continue
		}

		h.broadcast <- messageBytes

		h.logger.WithFields(map[string]interface{}{
			"job_id":  wsMessage.JobID,
			"status":  wsMessage.Status,
			"clients": len(h.clients),
		}).Debug("Job update broadcasted")
	}
}

// pingClients sends ping messages to all clients every 30 seconds
func (h *WebSocketHandler) pingClients() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		h.clientsMutex.RLock()
		inactiveClients := make([]*Client, 0)

		for _, client := range h.clients {
			// Check if client has been inactive for too long (2 minutes)
			if time.Since(client.LastActive) > 2*time.Minute {
				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"inactive":  time.Since(client.LastActive).String(),
				}).Debug("Client inactive for too long, disconnecting")
				inactiveClients = append(inactiveClients, client)
				continue
			}

			// Send ping
			if err := client.Conn.WriteControl(websocket.PingMessage, []byte{}, time.Now().Add(10*time.Second)); err != nil {
				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"error":     err.Error(),
				}).Debug("Failed to send ping, client will be disconnected")
				inactiveClients = append(inactiveClients, client)
			}
		}
		h.clientsMutex.RUnlock()

		// Unregister inactive clients
		for _, client := range inactiveClients {
			h.unregister <- client
		}

		if len(h.clients) > 0 {
			h.logger.WithField("active_clients", len(h.clients)).Debug("Ping check completed")
		}
	}
}

// HandleWebSocket upgrades HTTP connection to WebSocket
func (h *WebSocketHandler) HandleWebSocket(c *websocket.Conn) {
	// Create new client
	client := &Client{
		ID:         generateClientID(),
		Conn:       c,
		SendChan:   make(chan []byte, 256),
		DisconnCh:  make(chan bool),
		LastActive: time.Now(),
	}

	h.logger.WithFields(map[string]interface{}{
		"client_id":   client.ID,
		"remote_addr": c.RemoteAddr().String(),
		"local_addr":  c.LocalAddr().String(),
	}).Info("New WebSocket connection established")

	// Register client
	h.register <- client

	// Start the write pump in a new goroutine
	go h.writePump(client)

	// Run the read pump in the current goroutine (blocking)
	h.readPump(client)
}

// readPump reads messages from the WebSocket connection
func (h *WebSocketHandler) readPump(client *Client) {
	defer func() {
		h.logger.WithField("client_id", client.ID).Debug("ReadPump exiting, unregistering client")
		h.unregister <- client
		client.Conn.Close()
	}()

	// Configure WebSocket settings
	client.Conn.SetReadDeadline(time.Now().Add(70 * time.Second)) // Longer timeout to allow ping/pong

	// Handle pong messages from client's pings
	client.Conn.SetPongHandler(func(string) error {
		client.LastActive = time.Now()
		client.Conn.SetReadDeadline(time.Now().Add(70 * time.Second))
		h.logger.WithField("client_id", client.ID).Debug("Received pong from client")
		return nil
	})

	// Handle ping messages from client (respond with pong)
	client.Conn.SetPingHandler(func(data string) error {
		client.LastActive = time.Now()
		client.Conn.SetReadDeadline(time.Now().Add(70 * time.Second))
		h.logger.WithField("client_id", client.ID).Debug("Received ping from client, sending pong")

		// Send pong response
		if err := client.Conn.WriteControl(websocket.PongMessage, []byte(data), time.Now().Add(10*time.Second)); err != nil {
			h.logger.WithFields(map[string]interface{}{
				"client_id": client.ID,
				"error":     err.Error(),
			}).Debug("Failed to send pong")
			return err
		}
		return nil
	})

	for {
		messageType, message, err := client.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure, websocket.CloseNormalClosure) {
				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"error":     err.Error(),
				}).Warn("Unexpected WebSocket close error")
			} else {
				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"error":     err.Error(),
				}).Debug("WebSocket connection closed normally")
			}
			break
		}

		client.LastActive = time.Now()
		client.Conn.SetReadDeadline(time.Now().Add(70 * time.Second))

		// Handle incoming messages
		if messageType == websocket.TextMessage {
			// Try to parse as JSON
			var msg map[string]interface{}
			if err := json.Unmarshal(message, &msg); err == nil {
				msgType, _ := msg["type"].(string)

				// Handle ping messages
				if msgType == "ping" {
					h.logger.WithField("client_id", client.ID).Debug("Received ping, sending pong")

					// Send pong response
					pongMsg := map[string]interface{}{
						"type":      "pong",
						"timestamp": time.Now().UnixMilli(),
					}
					if pongBytes, err := json.Marshal(pongMsg); err == nil {
						client.SendChan <- pongBytes
					}
					continue
				}

				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"type":      msgType,
					"message":   string(message),
				}).Debug("Received message from client")
			}
		}
	}
}

// writePump writes messages to the WebSocket connection
func (h *WebSocketHandler) writePump(client *Client) {
	ticker := time.NewTicker(54 * time.Second)
	defer func() {
		ticker.Stop()
		client.Conn.Close()
	}()

	for {
		select {
		case message, ok := <-client.SendChan:
			client.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				// Channel closed, send close message
				client.Conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := client.Conn.WriteMessage(websocket.TextMessage, message); err != nil {
				h.logger.WithFields(map[string]interface{}{
					"client_id": client.ID,
					"error":     err.Error(),
				}).Debug("Failed to write message to client")
				return
			}

		case <-ticker.C:
			// Send ping message
			client.Conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := client.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// GetStats returns WebSocket statistics
func (h *WebSocketHandler) GetStats(c *fiber.Ctx) error {
	h.clientsMutex.RLock()
	defer h.clientsMutex.RUnlock()

	return c.JSON(fiber.Map{
		"connected_clients": len(h.clients),
		"timestamp":         time.Now(),
	})
}

// Helper function to generate unique client ID
func generateClientID() string {
	return time.Now().Format("20060102150405") + "-" + randomString(8)
}

// Helper function to generate random string
func randomString(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = letters[time.Now().UnixNano()%int64(len(letters))]
	}
	return string(b)
}

// Helper function to safely get string value from map
func getStringValue(data map[string]interface{}, key string) string {
	if val, ok := data[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}
