import { useEffect, useRef, useCallback, useState } from 'react';

export interface Position {
    symbol: string;
    side: 'LONG' | 'SHORT' | 'FLAT' | 'BOTH';
    quantity: number;
    entry_price: number;
    unrealized_pnl: number;
    margin_type?: string;
    isolated_wallet?: string;
    timestamp?: string;
}

interface WebSocketMessage {
    type: string;
    data?: any;
    timestamp: string;
    bot_id?: string;
}

interface UseBotPositionsWebSocketOptions {
    botId: string;
    onPositionsUpdate?: (positions: Position[]) => void;
    enabled?: boolean;
}

export function useBotPositionsWebSocket({
    botId,
    onPositionsUpdate,
    enabled = true,
}: UseBotPositionsWebSocketOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (!enabled || !botId) return;

        try {
            const token = localStorage.getItem('access_token');
            const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/trading'; // Using /trading endpoint for auth

            if (typeof WebSocket === 'undefined') return;

            const ws = new WebSocket(`${wsUrl}?token=${token}`);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                setError(null);
                console.log('[BotPositionsWS] Connected');

                // 1. Subscribe to positions channel
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    channels: [`positions:${botId}`, `orders:${botId}`]
                }));

                // 2. Trigger the User Data Stream on the backend
                ws.send(JSON.stringify({
                    type: 'start_bot_stream',
                    bot_id: botId
                }));
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    // console.log('[TRACE] WS Message:', message); // Optional debug

                    // Handle standard StreamMessage format from backend
                    if (message.stream_type === 'POSITIONS' || message.type === 'position_update') {
                        // message.data contains list of positions
                        const positions = message.data as Position[];
                        onPositionsUpdate?.(positions);
                    }

                    if (message.type === 'stream_started') {
                        console.log('[BotPositionsWS] Backend User Stream started');
                    }

                } catch (e) {
                    console.error('[BotPositionsWS] Failed to parse message:', e);
                }
            };

            ws.onerror = () => {
                console.warn('[BotPositionsWS] Connection failed');
                setError('WebSocket connection error');
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                if (event.code !== 1000) {
                    if (enabled) {
                        reconnectTimeoutRef.current = setTimeout(() => {
                            connect();
                        }, 5000); // Retry faster than stats
                    }
                }
            };
        } catch (e) {
            console.warn('[BotPositionsWS] Failed to connect:', e);
            setError(`Failed to connect`);
        }
    }, [botId, enabled, onPositionsUpdate]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close(1000, 'Component unmounted');
            wsRef.current = null;
        }
    }, []);

    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return { isConnected, error };
}
