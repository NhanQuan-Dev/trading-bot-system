import { useEffect, useRef, useCallback, useState } from 'react';

export interface BotStats {
    bot_id: string;
    total_pnl: string;  // Decimal as string from API
    win_rate: number;   // Already 0-100, don't multiply
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    current_win_streak: number;
    current_loss_streak: number;
    max_win_streak: number;
    max_loss_streak: number;
}

interface WebSocketMessage {
    stream_type: string;
    data: BotStats;
    timestamp: string;
    user_id?: string;
}

interface UseBotStatsWebSocketOptions {
    botId: string;
    onStatsUpdate?: (stats: BotStats) => void;
    enabled?: boolean;
}

/**
 * Hook for subscribing to real-time bot stats updates via WebSocket.
 * 
 * Usage:
 * ```tsx
 * const { stats, isConnected, error } = useBotStatsWebSocket({
 *   botId: bot.id,
 *   onStatsUpdate: (newStats) => console.log('Stats updated:', newStats),
 * });
 * ```
 */
export function useBotStatsWebSocket({
    botId,
    onStatsUpdate,
    enabled = true,
}: UseBotStatsWebSocketOptions) {
    const [stats, setStats] = useState<BotStats | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (!enabled || !botId) return;

        try {
            // Get auth token from localStorage or context
            const token = localStorage.getItem('access_token');
            // Backend WS endpoint is at /ws (not /api/v1/ws)
            const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

            // Check if WebSocket is supported
            if (typeof WebSocket === 'undefined') {
                console.warn('[BotStatsWS] WebSocket not supported');
                return;
            }

            const ws = new WebSocket(`${wsUrl}?token=${token}`);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                setError(null);

                // Subscribe to bot_stats stream
                ws.send(JSON.stringify({
                    type: 'subscribe',
                    stream_type: 'BOT_STATS',
                    bot_id: botId,
                }));
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);

                    if (message.stream_type === 'BOT_STATS' && message.data?.bot_id === botId) {
                        setStats(message.data);
                        onStatsUpdate?.(message.data);
                    }
                } catch (e) {
                    console.error('[BotStatsWS] Failed to parse message:', e);
                }
            };

            ws.onerror = () => {
                // Don't log full error object as it's uninformative for WebSocket
                console.warn('[BotStatsWS] Connection failed - WebSocket may not be available');
                setError('WebSocket connection error');
            };

            ws.onclose = (event) => {
                setIsConnected(false);

                // Only log and reconnect if it wasn't a normal close
                if (event.code !== 1000) {
                    // Reconnect after 10 seconds if not intentionally closed
                    if (enabled) {
                        reconnectTimeoutRef.current = setTimeout(() => {
                            connect();
                        }, 10000);
                    }
                }
            };
        } catch (e) {
            // Graceful failure - don't crash the page
            console.warn('[BotStatsWS] Failed to connect:', e);
            setError(`Failed to connect`);
        }
    }, [botId, enabled, onStatsUpdate]);

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

    return {
        stats,
        isConnected,
        error,
        reconnect: connect,
    };
}

/**
 * Helper function to safely parse bot stats numbers.
 * Handles string -> number conversion for Decimal values from API.
 */
export function parseBotStats(stats: BotStats | null) {
    if (!stats) {
        return {
            totalPnl: 0,
            winRate: 0,
            totalTrades: 0,
            winningTrades: 0,
            losingTrades: 0,
            currentWinStreak: 0,
            currentLossStreak: 0,
            maxWinStreak: 0,
            maxLossStreak: 0,
        };
    }

    return {
        totalPnl: parseFloat(String(stats.total_pnl)) || 0,
        winRate: stats.win_rate ?? 0,  // Already 0-100, DON'T multiply by 100
        totalTrades: stats.total_trades ?? 0,
        winningTrades: stats.winning_trades ?? 0,
        losingTrades: stats.losing_trades ?? 0,
        currentWinStreak: stats.current_win_streak ?? 0,
        currentLossStreak: stats.current_loss_streak ?? 0,
        maxWinStreak: stats.max_win_streak ?? 0,
        maxLossStreak: stats.max_loss_streak ?? 0,
    };
}
