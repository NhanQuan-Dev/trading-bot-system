/**
 * Hook for real-time market data from Binance WebSocket (public)
 * - Order book depth (asks/bids)
 * - Recent trades (aggTrade stream)
 */
import { useState, useEffect, useRef, useCallback } from 'react';

export interface OrderBookLevel {
    price: number;
    amount: number;
    total: number;
    /** Change delta from previous update (positive = increased, negative = decreased) */
    change?: number;
}

export interface OrderBook {
    bids: OrderBookLevel[];
    asks: OrderBookLevel[];
    lastPrice: number;
    /** Max bid amount for intensity scaling */
    maxBidAmount: number;
    /** Max ask amount for intensity scaling */
    maxAskAmount: number;
}

export interface RecentTrade {
    id: number;
    time: string;
    price: number;
    amount: number;
    side: 'buy' | 'sell';
}

interface UseMarketDataOptions {
    symbol: string;
    enabled?: boolean;
    orderBookLevels?: number;
    maxTrades?: number;
    isTestnet?: boolean; // Auto-select URL based on exchange connection
}

interface UseMarketDataResult {
    orderBook: OrderBook;
    recentTrades: RecentTrade[];
    isConnected: boolean;
    error: string | null;
}

// Default empty order book
const emptyOrderBook: OrderBook = {
    bids: [],
    asks: [],
    lastPrice: 0,
    maxBidAmount: 0,
    maxAskAmount: 0,
};

export function useMarketData({
    symbol,
    enabled = true,
    orderBookLevels = 5,
    maxTrades = 10,
    isTestnet = true, // Default to testnet for safety
}: UseMarketDataOptions): UseMarketDataResult {
    const [orderBook, setOrderBook] = useState<OrderBook>(emptyOrderBook);
    const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const tradeIdRef = useRef(0);

    // Format symbol for Binance (BTCUSDT -> btcusdt)
    const formatSymbol = useCallback((sym: string) => {
        return sym.replace('/', '').replace('-', '').toLowerCase();
    }, []);

    // Process order book depth update
    // Futures format: { a: [[price, qty], ...], b: [[price, qty], ...] }
    // Spot format: { asks: [...], bids: [...] }
    const processDepthUpdate = useCallback((data: any) => {
        // Handle both Futures (a/b) and Spot (asks/bids) formats
        const rawBids = data.b || data.bids || [];
        const rawAsks = data.a || data.asks || [];

        setOrderBook(prev => {
            // Create map of previous prices for change detection
            const prevBidMap = new Map(prev.bids.map(b => [b.price, b.amount]));
            const prevAskMap = new Map(prev.asks.map(a => [a.price, a.amount]));

            const bids: OrderBookLevel[] = rawBids.slice(0, orderBookLevels).map((b: string[]) => {
                const price = parseFloat(b[0]);
                const amount = parseFloat(b[1]);
                const prevAmount = prevBidMap.get(price) || amount;
                const change = amount - prevAmount;
                return {
                    price,
                    amount,
                    total: price * amount,
                    change: Math.abs(change) > 0.0001 ? change : 0, // Threshold for noise
                };
            });

            const asks: OrderBookLevel[] = rawAsks.slice(0, orderBookLevels).map((a: string[]) => {
                const price = parseFloat(a[0]);
                const amount = parseFloat(a[1]);
                const prevAmount = prevAskMap.get(price) || amount;
                const change = amount - prevAmount;
                return {
                    price,
                    amount,
                    total: price * amount,
                    change: Math.abs(change) > 0.0001 ? change : 0,
                };
            });

            // Calculate max amounts for intensity scaling
            const maxBidAmount = Math.max(...bids.map(b => b.amount), 0.001);
            const maxAskAmount = Math.max(...asks.map(a => a.amount), 0.001);

            // Calculate last price as midpoint
            const lastPrice = bids[0] && asks[0]
                ? (bids[0].price + asks[0].price) / 2
                : 0;

            return { bids, asks, lastPrice, maxBidAmount, maxAskAmount };
        });
    }, [orderBookLevels]);

    // Process trade update
    const processTradeUpdate = useCallback((data: any) => {
        const trade: RecentTrade = {
            id: tradeIdRef.current++,
            time: new Date(data.T).toLocaleTimeString(),
            price: parseFloat(data.p),
            amount: parseFloat(data.q),
            side: data.m ? 'sell' : 'buy', // 'm' = true means buyer is market maker (sell)
        };

        setRecentTrades(prev => [trade, ...prev].slice(0, maxTrades));
    }, [maxTrades]);

    useEffect(() => {
        if (!enabled || !symbol) {
            return;
        }

        const binanceSymbol = formatSymbol(symbol);

        // Connect to Binance FUTURES WebSocket for depth and trades
        // Select WebSocket URL based on testnet/mainnet
        // Combined stream: depth@10 + aggTrade
        const wsBase = isTestnet
            ? 'wss://fstream.binancefuture.com'
            : 'wss://fstream.binance.com';
        const wsUrl = `${wsBase}/stream?streams=${binanceSymbol}@depth10@100ms/${binanceSymbol}@aggTrade`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log(`[MarketData] Connected to ${symbol}`);
                setIsConnected(true);
                setError(null);
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    const { stream, data } = message;

                    if (stream.includes('@depth')) {
                        processDepthUpdate(data);
                    } else if (stream.includes('@aggTrade')) {
                        processTradeUpdate(data);
                    }
                } catch (e) {
                    console.error('[MarketData] Parse error:', e);
                }
            };

            ws.onerror = (e) => {
                // Graceful handling - WebSocket connections may fail due to network issues
                // This is expected behavior, not a critical error
                console.warn('[MarketData] WebSocket connection unavailable - market data will not update in real-time');
                setError('Market data stream unavailable');
                setIsConnected(false);
            };

            ws.onclose = () => {
                // Silent close - no need to log every close
                setIsConnected(false);
            };

        } catch (e) {
            console.error('[MarketData] Failed to connect:', e);
            setError('Failed to connect to market data');
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [symbol, enabled, formatSymbol, processDepthUpdate, processTradeUpdate]);

    return {
        orderBook,
        recentTrades,
        isConnected,
        error,
    };
}
