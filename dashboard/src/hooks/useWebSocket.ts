import { useEffect, useRef, useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import type { WebSocketMessage } from '@/types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws';
const INITIAL_RECONNECT_DELAY = 1000; // 1 second
const MAX_RECONNECT_DELAY = 30000; // 30 seconds
const MAX_RECONNECT_ATTEMPTS = 10;

export type ConnectionState = 'connected' | 'disconnected' | 'reconnecting';

export function useWebSocket(onMessage?: (message: WebSocketMessage) => void) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const onMessageRef = useRef(onMessage);
  const hasShownConnectedToastRef = useRef(false);

  // Keep onMessage ref updated
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    clearReconnectTimeout();

    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error('[WebSocket] Max reconnection attempts reached');
      toast.error('WebSocket connection failed. Please refresh the page.');
      setConnectionState('disconnected');
      return;
    }

    setConnectionState('reconnecting');
    const delay = reconnectDelayRef.current;

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      setReconnectAttempts((prev) => prev + 1);
      connect();
    }, delay);

    // Exponential backoff with max delay
    reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
  }, [reconnectAttempts]);

  const connect = useCallback(() => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      console.log('[WebSocket] Connecting to', WS_URL);
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WebSocket] Connection established');
        setConnectionState('connected');
        setReconnectAttempts(0);
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
        clearReconnectTimeout();

        // Show success toast only after first reconnection (not on initial connect)
        if (hasShownConnectedToastRef.current) {
          toast.success('WebSocket reconnected');
        }
        hasShownConnectedToastRef.current = true;
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] Message received:', message.type, message);
          setLastMessage(message);
          onMessageRef.current?.(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Connection closed', event.code, event.reason);
        setConnectionState('disconnected');
        
        // Only show toast if connection was previously established
        if (hasShownConnectedToastRef.current && reconnectAttempts === 0) {
          toast.error('WebSocket disconnected');
        }

        // Schedule reconnection
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error occurred:', error);
        setConnectionState('disconnected');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      setConnectionState('disconnected');
      scheduleReconnect();
    }
  }, [reconnectAttempts, scheduleReconnect, clearReconnectTimeout]);

  // Manual reconnect function
  const reconnect = useCallback(() => {
    console.log('[WebSocket] Manual reconnection triggered');
    setReconnectAttempts(0);
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
    clearReconnectTimeout();
    connect();
  }, [connect, clearReconnectTimeout]);

  useEffect(() => {
    connect();

    return () => {
      console.log('[WebSocket] Cleaning up connection');
      clearReconnectTimeout();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearReconnectTimeout]);

  const send = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      console.log('[WebSocket] Message sent:', message);
    } else {
      console.warn('[WebSocket] Cannot send message - connection not open');
    }
  }, []);

  return {
    connectionState,
    isConnected: connectionState === 'connected',
    reconnectAttempts,
    lastMessage,
    send,
    reconnect,
  };
}
