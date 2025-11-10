import { createContext, useContext, ReactNode } from 'react';
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

  return (
    <WebSocketContext.Provider value={websocket}>
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
