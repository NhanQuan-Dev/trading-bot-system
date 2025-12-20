import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, Download, TrendingUp, TrendingDown, Calendar, DollarSign, Activity, Percent, BarChart2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Area,
  ComposedChart,
  ReferenceDot,
  Legend
} from 'recharts';
import { useToast } from '@/hooks/use-toast';

// Interfaces matching Backend DTOs
interface BacktestResult {
  id: string;
  strategy_id: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_equity: number | null;
  total_return: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  total_trades: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  profit_factor: number | null;
  status: string;
  created_at: string;
  error_message?: string;
}

interface Trade {
  trade_id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entry_time: string;
  entry_price: number;
  exit_time: string;
  exit_price: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
  status: string;
}

interface EquityPoint {
  timestamp: string;
  equity: number;
  drawdown_percent?: number;
}

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export default function BacktestDetail() {
  const { backtestId } = useParams(); // Fix: match route param name
  const id = backtestId; // Keep existing variable name for rest of code
  const navigate = useNavigate();
  const { toast } = useToast();

  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);

  // Strategy Name Mapping - synced with backend seed_strategies.py
  const strategyMap: Record<string, string> = {
    '00000000-0000-0000-0000-000000000001': 'Grid Trading',
    '00000000-0000-0000-0000-000000000002': 'Momentum Strategy',
    '00000000-0000-0000-0000-000000000003': 'Mean Reversion',
    '00000000-0000-0000-0000-000000000004': 'Arbitrage',
    '00000000-0000-0000-0000-000000000005': 'Scalping',
  };

  useEffect(() => {
    if (!id) return;

    const fetchDetails = async () => {
      try {
        setLoading(true);
        // 1. Fetch Backtest Details
        const btRes = await fetch(`/api/v1/backtests/${id}`);
        if (!btRes.ok) throw new Error('Failed to fetch backtest details');
        const btData: BacktestResult = await btRes.json();
        setBacktest(btData);
        setLoading(false); // Force loading to complete immediately after main fetch

        // 2. Fetch Trades (non-blocking)
        try {
          const tradesRes = await fetch(`/api/v1/backtests/${id}/trades`);
          if (tradesRes.ok) {
            const tradesData = await tradesRes.json();
            // Map backend response to frontend Trade interface
            const mappedTrades = (tradesData.trades || []).map((t: any) => ({
              trade_id: t.id,
              symbol: t.symbol,
              side: t.side === 'LONG' ? 'BUY' : 'SELL',  // Map direction to side
              entry_time: t.entry_time,
              entry_price: t.entry_price,
              exit_time: t.exit_time,
              exit_price: t.exit_price,
              quantity: t.quantity,
              pnl: t.pnl || 0,
              pnl_percent: t.pnl_pct || 0,
              status: t.pnl > 0 ? 'WIN' : t.pnl < 0 ? 'LOSS' : 'BREAK_EVEN',
            }));
            setTrades(mappedTrades);
          }
        } catch (err) {
          console.warn('Failed to fetch trades:', err);
        }

        // 3. Fetch Equity Curve (non-blocking)
        try {
          const equityRes = await fetch(`/api/v1/backtests/${id}/equity-curve`);
          if (equityRes.ok) {
            const equityData = await equityRes.json();
            setEquityCurve(equityData.map((e: any) => ({
              timestamp: new Date(e.timestamp).toISOString(),
              equity: e.equity,
              drawdown_percent: e.drawdown_percent || 0
            })));
          }
        } catch (err) {
          console.warn('Failed to fetch equity curve:', err);
        }

        // 4. Fetch Market Data for Chart (non-blocking)
        if (btData.symbol && btData.start_date && btData.end_date) {
          try {
            // Backend expects: interval (not timeframe), start_time/end_time (not start_date/end_date)
            const marketRes = await fetch(`/api/v1/market-data/candles/${btData.symbol.replace('/', '-')}?interval=${btData.timeframe}&start_time=${btData.start_date}&end_time=${btData.end_date}`);
            if (marketRes.ok) {
              const marketData = await marketRes.json();
              const mappedCandles = marketData.map((c: any) => ({
                time: new Date(c.open_time).toISOString(),
                open: c.open_price,
                high: c.high_price,
                low: c.low_price,
                close: c.close_price,
                volume: c.volume
              }));
              setCandles(mappedCandles);
            }
          } catch (err) {
            console.warn('Failed to fetch market data:', err);
          }
        }

      } catch (error) {
        console.error(error);
        toast({ title: 'Error loading backtest details', variant: 'destructive' });
      } finally {
        setLoading(false);
      }
    };


    fetchDetails();
  }, [id]); // Remove toast from dependencies!

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex h-[80vh] items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"></div>
            <p className="mt-4 text-muted-foreground">Loading backtest results...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (!backtest) {
    return (
      <DashboardLayout>
        <div className="flex bg-card p-6 rounded-lg border border-border flex-col items-center justify-center h-64">
          <p className="text-destructive mb-4">Backtest not found</p>
          <Button onClick={() => navigate('/backtest')}>Go Back</Button>
        </div>
      </DashboardLayout>
    );
  }

  // Derived Metrics
  const netProfit = backtest.final_equity ? backtest.final_equity - backtest.initial_capital : 0;
  const netProfitPercent = backtest.total_return ? backtest.total_return * 100 : 0;
  const isProfit = netProfit >= 0;

  // Chart Data Preparation
  // Combine candles with trade markers if possible, or just overlay scatter on candle/line chart
  // For simplicity, we'll use a Line chart for price and reference dots for trades
  const priceChartData = candles.map(c => {
    // Find trades executed at this time (approximate)
    const tradeEntry = trades.find(t => new Date(t.entry_time).getTime() === new Date(c.time).getTime());
    const tradeExit = trades.find(t => new Date(t.exit_time).getTime() === new Date(c.time).getTime());

    return {
      ...c,
      dateShort: new Date(c.time).toLocaleDateString(),
      buy: tradeEntry && tradeEntry.side === 'BUY' ? tradeEntry.entry_price : null,
      sell: tradeEntry && tradeEntry.side === 'SELL' ? tradeEntry.entry_price : null,
      exit: tradeExit ? tradeExit.exit_price : null,
      exitPnL: tradeExit ? tradeExit.pnl : 0
    };
  });

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/backtest')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold">{strategyMap[backtest.strategy_id] || 'Strategy'}</h1>
                <Badge variant={backtest.status === 'completed' ? 'default' : 'secondary'}>
                  {backtest.status.toUpperCase()}
                </Badge>
              </div>
              <p className="text-muted-foreground mt-1 flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1"><DollarSign className="h-3 w-3" /> {backtest.symbol}</span>
                <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {backtest.timeframe}</span>
                <span className="flex items-center gap-1"><Activity className="h-3 w-3" /> {new Date(backtest.start_date).toLocaleDateString()} - {new Date(backtest.end_date).toLocaleDateString()}</span>
              </p>
            </div>
          </div>
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            Export Results
          </Button>
        </div>

        {/* Key Metrics */}
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Net Profit</CardTitle>
              {isProfit ? <TrendingUp className="h-4 w-4 text-primary" /> : <TrendingDown className="h-4 w-4 text-destructive" />}
            </CardHeader>
            <CardContent>
              <div className={cn("text-2xl font-bold", isProfit ? "text-primary" : "text-destructive")}>
                {isProfit ? '+' : ''}{netProfit.toFixed(2)} USD
              </div>
              <p className="text-xs text-muted-foreground">{isProfit ? '+' : ''}{netProfitPercent.toFixed(2)}% Return</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
              <TargetIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(backtest.win_rate != null ? parseFloat(String(backtest.win_rate)) : 0).toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">{backtest.total_trades} Total Trades</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Profit Factor</CardTitle>
              <BarChart2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{backtest.profit_factor?.toFixed(2) || '0.00'}</div>
              <p className="text-xs text-muted-foreground">Sharpe: {backtest.sharpe_ratio?.toFixed(2) || '0.00'}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
              <TrendingDown className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">{backtest.max_drawdown?.toFixed(2)}%</div>
              <p className="text-xs text-muted-foreground">Peak to Trough</p>
            </CardContent>
          </Card>
        </div>

        {/* Charts & Details Tabs */}
        <Tabs defaultValue="equity" className="space-y-4">
          <TabsList>
            <TabsTrigger value="equity">Equity Curve</TabsTrigger>
            <TabsTrigger value="price">Price Action</TabsTrigger>
            <TabsTrigger value="trades">Trade History</TabsTrigger>
            <TabsTrigger value="positions">Position Log</TabsTrigger>
          </TabsList>

          <TabsContent value="equity" className="space-y-4">
            <Card className="p-6">
              <CardHeader className="px-0 pt-0">
                <CardTitle>Equity Growth & Drawdown</CardTitle>
              </CardHeader>
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={equityCurve}>
                    <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(val) => new Date(val).toLocaleDateString()}
                      minTickGap={50}
                    />
                    <YAxis yAxisId="left" domain={['auto', 'auto']} />
                    <YAxis yAxisId="right" orientation="right" domain={[-100, 0]} hide /> {/* Optional DD axis */}
                    <Tooltip
                      labelFormatter={(val) => new Date(val).toLocaleString()}
                      formatter={(val: number) => [`$${val.toFixed(2)}`, 'Equity']}
                    />
                    <Area type="monotone" dataKey="equity" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.1} yAxisId="left" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="price" className="space-y-4">
            <Card className="p-6">
              <CardHeader className="px-0 pt-0">
                <CardTitle>Price Action & Trade Entries</CardTitle>
              </CardHeader>
              <div className="h-[400px] w-full">
                {priceChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={priceChartData}>
                      <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                      <XAxis
                        dataKey="time"
                        tickFormatter={(val) => new Date(val).toLocaleDateString()}
                        minTickGap={50}
                      />
                      <YAxis domain={['auto', 'auto']} />
                      <Tooltip
                        labelFormatter={(val) => new Date(val).toLocaleString()}
                      />
                      <Line type="monotone" dataKey="close" stroke="hsl(var(--foreground))" dot={false} strokeWidth={1} name="Price" />
                      {/* Simple markers for now. Advanced chart needs more complex setup */}
                      <Line type="monotone" dataKey="buy" stroke="none" isAnimationActive={false} dot={{ r: 4, fill: '#22c55e', strokeWidth: 0 }} name="Buy" />
                      <Line type="monotone" dataKey="sell" stroke="none" isAnimationActive={false} dot={{ r: 4, fill: '#ef4444', strokeWidth: 0 }} name="Sell" />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground">
                    No market data available for chart
                  </div>
                )}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="trades">
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-right">PnL</TableHead>
                    <TableHead className="text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trades.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                        No trades recorded
                      </TableCell>
                    </TableRow>
                  ) : trades.map((trade) => {
                    const isWin = trade.pnl > 0;
                    return (
                      <TableRow key={trade.trade_id}>
                        <TableCell className="font-mono text-sm">{new Date(trade.entry_time).toLocaleString()}</TableCell>
                        <TableCell>
                          <Badge variant={trade.side === 'BUY' ? 'default' : 'destructive'} className="text-xs">
                            {trade.side}
                          </Badge>
                        </TableCell>
                        <TableCell>{trade.symbol}</TableCell>
                        <TableCell className="text-right font-mono">${trade.entry_price.toFixed(2)}</TableCell>
                        <TableCell className="text-right">{trade.quantity}</TableCell>
                        <TableCell className={cn("text-right font-mono", isWin ? "text-primary" : "text-destructive")}>
                          {trade.pnl !== 0 ? `${isWin ? '+' : ''}${trade.pnl.toFixed(2)}` : '-'}
                          <span className="text-xs ml-1 opacity-70">
                            ({trade.pnl_percent.toFixed(2)}%)
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className="capitalize text-xs text-muted-foreground">{trade.status.toLowerCase()}</span>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          </TabsContent>

          <TabsContent value="positions">
            <Card>
              <CardHeader>
                <CardTitle>Position Log</CardTitle>
                <CardDescription>Detailed entry and exit information for each position</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Direction</TableHead>
                      <TableHead>Entry Time</TableHead>
                      <TableHead>Entry Price</TableHead>
                      <TableHead>Exit Time</TableHead>
                      <TableHead>Exit Price</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead className="text-right">P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trades.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
                          No positions recorded. Run a backtest to see position data.
                        </TableCell>
                      </TableRow>
                    ) : trades.map((trade, idx) => {
                      const entryDate = new Date(trade.entry_time);
                      const exitDate = trade.exit_time ? new Date(trade.exit_time) : null;
                      const durationMs = exitDate ? exitDate.getTime() - entryDate.getTime() : 0;
                      const durationHours = Math.floor(durationMs / (1000 * 60 * 60));
                      const durationMins = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
                      const isWin = trade.pnl > 0;

                      return (
                        <TableRow key={trade.trade_id}>
                          <TableCell className="font-mono text-muted-foreground">{idx + 1}</TableCell>
                          <TableCell>
                            <Badge variant={trade.side === 'BUY' ? 'default' : 'destructive'}>
                              {trade.side === 'BUY' ? 'LONG' : 'SHORT'}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            <div>{entryDate.toLocaleDateString()}</div>
                            <div className="text-muted-foreground">{entryDate.toLocaleTimeString()}</div>
                          </TableCell>
                          <TableCell className="font-mono">${trade.entry_price.toFixed(2)}</TableCell>
                          <TableCell className="font-mono text-xs">
                            {exitDate ? (
                              <>
                                <div>{exitDate.toLocaleDateString()}</div>
                                <div className="text-muted-foreground">{exitDate.toLocaleTimeString()}</div>
                              </>
                            ) : (
                              <span className="text-muted-foreground">Open</span>
                            )}
                          </TableCell>
                          <TableCell className="font-mono">
                            {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {durationHours > 0 ? `${durationHours}h ` : ''}{durationMins}m
                          </TableCell>
                          <TableCell className={cn("text-right font-mono font-medium", isWin ? "text-primary" : "text-destructive")}>
                            {trade.pnl !== 0 ? `${isWin ? '+' : ''}$${trade.pnl.toFixed(2)}` : '-'}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}

function TargetIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}
