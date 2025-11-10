import { createContext, useContext, ReactNode, useMemo } from 'react';
import { useWebSocket, ConnectionState } from '../hooks/useWebSocket';
import type { WebSocketMessage } from '@/types';

interface WebSocketContextType {
  connectionState: ConnectionState;
  isConnected: boolean;
  reconnectAttempts: number;
  lastMessage: WebSocketMessage | null;
  send: (message: any) => void;
  reconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
  onMessage?: (message: WebSocketMessage) => void;
}

export function WebSocketProvider({ children, onMessage }: WebSocketProviderProps) {
  const websocket = useWebSocket(onMessage);

  // Memoize the context value to prevent unnecessary re-renders
  const value = useMemo(() => websocket, [
    websocket.connectionState,
    websocket.isConnected,
    websocket.reconnectAttempts,
    websocket.lastMessage,
    websocket.send,
    websocket.reconnect
  ]);

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
}
