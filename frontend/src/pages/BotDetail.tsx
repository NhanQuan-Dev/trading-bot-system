import { useEffect, useState, useCallback, useRef } from 'react';
import { apiClient } from '@/lib/api/client';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAppStore } from '@/lib/store';
import { ArrowLeft, Play, Pause, Settings, TrendingUp, TrendingDown, Wifi, WifiOff, CircleDollarSign, Coins, Loader2, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useBotStatsWebSocket, parseBotStats, BotStats } from '@/hooks/use-bot-stats-websocket';
import { useBotPositionsWebSocket } from '@/hooks/use-bot-positions-websocket';
import { useMarketData } from '@/hooks/use-market-data';
import { useCandleData } from '@/hooks/use-candle-data';
import { PriceExplosion } from '@/components/effects/PriceExplosion';
import { FlashPrice } from '@/components/FlashPrice';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Plot from 'react-plotly.js';
import { PeriodStatsRow, PeriodStats } from '@/components/dashboard/PeriodStats';



// Mock candlestick data
const generateCandleData = () => {
  const data = [];
  let price = 43500;
  for (let i = 0; i < 50; i++) {
    const open = price;
    const change = (Math.random() - 0.5) * 500;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * 200;
    const low = Math.min(open, close) - Math.random() * 200;
    const volume = Math.random() * 1000 + 500;
    price = close;
    data.push({
      time: `${String(i).padStart(2, '0')}:00`,
      open,
      high,
      low,
      close,
      volume,
      isUp: close >= open,
    });
  }
  return data;
};

// Using real-time candle data from Binance WebSocket

const candleData = generateCandleData();

// Bot status configuration - matches backend BotStatus enum (all uppercase)
// Statuses: RUNNING, PAUSED, ERROR
const statusConfig: Record<string, { label: string; color: string }> = {
  RUNNING: { label: 'Running', color: 'border-primary/50 text-primary' },
  PAUSED: { label: 'Paused', color: 'border-accent/50 text-accent' },
  ERROR: { label: 'Error', color: 'border-destructive/50 text-destructive' },
};

export default function BotDetail() {
  const { botId } = useParams();
  const navigate = useNavigate();
  const bots = useAppStore((state) => state.bots);
  const getBot = useAppStore((state) => state.getBot);
  const updateBot = useAppStore((state) => state.updateBot);
  const pauseBot = useAppStore((state) => state.pauseBot);
  const startBot = useAppStore((state) => state.startBot);

  const storeBot = bots.find(b => b.id === botId);
  const [bot, setBot] = useState(storeBot);
  const [isLoading, setIsLoading] = useState(!storeBot);
  const [connections, setConnections] = useState<{ id: string; name: string; is_testnet?: boolean }[]>([]);
  const [strategies, setStrategies] = useState<{ id: string; name: string; }[]>([]);
  const [isToggling, setIsToggling] = useState(false);

  // === Open Positions state ===
  const [positions, setPositions] = useState<any[]>([]);
  const [positionsLoading, setPositionsLoading] = useState(true);
  const [positionsTotal, setPositionsTotal] = useState(0);
  const [positionsLimit] = useState(50);
  const [positionsOffset, setPositionsOffset] = useState(0);

  // === Open Orders state ===
  const [orders, setOrders] = useState<any[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(true);
  const [ordersTotal, setOrdersTotal] = useState(0);
  const [ordersLimit] = useState(50);
  const [ordersOffset, setOrdersOffset] = useState(0);
  const [ordersStatusFilter] = useState<string | null>(null);

  // === Trade History state ===
  const [trades, setTrades] = useState<any[]>([]);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [tradesTotal, setTradesTotal] = useState(0);
  const [tradesLimit] = useState(50);
  const [tradesOffset, setTradesOffset] = useState(0);

  // === Active tab tracking ===
  const [activeTab, setActiveTab] = useState('positions');

  // === Period Stats for sub-metrics display ===
  const [periodStats, setPeriodStats] = useState<PeriodStats | null>(null);
  const [periodStatsLoading, setPeriodStatsLoading] = useState(true);

  // Load period stats from backend API (reusable callback for real-time updates)
  const loadPeriodStats = useCallback(async () => {
    if (!botId) return;

    try {
      setPeriodStatsLoading(true);
      const response = await apiClient.get(`/api/v1/bots/${botId}/stats/periods`);
      setPeriodStats(response.data);
    } catch (error) {
      console.error('Failed to load period stats:', error);
      // Fall back to empty stats
      setPeriodStats({
        today: { pnl: 0, trades: 0, wins: 0, losses: 0 },
        yesterday: { pnl: 0, trades: 0, wins: 0, losses: 0 },
        this_week: { pnl: 0, trades: 0, wins: 0, losses: 0 },
        last_week: { pnl: 0, trades: 0, wins: 0, losses: 0 },
        this_month: { pnl: 0, trades: 0, wins: 0, losses: 0 },
        last_month: { pnl: 0, trades: 0, wins: 0, losses: 0 },
      });
    } finally {
      setPeriodStatsLoading(false);
    }
  }, [botId]);

  // Load period stats on mount
  useEffect(() => {
    loadPeriodStats();
  }, [loadPeriodStats]);


  // === NEW: Price Explosion Effect State ===
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [explosions, setExplosions] = useState<{ id: number; y: number }[]>([]);
  const lastPriceRef = useRef<number | null>(null);



  // === NEW: Real-time Positions via WebSocket ===
  const handlePositionsUpdate = useCallback((newPositions: any[]) => {
    setPositions(newPositions);
    setPositionsTotal(newPositions.length);
    setPositionsLoading(false);
  }, []);

  const { isConnected: positionsConnected } = useBotPositionsWebSocket({
    botId: botId || '',
    onPositionsUpdate: handlePositionsUpdate,
    enabled: !!botId,
  });

  // === Close Position Logic ===
  const [closingPosition, setClosingPosition] = useState<string | null>(null);
  const [closingAll, setClosingAll] = useState(false);

  // Calculate Totals
  const totalUnrealizedPnl = positions.reduce((sum, p) => sum + (parseFloat(String(p.unrealized_pnl || 0)) || 0), 0);
  const totalMargin = positions.reduce((sum, p) => {
    // Priority: position_initial_margin > isolated_wallet > calculation
    const margin = parseFloat(String(p.position_initial_margin || p.isolated_wallet || 0));
    if (margin > 0) return sum + margin;
    // Fallback calculation
    return sum + ((parseFloat(String(p.entry_price || 0)) * parseFloat(String(p.quantity || 0))) / (parseFloat(String(p.leverage || 1)) || 1));
  }, 0);
  const totalRoi = totalMargin > 0 ? (totalUnrealizedPnl / totalMargin) * 100 : 0;

  const handleClosePosition = async (symbol: string, side: string) => {
    if (!bot) return;
    if (!window.confirm(`Are you sure you want to close ${side} position for ${symbol}?`)) return;

    const key = `${symbol}-${side}`;
    setClosingPosition(key);
    try {
      await apiClient.post(`/api/v1/bots/${bot.id}/positions/close`, {
        symbol,
        side
      });
      // WebSocket will update the list
    } catch (error) {
      console.error('Failed to close position:', error);
      alert('Failed to close position');
    } finally {
      setClosingPosition(null);
    }
  };

  const handleCloseAllPositions = async () => {
    if (!bot) return;
    if (!window.confirm('Are you sure you want to CLOSE ALL positions? This action cannot be undone.')) return;

    setClosingAll(true);
    try {
      await apiClient.post(`/api/v1/bots/${bot.id}/positions/close-all`);
    } catch (error) {
      console.error('Failed to close all positions:', error);
      alert('Failed to close all positions');
    } finally {
      setClosingAll(false);
    }
  };

  // === Real-time market data (Order Book & Trades) ===
  const tradingSymbol = bot?.symbol || bot?.configuration?.symbol || 'BTCUSDT';

  // Get is_testnet from bot's Exchange Connection
  const botConnection = connections.find(c => c.id === bot?.exchange_connection_id);
  const isTestnet = botConnection?.is_testnet ?? true; // Default testnet for safety

  const { orderBook, recentTrades, isConnected: marketConnected } = useMarketData({
    symbol: tradingSymbol,
    enabled: !!tradingSymbol,
    orderBookLevels: 10,
    maxTrades: 21,
    isTestnet: isTestnet,
  });

  // === Real-time candlestick data ===
  const { candles, minPrice: candleMinPrice, maxPrice: candleMaxPrice, isConnected: candleConnected } = useCandleData({
    symbol: tradingSymbol,
    interval: '1m',
    maxCandles: 21,
    enabled: !!tradingSymbol,
    isTestnet: isTestnet,
  });

  // Calculate explicit Y-axis range to sync coordinate mapping
  // Add 10% padding top/bottom
  const yPadding = (candleMaxPrice - candleMinPrice) * 0.1 || (candleMaxPrice * 0.01);
  const yAxisMin = candleMinPrice - yPadding;
  const yAxisMax = candleMaxPrice + yPadding;

  const handleExplosionComplete = useCallback((id: number) => {
    setExplosions(prev => prev.filter(e => e.id !== id));
  }, []);

  // Track price changes for explosion effect
  useEffect(() => {
    if (candles.length === 0) return;
    const currentPrice = candles[candles.length - 1].close;

    if (lastPriceRef.current !== null && currentPrice > lastPriceRef.current) {
      // Price increased! Trigger explosion
      if (chartContainerRef.current) {
        const containerHeight = chartContainerRef.current.clientHeight;
        const range = yAxisMax - yAxisMin;
        const normalizedPrice = (currentPrice - yAxisMin) / range;
        const yPixel = containerHeight - (normalizedPrice * containerHeight); // Invert for CSS (top=0)

        // Add new explosion to the list
        const newExplosion = { id: Date.now(), y: yPixel };
        setExplosions(prev => [...prev, newExplosion]);
      }
    }
    lastPriceRef.current = currentPrice;
  }, [candles, yAxisMin, yAxisMax]); // Dependency on candles ensures we check every update



  useEffect(() => {
    if (storeBot) {
      setBot(storeBot);
      setIsLoading(false);
    } else if (botId) {
      setIsLoading(true);
      getBot(botId)
        .then((fetchedBot) => {
          setBot(fetchedBot);
        })
        .catch(() => {
          // Keep bot null
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [botId, storeBot, getBot]);

  // Load connections and strategies
  useEffect(() => {
    const loadData = async () => {
      try {
        const [connRes, stratRes] = await Promise.all([
          apiClient.get('/api/connections'),
          apiClient.get('/api/v1/strategies')
        ]);
        setConnections(connRes.data || []);
        setStrategies(Array.isArray(stratRes.data) ? stratRes.data : stratRes.data?.strategies || []);
      } catch (error) {
        console.error('Failed to load lookup data:', error);
      }
    };
    loadData();
  }, []);

  // Load positions data (Initial REST fetch)
  const loadPositions = useCallback(async (showLoading = true) => {
    if (!botId) return;

    try {
      if (showLoading) setPositionsLoading(true);
      const response = await apiClient.get(`/api/v1/bots/${botId}/positions`, {
        params: { limit: positionsLimit, offset: positionsOffset }
      });

      if (!response.data || !Array.isArray(response.data.positions)) {
        setPositions([]);
        setPositionsTotal(0);
        return;
      }

      setPositions(response.data.positions);
      setPositionsTotal(response.data.total || 0);
    } catch (error) {
      console.error('Failed to load positions:', error);
    } finally {
      if (showLoading) setPositionsLoading(false);
    }
  }, [botId, positionsLimit, positionsOffset]);

  // Initial load
  useEffect(() => {
    loadPositions(true);
  }, [loadPositions]);

  // Load orders data
  const loadOrders = useCallback(async () => {
    if (!botId) return;

    try {
      setOrdersLoading(true);
      const params: any = { limit: ordersLimit, offset: ordersOffset };
      if (ordersStatusFilter) {
        params.status_filter = ordersStatusFilter;
      }

      const response = await apiClient.get(`/api/v1/bots/${botId}/orders`, { params });

      // ✅ Validate response structure (Pattern 2)
      if (!response.data || !Array.isArray(response.data.orders)) {
        console.error('Invalid orders response:', response.data);
        setOrders([]);
        setOrdersTotal(0);
        return;
      }

      setOrders(response.data.orders);
      setOrdersTotal(response.data.total || 0);
    } catch (error) {
      console.error('Failed to load orders:', error);
      setOrders([]);
      setOrdersTotal(0);
    } finally {
      setOrdersLoading(false);
    }
  }, [botId, ordersLimit, ordersOffset, ordersStatusFilter]);

  // Load trades data
  const loadTrades = useCallback(async () => {
    if (!botId) return;

    try {
      setTradesLoading(true);
      const response = await apiClient.get(`/api/v1/bots/${botId}/trades`, {
        params: { limit: tradesLimit, offset: tradesOffset }
      });

      // ✅ Validate response structure (Pattern 2)
      if (!response.data || !Array.isArray(response.data.trades)) {
        console.error('Invalid trades response:', response.data);
        setTrades([]);
        setTradesTotal(0);
        return;
      }

      setTrades(response.data.trades);
      setTradesTotal(response.data.total || 0);
    } catch (error) {
      console.error('Failed to load trades:', error);
      setTrades([]);
      setTradesTotal(0);
    } finally {
      setTradesLoading(false);
    }
  }, [botId, tradesLimit, tradesOffset]);

  // === NEW: Real-time bot stats via WebSocket ===
  const [liveStats, setLiveStats] = useState<BotStats | null>(null);

  const handleStatsUpdate = useCallback((stats: BotStats) => {
    setLiveStats(stats);
    // Reload all data when a trade closes (stats update received)
    loadPositions(false); // Don't show loading spinner for smooth update
    loadOrders();
    loadTrades();
    loadPeriodStats(); // === REAL-TIME: Refresh period sub-metrics ===
  }, [loadPositions, loadOrders, loadTrades, loadPeriodStats]);

  const { stats: wsStats, isConnected } = useBotStatsWebSocket({
    botId: botId || '',
    onStatsUpdate: handleStatsUpdate,
    enabled: !!botId,
  });

  // Use live stats if available, otherwise fall back to bot data from API
  const displayStats = liveStats || wsStats
    ? parseBotStats(liveStats || wsStats)
    : {
      // Fallback to bot data from API when WebSocket not available
      totalPnl: parseFloat(String(bot?.total_profit_loss || bot?.total_pnl || 0)) || 0,
      winRate: parseFloat(String(bot?.win_rate || 0)) || 0,
      totalTrades: bot?.total_trades || 0,
      winningTrades: bot?.winning_trades || 0,
      losingTrades: bot?.losing_trades || 0,
      currentWinStreak: bot?.current_win_streak || 0,
      currentLossStreak: bot?.current_loss_streak || 0,
      maxWinStreak: bot?.max_win_streak || 0,
      maxLossStreak: bot?.max_loss_streak || 0,
    };

  // Load initial data when tab changes
  const handleTabChange = (value: string) => {
    setActiveTab(value);
    if (value === 'positions' && positions.length === 0) {
      loadPositions();
    } else if (value === 'orders' && orders.length === 0) {
      loadOrders();
    } else if (value === 'history' && trades.length === 0) {
      loadTrades();
    }
  };

  // Load positions, orders, and trades on mount or when botId changes
  useEffect(() => {
    if (botId) {
      if (activeTab === 'positions') loadPositions();
      // Always load initial orders and trades to get counts
      loadOrders();
      loadTrades();
    }
  }, [botId, activeTab, loadPositions, loadOrders, loadTrades]);

  // Reload when pagination changes
  useEffect(() => {
    if (activeTab === 'positions') loadPositions();
  }, [positionsOffset, loadPositions, activeTab]);

  useEffect(() => {
    if (activeTab === 'orders') loadOrders();
  }, [ordersOffset, loadOrders, activeTab]);

  useEffect(() => {
    if (activeTab === 'history') loadTrades();
  }, [tradesOffset, loadTrades, activeTab]);

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-[calc(100vh-100px)]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (!bot) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-muted-foreground">Bot not found</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/bots')}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Bots
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const config = statusConfig[bot.status] || statusConfig.STOPPED || { label: bot.status, color: 'border-muted/50 text-muted-foreground' };

  const handleToggle = async () => {
    if (isToggling) return; // Prevent double-click
    setIsToggling(true);

    try {
      if (bot.status === 'RUNNING') {
        await pauseBot(bot.id);
      } else {
        await startBot(bot.id);
      }
      // Refetch bot data to ensure state is in sync
      const refreshedBot = await getBot(bot.id);
      setBot(refreshedBot);
    } catch (error: any) {
      console.error('Failed to toggle bot status:', error);
      // Show more specific error to user
      const message = error?.response?.data?.detail || error?.message || 'Unknown error';
      console.error('Error details:', message);
    } finally {
      setIsToggling(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/bots')}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-foreground">{bot.name}</h1>
                <Badge variant="outline" className={config.color}>{config.label}</Badge>
              </div>
              <p className="text-muted-foreground">
                {bot.symbol || bot.configuration?.symbol} • {connections.find(c => c.id === bot.exchange_connection_id)?.name || 'Unknown Exchange'} • {strategies.find(s => s.id === bot.strategy_id)?.name || 'Unknown Strategy'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleToggle} disabled={bot.status === 'ERROR' || isToggling}>
              {isToggling ? (
                <>
                  <svg className="mr-1 h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {bot.status === 'RUNNING' ? 'Pausing...' : 'Starting...'}
                </>
              ) : bot.status === 'RUNNING' ? (
                <><Pause className="mr-1 h-4 w-4" /> Pause</>
              ) : (
                <><Play className="mr-1 h-4 w-4" /> Start</>
              )}
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="mr-1 h-4 w-4" /> Configure
            </Button>
          </div>
        </div>

        {/* Summary Stats - Uses real-time WebSocket data when available */}
        <div className="grid gap-4 md:grid-cols-4">
          {/* Total P&L Card */}
          <Card className="border-border bg-card relative">
            {/* WebSocket connection indicator */}
            <div className="absolute top-2 right-2" title={isConnected ? "Live updates active" : "Connecting..."}>
              {isConnected ? (
                <Wifi className="h-3 w-3 text-primary" />
              ) : (
                <WifiOff className="h-3 w-3 text-muted-foreground" />
              )}
            </div>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Total P&L</p>
              <p className={cn("text-2xl font-bold", displayStats.totalPnl >= 0 ? "text-primary" : "text-destructive")}>
                {displayStats.totalPnl >= 0 ? '+' : ''}${displayStats.totalPnl.toFixed(2)}
              </p>
              {periodStats && <PeriodStatsRow periodStats={periodStats} metric="pnl" />}
            </CardContent>
          </Card>

          {/* Win Rate Card */}
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold text-foreground">{displayStats.winRate.toFixed(1)}%</p>
              {periodStats && <PeriodStatsRow periodStats={periodStats} metric="winRate" />}
            </CardContent>
          </Card>

          {/* Total Trades Card */}
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Total Trades</p>
              <p className="text-2xl font-bold text-foreground">
                {displayStats.totalTrades}
                <span className="text-sm font-normal text-muted-foreground ml-2">
                  ({displayStats.winningTrades}W / {displayStats.losingTrades}L)
                </span>
              </p>
              {periodStats && <PeriodStatsRow periodStats={periodStats} metric="trades" />}
            </CardContent>
          </Card>

          {/* Streak Card */}
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Streak</p>
              <p className="text-2xl font-bold text-foreground">
                {displayStats.currentWinStreak > 0 && (
                  <span className="text-primary">🔥 {displayStats.currentWinStreak}W</span>
                )}
                {displayStats.currentLossStreak > 0 && (
                  <span className="text-destructive">❄️ {displayStats.currentLossStreak}L</span>
                )}
                {displayStats.currentWinStreak === 0 && displayStats.currentLossStreak === 0 && (
                  <span className="text-muted-foreground">-</span>
                )}
              </p>
              <p className="text-xs text-muted-foreground">
                Best: {displayStats.maxWinStreak}W | Worst: {displayStats.maxLossStreak}L
              </p>
              {periodStats && <PeriodStatsRow periodStats={periodStats} metric="streak" />}
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Candlestick Chart - Flex 10 (5 parts) */}
          <Card className="border-none bg-transparent shadow-none w-full lg:flex-[10] lg:w-auto flex flex-col min-w-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Price Chart</CardTitle>
                {candleConnected && (
                  <span className="flex items-center gap-1 text-xs text-primary">
                    <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                    Live
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0 flex-1 relative min-h-[450px]" ref={chartContainerRef}>

              {/* Explosion Effect Overlay */}
              {/* Multiple Price Explosions */}
              {explosions.map(exp => (
                <PriceExplosion
                  key={exp.id}
                  x={0} // x is handled by CSS right positioning
                  y={exp.y}
                  active={true}
                  onComplete={() => handleExplosionComplete(exp.id)}
                />
              ))}

              <div className="absolute inset-0">
                <Plot
                  data={[
                    {
                      x: candles.map(c => c.timeStr),
                      open: candles.map(c => c.open),
                      high: candles.map(c => c.high),
                      low: candles.map(c => c.low),
                      close: candles.map(c => c.close),
                      type: 'candlestick',
                      increasing: {
                        line: { color: '#15FF00', width: 1 },
                        fillcolor: '#15FF00'
                      },
                      decreasing: {
                        line: { color: '#FF1E1E', width: 1 },
                        fillcolor: '#FF1E1E'
                      },
                    } as any,
                  ]}
                  layout={{
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    showlegend: false,
                    dragmode: false, // Disable drag interactions
                    xaxis: {
                      visible: false,
                      rangeslider: { visible: false },
                      fixedrange: true, // Disable X zoom
                    },
                    yaxis: {
                      visible: false,
                      fixedrange: true, // Disable Y zoom
                      range: [yAxisMin, yAxisMax], // Explicit range for sync
                    },
                    margin: { t: 0, r: 100, l: 0, b: 0 },
                    autosize: true,
                    annotations: candles.length > 0 ? [
                      {
                        xref: 'paper',
                        yref: 'y',
                        x: 1,
                        y: candles[candles.length - 1].close,
                        xanchor: 'left',
                        text: candles[candles.length - 1].close.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
                        showarrow: false,
                        font: {
                          family: 'monospace',
                          size: 18,
                          color: '#15FF00',
                          weight: 700
                        },
                        yshift: 0
                      }
                    ] : [],
                    shapes: candleMinPrice > 0 ? [
                      {
                        type: 'line',
                        xref: 'paper',
                        yref: 'y',
                        x0: 0,
                        y0: candleMinPrice,
                        x1: 1,
                        y1: candleMinPrice,
                        line: {
                          color: '#FF1E1E',
                          width: 1,
                          dash: 'dash'
                        },
                        opacity: 0.5
                      }
                    ] : []
                  }}
                  useResizeHandler={true}
                  style={{ width: '100%', height: '100%' }}
                  config={{
                    displayModeBar: false,
                    scrollZoom: false,
                    doubleClick: false,
                    showTips: false,
                    editable: false,
                  }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Order Depth with Depth Bars - Flex 3 (1.5 parts) */}
          <Card className="border-border bg-card w-full lg:flex-[3] lg:w-auto min-w-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Order Depth</CardTitle>
                <div className="flex items-center gap-2">
                  {marketConnected && (
                    <span className="flex items-center gap-1 text-xs text-primary">
                      <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                      Live
                    </span>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/30">
                {/* Header */}
                <div className="grid grid-cols-3 px-4 py-2 text-xs text-muted-foreground">
                  <span>Price</span>
                  <span className="text-right">Size</span>
                  <span className="text-right">Total</span>
                </div>

                {/* Asks (sells) - reversed so highest is at top */}
                {orderBook.asks.slice().reverse().map((ask, i) => {
                  const depthPercent = (ask.amount / (orderBook.maxAskAmount || 0.001)) * 100;
                  // Intensity: higher volume = more opaque (0.1 to 0.5)
                  const intensity = 0.1 + (ask.amount / (orderBook.maxAskAmount || 0.001)) * 0.4;
                  // Flash intensity based on change magnitude
                  const hasChange = ask.change && Math.abs(ask.change) > 0.0001;
                  const flashIntensity = hasChange ? Math.min(Math.abs(ask.change) / (orderBook.maxAskAmount || 0.001), 1) : 0;

                  return (
                    <div
                      key={`ask-${ask.price}`}
                      className="relative grid grid-cols-3 px-4 py-1.5 transition-all duration-150"
                      style={{
                        // Flash background on change
                        boxShadow: flashIntensity > 0
                          ? `inset 0 0 0 100px rgba(239, 68, 68, ${flashIntensity * 0.3})`
                          : undefined,
                      }}
                    >
                      {/* Depth bar background with intensity */}
                      <div
                        className="absolute inset-y-0 right-0 transition-all duration-300 ease-out"
                        style={{
                          width: `${depthPercent}%`,
                          backgroundColor: `rgba(239, 68, 68, ${intensity})`,
                        }}
                      />
                      {/* Content */}
                      <span className="relative font-mono text-xs text-destructive">{ask.price.toLocaleString()}</span>
                      <span className="relative text-right font-mono text-xs">{ask.amount.toFixed(4)}</span>
                      <span className="relative text-right font-mono text-xs text-muted-foreground">{ask.total.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    </div>
                  );
                })}

                {/* Spread indicator */}
                <div className="px-4 py-2 text-center bg-muted/30">
                  <span className="font-mono text-sm font-bold text-foreground">
                    {orderBook.lastPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  {orderBook.asks[0] && orderBook.bids[0] && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      Spread: {(orderBook.asks[0].price - orderBook.bids[0].price).toFixed(2)}
                    </span>
                  )}
                </div>

                {/* Bids (buys) */}
                {orderBook.bids.map((bid, i) => {
                  const depthPercent = (bid.amount / (orderBook.maxBidAmount || 0.001)) * 100;
                  // Intensity: higher volume = more opaque (0.1 to 0.5)
                  const intensity = 0.1 + (bid.amount / (orderBook.maxBidAmount || 0.001)) * 0.4;
                  // Flash intensity based on change magnitude
                  const hasChange = bid.change && Math.abs(bid.change) > 0.0001;
                  const flashIntensity = hasChange ? Math.min(Math.abs(bid.change) / (orderBook.maxBidAmount || 0.001), 1) : 0;

                  return (
                    <div
                      key={`bid-${bid.price}`}
                      className="relative grid grid-cols-3 px-4 py-1.5 transition-all duration-150"
                      style={{
                        // Flash background on change
                        boxShadow: flashIntensity > 0
                          ? `inset 0 0 0 100px rgba(34, 197, 94, ${flashIntensity * 0.3})`
                          : undefined,
                      }}
                    >
                      {/* Depth bar background with intensity */}
                      <div
                        className="absolute inset-y-0 right-0 transition-all duration-300 ease-out"
                        style={{
                          width: `${depthPercent}%`,
                          backgroundColor: `rgba(34, 197, 94, ${intensity})`,
                        }}
                      />
                      {/* Content */}
                      <span className="relative font-mono text-xs text-primary">{bid.price.toLocaleString()}</span>
                      <span className="relative text-right font-mono text-xs">{bid.amount.toFixed(4)}</span>
                      <span className="relative text-right font-mono text-xs text-muted-foreground">{bid.total.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Recent Trades with Flash Animation - Flex 3 (1.5 parts) */}
          <Card className="border-border bg-card w-full lg:flex-[3] lg:w-auto min-w-0">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Recent Trades</CardTitle>
                {marketConnected && (
                  <span className="flex items-center gap-1 text-xs text-primary">
                    <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                    Live
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/30">
                {/* Header */}
                <div className="grid grid-cols-3 px-4 py-2 text-xs text-muted-foreground">
                  <span>Time</span>
                  <span className="text-right">Price</span>
                  <span className="text-right">Size</span>
                </div>

                {recentTrades.length === 0 ? (
                  <div className="px-4 py-6 text-center text-xs text-muted-foreground">
                    Waiting for trades...
                  </div>
                ) : (
                  recentTrades.map((trade, i) => (
                    <div
                      key={trade.id}
                      className={cn(
                        "grid grid-cols-3 px-4 py-1.5 transition-all duration-500",
                        i === 0 && "animate-flash-trade"
                      )}
                      style={{
                        backgroundColor: i === 0
                          ? (trade.side === 'buy' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)')
                          : undefined
                      }}
                    >
                      <span className="font-mono text-xs text-muted-foreground">{trade.time}</span>
                      <span className={cn(
                        "text-right font-mono text-xs font-medium",
                        trade.side === 'buy' ? "text-primary" : "text-destructive"
                      )}>
                        {trade.price.toLocaleString()}
                      </span>
                      <span className="text-right font-mono text-xs">{trade.amount.toFixed(4)}</span>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tables Section */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="positions">Open Positions ({positionsTotal})</TabsTrigger>
            <TabsTrigger value="orders">Open Orders ({ordersTotal})</TabsTrigger>
            <TabsTrigger value="history">Trade History ({tradesTotal})</TabsTrigger>
          </TabsList>



          <TabsContent value="positions" className="mt-4">

            {/* Total PnL Summary */}


            <Card className="border-border bg-card">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead className="w-[100px]">Symbol</TableHead>
                      <TableHead className="w-[80px]">Side</TableHead>
                      <TableHead className="text-right w-[100px]">Size</TableHead>
                      <TableHead className="text-right w-[110px]">Entry Price</TableHead>
                      <TableHead className="text-right w-[110px]">Mark Price</TableHead>
                      <TableHead className="text-right w-[110px]">Break-even</TableHead>
                      <TableHead className="text-right w-[110px]">Liq. Price</TableHead>
                      <TableHead className="text-right w-[140px]">P&L</TableHead>
                      <TableHead className="text-right w-[140px]">Margin</TableHead>
                      <TableHead className="text-right w-[80px]">Leverage</TableHead>
                      <TableHead className="text-right w-[80px]">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positionsLoading ? (
                      <TableRow>
                        <TableCell colSpan={11} className="text-center py-8">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
                        </TableCell>
                      </TableRow>
                    ) : positions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={11} className="text-center text-muted-foreground py-8">
                          No open positions
                        </TableCell>
                      </TableRow>
                    ) : (
                      <>
                        {positions.map((pos) => {
                          // Parse values from WebSocket/REST (support both field names)
                          const quantity = parseFloat(String(pos.quantity || 0));
                          const entryPrice = parseFloat(String(pos.entry_price || 0));
                          // WebSocket sends mark_price, REST sends current_price
                          const currentPrice = parseFloat(String(pos.mark_price || pos.current_price || 0));
                          const unrealizedPnl = parseFloat(String(pos.unrealized_pnl || 0));
                          const unrealizedPnlPct = parseFloat(String(pos.unrealized_pnl_pct || 0));

                          // NEW: Parse new fields
                          const breakEvenPrice = parseFloat(String(pos.break_even_price || 0));
                          const liquidationPrice = parseFloat(String(pos.liquidation_price || 0));
                          const positionInitialMargin = parseFloat(String(pos.position_initial_margin || pos.isolated_wallet || 0));
                          const maintMargin = parseFloat(String(pos.maint_margin || 0));
                          const marginAsset = pos.margin_asset || 'USDT';

                          return (
                            <TableRow key={pos.id} className="border-border">
                              <TableCell className="font-medium">{pos.symbol}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className={pos.side === 'LONG' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                                  {pos.side}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-right font-mono tabular-nums">{quantity.toFixed(4)}</TableCell>
                              <TableCell className="text-right font-mono tabular-nums">${entryPrice.toLocaleString()}</TableCell>
                              <TableCell className="text-right font-mono tabular-nums">
                                <FlashPrice
                                  value={currentPrice}
                                  prefix="$"
                                  formatter={(v) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                />
                              </TableCell>
                              {/* NEW: Break-even Price */}
                              <TableCell className="text-right font-mono tabular-nums">
                                {breakEvenPrice > 0 ? `$${breakEvenPrice.toLocaleString()}` : '-'}
                              </TableCell>
                              {/* NEW: Liquidation Price */}
                              <TableCell className="text-right font-mono tabular-nums text-destructive/80">
                                {liquidationPrice > 0 ? `$${liquidationPrice.toLocaleString()}` : '-'}
                              </TableCell>
                              {/* P&L */}
                              <TableCell className={cn("text-right font-mono tabular-nums", unrealizedPnl >= 0 ? "text-primary" : "text-destructive")}>
                                <div className="flex items-center justify-end gap-1">
                                  {unrealizedPnl >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                  ${Math.abs(unrealizedPnl).toFixed(2)} ({unrealizedPnlPct.toFixed(2)}%)
                                </div>
                              </TableCell>
                              {/* NEW: Margin (positionInitialMargin with maintMargin) */}
                              <TableCell className="text-right font-mono tabular-nums">
                                <div className="flex flex-col items-end">
                                  <span>{positionInitialMargin.toFixed(2)} {marginAsset}</span>
                                  {maintMargin > 0 && (
                                    <span className="text-xs text-muted-foreground">(Min: {maintMargin.toFixed(2)})</span>
                                  )}
                                </div>
                              </TableCell>
                              {/* Leverage */}
                              <TableCell className="text-right font-mono tabular-nums">
                                <div className="flex flex-col items-end">
                                  <span>{pos.leverage || 1}x</span>
                                  <span className="text-xs text-muted-foreground capitalize">{pos.margin_type || 'Cross'}</span>
                                </div>
                              </TableCell>
                              <TableCell className="text-right">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-muted-foreground hover:text-green-500"
                                  onClick={() => handleClosePosition(pos.symbol, pos.side)}
                                  disabled={closingPosition === `${pos.symbol}-${pos.side}` || closingAll}
                                >
                                  {closingPosition === `${pos.symbol}-${pos.side}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <CircleDollarSign className="h-5 w-5" />}
                                </Button>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                        <TableRow className="hover:bg-transparent border-t-[1px] border-border bg-muted/10 font-bold">
                          <TableCell colSpan={7} className="text-right py-4">Total Unrealized PnL</TableCell>
                          <TableCell className={cn("text-right font-mono tabular-nums py-4", totalUnrealizedPnl >= 0 ? "text-green-500" : "text-red-500")}>
                            ${totalUnrealizedPnl.toFixed(2)} ({totalRoi.toFixed(2)}%)
                          </TableCell>
                          <TableCell colSpan={2} className="py-4"></TableCell>
                          <TableCell className="text-right py-4">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 w-8 p-0 border-green-500/50 text-green-500 hover:bg-green-500/10 hover:text-green-600"
                              onClick={handleCloseAllPositions}
                              disabled={closingAll}
                              title="Close All Positions (Take Profit)"
                            >
                              {closingAll ? <Loader2 className="h-4 w-4 animate-spin" /> : <Coins className="h-4 w-4" />}
                            </Button>
                          </TableCell>
                        </TableRow>
                      </>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
              {/* Pagination for Positions */}
              {!positionsLoading && positions.length > 0 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-border">
                  <div className="text-sm text-muted-foreground">
                    Showing {positionsOffset + 1}-{Math.min(positionsOffset + positionsLimit, positionsTotal)} of {positionsTotal}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={positionsOffset === 0}
                      onClick={() => setPositionsOffset(Math.max(0, positionsOffset - positionsLimit))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={positionsOffset + positionsLimit >= positionsTotal}
                      onClick={() => setPositionsOffset(positionsOffset + positionsLimit)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="orders" className="mt-4">
            <Card className="border-border bg-card">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead>Symbol</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Filled</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ordersLoading ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
                        </TableCell>
                      </TableRow>
                    ) : orders.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                          No open orders
                        </TableCell>
                      </TableRow>
                    ) : (
                      orders.map((order) => {
                        // ✅ SAFE: Parse Decimal strings (Pattern 15)
                        const quantity = parseFloat(String(order.quantity || 0));
                        const price = order.price != null ? parseFloat(String(order.price)) : null;
                        const filledQty = parseFloat(String(order.filled_quantity || 0));

                        return (
                          <TableRow key={order.id} className="border-border">
                            <TableCell className="font-medium">{order.symbol}</TableCell>
                            <TableCell className="capitalize">{order.type}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className={order.side === 'BUY' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                                {order.side}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {price != null ? `$${price.toLocaleString()}` : 'Market'}
                            </TableCell>
                            <TableCell className="text-right font-mono">{quantity.toFixed(4)}</TableCell>
                            <TableCell className="text-right font-mono">{filledQty.toFixed(4)}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="border-accent/50 text-accent">{order.status}</Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {new Date(order.created_at).toLocaleString()}
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </CardContent>
              {/* Pagination for Orders */}
              {!ordersLoading && orders.length > 0 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-border">
                  <div className="text-sm text-muted-foreground">
                    Showing {ordersOffset + 1}-{Math.min(ordersOffset + ordersLimit, ordersTotal)} of {ordersTotal}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={ordersOffset === 0}
                      onClick={() => setOrdersOffset(Math.max(0, ordersOffset - ordersLimit))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={ordersOffset + ordersLimit >= ordersTotal}
                      onClick={() => setOrdersOffset(ordersOffset + ordersLimit)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="history" className="mt-4">
            <Card className="border-border bg-card">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Fee</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Realized P&L</TableHead>
                      <TableHead>Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tradesLoading ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
                        </TableCell>
                      </TableRow>
                    ) : trades.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                          No trade history
                        </TableCell>
                      </TableRow>
                    ) : (
                      trades.map((trade) => {
                        // ✅ SAFE: Parse Decimal strings (Pattern 15)
                        const quantity = parseFloat(String(trade.quantity || 0));
                        const price = parseFloat(String(trade.price || 0));
                        const fee = parseFloat(String(trade.fee || 0));
                        const total = (price * quantity) + fee;
                        const realizedPnl = parseFloat(String(trade.realized_pnl || 0));

                        return (
                          <TableRow key={trade.id} className="border-border">
                            <TableCell className="font-medium">{trade.symbol}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className={trade.side === 'BUY' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                                {trade.side}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono">${price.toLocaleString()}</TableCell>
                            <TableCell className="text-right font-mono">{quantity.toFixed(4)}</TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">${fee.toFixed(2)}</TableCell>
                            <TableCell className="text-right font-mono">${total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                            <TableCell className={cn("text-right font-mono tabular-nums", realizedPnl >= 0 ? "text-primary" : "text-destructive")}>
                              <div className="flex items-center justify-end gap-1">
                                {realizedPnl >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                ${Math.abs(realizedPnl).toFixed(2)}
                              </div>
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {new Date(trade.created_at).toLocaleString()}
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </CardContent>
              {/* Pagination for Trade History */}
              {!tradesLoading && trades.length > 0 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-border">
                  <div className="text-sm text-muted-foreground">
                    Showing {tradesOffset + 1}-{Math.min(tradesOffset + tradesLimit, tradesTotal)} of {tradesTotal}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={tradesOffset === 0}
                      onClick={() => setTradesOffset(Math.max(0, tradesOffset - tradesLimit))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={tradesOffset + tradesLimit >= tradesTotal}
                      onClick={() => setTradesOffset(tradesOffset + tradesLimit)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
