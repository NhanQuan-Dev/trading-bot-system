/**
 * Hook for real-time candlestick data from Binance WebSocket
 * - Maintains rolling window of candles
 * - Updates current candle in real-time
 * - Efficient updates (only changed data)
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

export interface Candle {
    time: number;        // Open time in ms
    timeStr: string;     // Formatted time string
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    isUp: boolean;
    isClosed: boolean;   // Whether candle is closed
}

interface UseCandleDataOptions {
    symbol: string;
    interval?: string;   // 1m, 5m, 15m, 1h, etc.
    maxCandles?: number; // Rolling window size
    enabled?: boolean;
    isTestnet?: boolean; // Auto-select URL based on exchange connection
}

interface UseCandleDataResult {
    candles: Candle[];
    minPrice: number;
    maxPrice: number;
    isConnected: boolean;
    error: string | null;
}

export function useCandleData({
    symbol,
    interval = '1m',
    maxCandles = 21,
    enabled = true,
    isTestnet = true, // Default to testnet for safety
}: UseCandleDataOptions): UseCandleDataResult {
    const [candles, setCandles] = useState<Candle[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);

    // Format symbol for Binance (BTC/USDT -> btcusdt)
    const formatSymbol = useCallback((sym: string) => {
        return sym.replace('/', '').replace('-', '').toLowerCase();
    }, []);

    // Process kline update from WebSocket
    const processKlineUpdate = useCallback((data: any) => {
        const k = data.k;
        if (!k) return;

        const newCandle: Candle = {
            time: k.t,
            timeStr: new Date(k.t).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            }),
            open: parseFloat(k.o),
            high: parseFloat(k.h),
            low: parseFloat(k.l),
            close: parseFloat(k.c),
            volume: parseFloat(k.v),
            isUp: parseFloat(k.c) >= parseFloat(k.o),
            isClosed: k.x, // x = is candle closed
        };

        setCandles(prev => {
            // Find if candle with same open time exists
            const existingIndex = prev.findIndex(c => c.time === newCandle.time);

            if (existingIndex >= 0) {
                // Update existing candle
                const updated = [...prev];
                updated[existingIndex] = newCandle;
                return updated;
            } else {
                // Add new candle and maintain rolling window
                const updated = [...prev, newCandle];
                // Keep only last maxCandles
                if (updated.length > maxCandles) {
                    return updated.slice(-maxCandles);
                }
                return updated;
            }
        });
    }, [maxCandles]);

    // Fetch initial candles via REST API
    const fetchInitialCandles = useCallback(async (binanceSymbol: string) => {
        try {
            // Select API URL based on testnet/mainnet
            const baseUrl = isTestnet
                ? 'https://demo-fapi.binance.com'
                : 'https://fapi.binance.com';
            const url = `${baseUrl}/fapi/v1/klines?symbol=${binanceSymbol.toUpperCase()}&interval=${interval}&limit=${maxCandles}`;
            const response = await fetch(url);
            const data = await response.json();

            if (Array.isArray(data)) {
                const initialCandles: Candle[] = data.map((k: any[]) => ({
                    time: k[0],
                    timeStr: new Date(k[0]).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                    }),
                    open: parseFloat(k[1]),
                    high: parseFloat(k[2]),
                    low: parseFloat(k[3]),
                    close: parseFloat(k[4]),
                    volume: parseFloat(k[5]),
                    isUp: parseFloat(k[4]) >= parseFloat(k[1]),
                    isClosed: true,
                }));

                // Mark last candle as not closed (current)
                if (initialCandles.length > 0) {
                    initialCandles[initialCandles.length - 1].isClosed = false;
                }

                setCandles(initialCandles);
            }
        } catch (e) {
            console.error('[CandleData] Failed to fetch initial candles:', e);
        }
    }, [interval, maxCandles, isTestnet]);

    useEffect(() => {
        if (!enabled || !symbol) {
            return;
        }

        const binanceSymbol = formatSymbol(symbol);

        // First fetch initial candles
        fetchInitialCandles(binanceSymbol);

        // Then connect to WebSocket for real-time updates
        // Futures kline stream: <symbol>@kline_<interval>
        // Select WebSocket URL based on testnet/mainnet
        const wsBase = isTestnet
            ? 'wss://fstream.binancefuture.com'
            : 'wss://fstream.binance.com';
        const wsUrl = `${wsBase}/ws/${binanceSymbol}@kline_${interval}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log(`[CandleData] Connected to ${symbol} ${interval}`);
                setIsConnected(true);
                setError(null);
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    if (message.e === 'kline') {
                        processKlineUpdate(message);
                    }
                } catch (e) {
                    console.error('[CandleData] Parse error:', e);
                }
            };

            ws.onerror = (e) => {
                // Graceful handling - WebSocket connections may fail
                console.warn('[CandleData] WebSocket connection unavailable - candles will not update in real-time');
                setError('Candle data stream unavailable');
                setIsConnected(false);
            };

            ws.onclose = () => {
                // Silent close
                setIsConnected(false);
            };

        } catch (e) {
            console.error('[CandleData] Failed to connect:', e);
            setError('Failed to connect to candle data');
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [symbol, interval, enabled, formatSymbol, fetchInitialCandles, processKlineUpdate]);

    // Calculate min/max prices (memoized)
    const { minPrice, maxPrice } = useMemo(() => {
        if (candles.length === 0) {
            return { minPrice: 0, maxPrice: 0 };
        }
        const lows = candles.map(c => c.low);
        const highs = candles.map(c => c.high);
        return {
            minPrice: Math.min(...lows),
            maxPrice: Math.max(...highs),
        };
    }, [candles]);

    return {
        candles,
        minPrice,
        maxPrice,
        isConnected,
        error,
    };
}
