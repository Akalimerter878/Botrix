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
        wsRef.current = null;
        
        // Don't reconnect if closed normally (code 1000 or 1001)
        if (event.code === 1000 || event.code === 1001) {
          console.log('[WebSocket] Normal closure, not reconnecting');
          return;
        }
        
        // Only show toast if connection was previously established
        if (hasShownConnectedToastRef.current && reconnectAttempts === 0) {
          toast.error('WebSocket disconnected');
        }

        // Schedule reconnection only if not at max attempts
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          setReconnectAttempts((prev) => prev + 1);
          const delay = reconnectDelayRef.current;
          console.log(`[WebSocket] Will reconnect in ${delay}ms`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
          
          reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error occurred:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      setConnectionState('disconnected');
    }
  }, [clearReconnectTimeout, reconnectAttempts]);

  // Manual reconnect function
  const reconnect = useCallback(() => {
    console.log('[WebSocket] Manual reconnection triggered');
    setReconnectAttempts(0);
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
    clearReconnectTimeout();
    connect();
  }, [connect, clearReconnectTimeout]);

  useEffect(() => {
    // Connect only once on mount
    connect();

    return () => {
      console.log('[WebSocket] Cleaning up connection');
      clearReconnectTimeout();
      if (wsRef.current) {
        // Send normal close code to prevent reconnection
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount/unmount

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
