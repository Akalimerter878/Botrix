package handlers

import (
	"context"
	"encoding/json"
	"log"
	"sync"
	"time"

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
}

// NewWebSocketHandler creates a new WebSocket handler
func NewWebSocketHandler(redisClient *redis.Client) *WebSocketHandler {
	handler := &WebSocketHandler{
		clients:     make(map[string]*Client),
		register:    make(chan *Client),
		unregister:  make(chan *Client),
		broadcast:   make(chan []byte, 256),
		redisClient: redisClient,
		ctx:         context.Background(),
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
			h.clientsMutex.Unlock()
			log.Printf("[WebSocket] Client registered: %s (Total: %d)", client.ID, len(h.clients))

		case client := <-h.unregister:
			h.clientsMutex.Lock()
			if _, ok := h.clients[client.ID]; ok {
				delete(h.clients, client.ID)
				close(client.SendChan)
				log.Printf("[WebSocket] Client unregistered: %s (Total: %d)", client.ID, len(h.clients))
			}
			h.clientsMutex.Unlock()

		case message := <-h.broadcast:
			h.clientsMutex.RLock()
			for _, client := range h.clients {
				select {
				case client.SendChan <- message:
					// Message sent successfully
				default:
					// Channel is full, close the client
					close(client.SendChan)
					delete(h.clients, client.ID)
					log.Printf("[WebSocket] Client removed due to slow consumer: %s", client.ID)
				}
			}
			h.clientsMutex.RUnlock()
		}
	}
}

// subscribeToRedis subscribes to Redis pub/sub channel for job updates
func (h *WebSocketHandler) subscribeToRedis() {
	pubsub := h.redisClient.Subscribe(h.ctx, "botrix:jobs:updates")
	defer pubsub.Close()

	log.Println("[WebSocket] Subscribed to Redis channel: botrix:jobs:updates")

	// Wait for confirmation that subscription is created
	_, err := pubsub.Receive(h.ctx)
	if err != nil {
		log.Printf("[WebSocket] Error subscribing to Redis: %v", err)
		return
	}

	// Listen for messages
	ch := pubsub.Channel()
	for msg := range ch {
		// Parse the Redis message
		var redisData map[string]interface{}
		if err := json.Unmarshal([]byte(msg.Payload), &redisData); err != nil {
			log.Printf("[WebSocket] Error parsing Redis message: %v", err)
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
			log.Printf("[WebSocket] Error marshaling message: %v", err)
			continue
		}

		h.broadcast <- messageBytes
		log.Printf("[WebSocket] Broadcasted update for job %s (status: %s) to %d clients",
			wsMessage.JobID, wsMessage.Status, len(h.clients))
	}
}

// pingClients sends ping messages to all clients every 30 seconds
func (h *WebSocketHandler) pingClients() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		h.clientsMutex.RLock()
		for _, client := range h.clients {
			// Check if client has been inactive for too long (2 minutes)
			if time.Since(client.LastActive) > 2*time.Minute {
				log.Printf("[WebSocket] Client %s inactive for too long, disconnecting", client.ID)
				h.unregister <- client
				continue
			}

			// Send ping
			if err := client.Conn.WriteControl(websocket.PingMessage, []byte{}, time.Now().Add(10*time.Second)); err != nil {
				log.Printf("[WebSocket] Error sending ping to client %s: %v", client.ID, err)
				h.unregister <- client
			}
		}
		h.clientsMutex.RUnlock()
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

	// Register client
	h.register <- client

	// Start goroutines for reading and writing
	go h.writePump(client)
	go h.readPump(client)
}

// readPump reads messages from the WebSocket connection
func (h *WebSocketHandler) readPump(client *Client) {
	defer func() {
		h.unregister <- client
		client.Conn.Close()
	}()

	// Set read deadline and pong handler
	client.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	client.Conn.SetPongHandler(func(string) error {
		client.LastActive = time.Now()
		client.Conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := client.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("[WebSocket] Unexpected close error for client %s: %v", client.ID, err)
			}
			break
		}

		client.LastActive = time.Now()

		// Handle incoming messages (for future use - subscriptions, filters, etc.)
		log.Printf("[WebSocket] Received message from client %s: %s", client.ID, string(message))
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
				log.Printf("[WebSocket] Error writing message to client %s: %v", client.ID, err)
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
