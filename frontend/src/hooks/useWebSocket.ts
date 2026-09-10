import { useEffect, useState, useCallback } from 'react';
import { fetchNearbyShips } from '@/services/api';
import type { Ship } from '@/types';

interface UseShipTrackingReturn {
  ships: Ship[];
  lastUpdate: string | null;
  isConnected: boolean;
  error: string | null;
}

export function useWebSocket(): UseShipTrackingReturn {
  const [ships, setShips] = useState<Ship[]>([]);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchShips = useCallback(async () => {
    try {
      const data = await fetchNearbyShips();
      setShips(data.ships);
      setLastUpdate(data.timestamp);
      setIsConnected(true);
      setError(null);
    } catch (err) {
      console.error('[ShipTracking] Failed to fetch ships:', err);
      setIsConnected(false);
      setError('Failed to fetch live ship data');
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchShips();

    // Poll every 10 seconds
    const intervalId = setInterval(fetchShips, 10000);

    return () => clearInterval(intervalId);
  }, [fetchShips]);

  return { ships, lastUpdate, isConnected, error };
}
