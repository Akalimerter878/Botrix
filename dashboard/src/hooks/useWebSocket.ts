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
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectAttemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  const hasShownConnectedToastRef = useRef(false);
  const isMountedRef = useRef(true);

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

  const clearPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const startPingInterval = useCallback(() => {
    clearPingInterval();
    
    // Send ping every 25 seconds to keep connection alive (backend pings every 30s)
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          console.log('[WebSocket] Sent periodic keepalive ping');
        } catch (e) {
          console.error('[WebSocket] Failed to send ping:', e);
        }
      }
    }, 25000); // 25 seconds (before backend timeout)
  }, [clearPingInterval]);

  const connect = useCallback(() => {
    // Don't connect if component is unmounted or already connecting
    if (!isMountedRef.current) {
      console.log('[WebSocket] Skipping connect - component unmounted');
      return;
    }

    // Prevent rapid reconnections - debounce
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('[WebSocket] Skipping connect - already connected/connecting');
      return;
    }

    // Close existing connection if any
    if (wsRef.current) {
      console.log('[WebSocket] Closing existing connection before reconnect');
      wsRef.current.close(1000, 'Reconnecting');
      wsRef.current = null;
    }

    try {
      console.log('[WebSocket] Connecting to', WS_URL);
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WebSocket] Connection established');
        console.log('[WebSocket] ReadyState:', ws.readyState);
        setConnectionState('connected');
        setReconnectAttempts(0);
        reconnectAttemptsRef.current = 0;
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
        clearReconnectTimeout();

        // Show success toast only after first reconnection (not on initial connect)
        if (hasShownConnectedToastRef.current) {
          toast.success('WebSocket reconnected');
        }
        hasShownConnectedToastRef.current = true;

        // Wait a bit before sending initial ping (let server setup connection)
        setTimeout(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
              console.log('[WebSocket] Sent initial keepalive ping');
            } catch (e) {
              console.error('[WebSocket] Failed to send initial ping:', e);
            }
          }
        }, 1000); // Wait 1 second before first ping

        // Start sending periodic pings
        startPingInterval();
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
        console.log('[WebSocket] Connection closed');
        console.log('[WebSocket] Close code:', event.code);
        console.log('[WebSocket] Close reason:', event.reason || '(no reason provided)');
        console.log('[WebSocket] Was clean close:', event.wasClean);
        console.log('[WebSocket] isMounted:', isMountedRef.current);
        
        setConnectionState('disconnected');
        wsRef.current = null;
        
        // Stop ping interval
        clearPingInterval();
        
        // Don't reconnect if closed normally or component unmounted
        if (event.code === 1000 || event.code === 1001 || !isMountedRef.current) {
          console.log('[WebSocket] Normal closure (code 1000/1001) or unmounted, not reconnecting');
          return;
        }
        
        // If close code is 1006 (abnormal), log it specially
        if (event.code === 1006) {
          console.warn('[WebSocket] Abnormal closure (1006) - connection dropped unexpectedly');
        }
        
        // Only show toast if connection was previously established
        if (hasShownConnectedToastRef.current && reconnectAttemptsRef.current === 0) {
          toast.error('WebSocket disconnected');
        }

        // Schedule reconnection only if not at max attempts
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const newAttempts = reconnectAttemptsRef.current + 1;
          reconnectAttemptsRef.current = newAttempts;
          setReconnectAttempts(newAttempts);
          
          const delay = reconnectDelayRef.current;
          console.log(`[WebSocket] Scheduling reconnection in ${delay}ms (attempt ${newAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
          setConnectionState('reconnecting');
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('[WebSocket] Attempting reconnection...');
            connect();
          }, delay);
          
          reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY);
        } else {
          console.log('[WebSocket] Max reconnection attempts reached');
          toast.error('Failed to reconnect to server');
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
  }, [clearReconnectTimeout, startPingInterval, clearPingInterval]);

  // Manual reconnect function
  const reconnect = useCallback(() => {
    console.log('[WebSocket] Manual reconnection triggered');
    setReconnectAttempts(0);
    reconnectAttemptsRef.current = 0;
    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
    clearReconnectTimeout();
    connect();
  }, [connect, clearReconnectTimeout]);

  useEffect(() => {
    // Mark component as mounted
    isMountedRef.current = true;
    
    // Connect only once on mount
    connect();

    return () => {
      console.log('[WebSocket] Cleaning up connection');
      isMountedRef.current = false;
      clearReconnectTimeout();
      clearPingInterval();
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
