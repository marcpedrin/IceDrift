import { useEffect, useRef, useState, useCallback } from 'react';
import { getShipsWebSocketUrl } from '@/services/api';
import type { Ship } from '@/types';

interface WSMessage {
  type: string;
  timestamp: string;
  ships: Ship[];
}

interface UseWebSocketReturn {
  ships: Ship[];
  lastUpdate: string | null;
  isConnected: boolean;
  error: string | null;
}

export function useWebSocket(): UseWebSocketReturn {
  const [ships, setShips] = useState<Ship[]>([]);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCount = useRef(0);

  const connect = useCallback(() => {
    const url = getShipsWebSocketUrl();

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        retryCount.current = 0;
        console.log('[WS] Connected to ships WebSocket');
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          if (msg.type === 'ship_update') {
            setShips(msg.ships);
            setLastUpdate(msg.timestamp);
          }
        } catch {
          console.warn('[WS] Failed to parse message:', event.data);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Exponential backoff reconnect (max 30s)
        const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
        retryCount.current++;
        console.log(`[WS] Disconnected. Reconnecting in ${delay}ms...`);
        reconnectTimer.current = setTimeout(connect, delay);
      };
    } catch (exc) {
      console.error('[WS] Failed to create WebSocket:', exc);
      setError('Failed to connect to live ship data');
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { ships, lastUpdate, isConnected, error };
}
