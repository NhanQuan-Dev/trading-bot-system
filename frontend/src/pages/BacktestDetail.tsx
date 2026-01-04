import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Download, TrendingDown, Calendar, DollarSign, Activity, BarChart2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';

import { PositionLogTable } from '@/components/backtest/PositionLogTable';
import { apiClient } from '@/lib/api/client';

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
  strategy_name?: string;
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

export default function BacktestDetail() {
  const { backtestId } = useParams();
  const id = backtestId;
  const navigate = useNavigate();
  const { toast } = useToast();

  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [strategyName, setStrategyName] = useState<string>('Loading...');
  const [trades, setTrades] = useState<Trade[]>([]);

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('position-log');

  const stats = useMemo(() => {
    let currentWinStreak = 0;
    let maxWinStreak = 0;
    let currentLossStreak = 0;
    let maxLossStreak = 0;

    // Sort just in case
    const sorted = [...trades].sort((a, b) => new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime());

    for (const t of sorted) {
      if (t.pnl > 0) {
        currentWinStreak++;
        currentLossStreak = 0;
        if (currentWinStreak > maxWinStreak) maxWinStreak = currentWinStreak;
      } else if (t.pnl < 0) {
        currentLossStreak++;
        currentWinStreak = 0;
        if (currentLossStreak > maxLossStreak) maxLossStreak = currentLossStreak;
      } else {
        // Break even resets both
        currentWinStreak = 0;
        currentLossStreak = 0;
      }
    }
    return { maxWinStreak, maxLossStreak };
  }, [trades]);

  useEffect(() => {
    if (!id) return;

    const fetchDetails = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('access_token');
        const headers: HeadersInit = token ? { 'Authorization': `Bearer ${token}` } : {};

        // 1. Backtest Details
        const btRes = await fetch(`/api/v1/backtests/${id}`, { headers });
        if (!btRes.ok) throw new Error('Failed to fetch details');
        const btData: BacktestResult = await btRes.json();
        setBacktest(btData);

        // Strategy Name
        if (btData.strategy_name) {
          setStrategyName(btData.strategy_name);
        } else {
          // Try fetching if not provided (e.g. legacy data)
          try {
            const sRes = await fetch(`/api/v1/strategies/${btData.strategy_id}`, { headers });
            if (sRes.ok) {
              const sData = await sRes.json();
              setStrategyName(sData.name);
            } else {
              console.warn("Strategy name fetch failed", sRes.status);
              setStrategyName('Strategy Not Found');
            }
          } catch (e) {
            console.warn("Strategy fetch error", e);
            setStrategyName('Strategy Not Found');
          }
        }

        setLoading(false);

        // 2. Trades
        try {
          const tRes = await fetch(`/api/v1/backtests/${id}/trades?page=1&limit=10000`, { headers });
          if (tRes.ok) {
            const tData = await tRes.json();
            const rawTrades = tData.trades || [];
            setTrades(rawTrades.map((t: any) => ({
              trade_id: t.id,
              symbol: t.symbol,
              side: (t.side?.toUpperCase() === 'LONG' ? 'BUY' : 'SELL') as 'BUY' | 'SELL',
              entry_time: t.entry_time,
              entry_price: t.entry_price,
              exit_time: t.exit_time,
              exit_price: t.exit_price,
              quantity: t.quantity,
              pnl: t.pnl || 0,
              pnl_percent: t.pnl_pct || 0,
              status: t.pnl > 0 ? 'WIN' : t.pnl < 0 ? 'LOSS' : 'BREAK_EVEN'
            })));
          }
        } catch (e) { console.error("Trades fetch error", e); }

      } catch (error) {
        console.error(error);
        toast({ title: 'Error loading data', variant: 'destructive' });
        setLoading(false);
      }
    };
    fetchDetails();
  }, [id]);


  if (loading && !backtest) {
    return (
      <DashboardLayout>
        <div className="flex h-[50vh] items-center justify-center">Loading...</div>
      </DashboardLayout>
    );
  }

  if (!backtest) return <DashboardLayout><div>Not Found</div></DashboardLayout>;

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
              <h2 className="text-2xl font-bold tracking-tight">{strategyName}</h2>
              <div className="flex items-center text-sm text-muted-foreground">
                <Badge variant="outline" className="mr-2">{backtest.symbol}</Badge>
                <Badge variant="outline" className="mr-2">{backtest.timeframe}</Badge>
                <Calendar className="mr-1 h-3 w-3" />
                {new Date(backtest.start_date).toLocaleDateString()} - {new Date(backtest.end_date).toLocaleDateString()}
                <Badge
                  className={cn("ml-2",
                    backtest.status === 'COMPLETED' ? "bg-green-500/10 text-green-500 border-green-500/20" :
                      backtest.status === 'FAILED' ? "bg-red-500/10 text-red-500 border-red-500/20" : ""
                  )}
                  variant="outline"
                >
                  {backtest.status}
                </Badge>
              </div>
            </div>
          </div>
          <Button variant="outline"><Download className="mr-2 h-4 w-4" /> Export</Button>
        </div>

        {/* Metrics Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Net Profit</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={cn("text-2xl font-bold", Number(backtest.total_return || 0) >= 0 ? "text-green-500" : "text-red-500")}>
                {Number(backtest.total_return || 0) >= 0 ? '+' : ''}${Number(backtest.final_equity ? Number(backtest.final_equity) - Number(backtest.initial_capital) : 0).toFixed(2)} USD
              </div>
              <p className="text-xs text-muted-foreground">
                {Number(backtest.total_return || 0) >= 0 ? '+' : ''}{Number(backtest.total_return || 0).toFixed(2)}% Return
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(Number(backtest.win_rate || 0) * 100).toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">
                {backtest.total_trades} Total Trades
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Profit Factor</CardTitle>
              <BarChart2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Number(backtest.profit_factor || 0).toFixed(2)}</div>
              <p className="text-xs text-muted-foreground">
                Sharpe: {Number(backtest.sharpe_ratio || 0).toFixed(2)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-500">{(Number(backtest.max_drawdown || 0) * 100).toFixed(2)}%</div>
              <p className="text-xs text-muted-foreground">
                Peak to Trough
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Streaks</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground rotate-180" />
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-baseline">
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground">Best</span>
                  <span className="text-xl font-bold text-green-500">{stats.maxWinStreak}</span>
                </div>
                <div className="flex flex-col text-right">
                  <span className="text-xs text-muted-foreground">Worst</span>
                  <span className="text-xl font-bold text-red-500">{stats.maxLossStreak}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>


        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="position-log">Position Log</TabsTrigger>
          </TabsList>

          <TabsContent value="position-log" forceMount className={cn("space-y-4", activeTab !== 'position-log' && 'hidden')}>
            <PositionLogTable trades={trades} />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
