import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Download, TrendingDown, Calendar, DollarSign, Activity, BarChart2, Hash, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

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
  entry_reason?: Record<string, any>;
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

  // Period stats from API
  const [periodStats, setPeriodStats] = useState({
    day: { avgProfit: 0, maxProfit: 0, minProfit: 0, avgTrades: 0, maxTrades: 0, minTrades: 0 },
    week: { avgProfit: 0, maxProfit: 0, minProfit: 0, avgTrades: 0, maxTrades: 0, minTrades: 0 },
    month: { avgProfit: 0, maxProfit: 0, minProfit: 0, avgTrades: 0, maxTrades: 0, minTrades: 0 },
    year: { avgProfit: 0, maxProfit: 0, minProfit: 0, avgTrades: 0, maxTrades: 0, minTrades: 0 },
  });

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
              status: t.pnl > 0 ? 'WIN' : t.pnl < 0 ? 'LOSS' : 'BREAK_EVEN',
              entry_reason: t.entry_reason,
              exit_reason: t.exit_reason,
            })));
          }
        } catch (e) { console.error("Trades fetch error", e); }

        // 3. Period Stats from API
        try {
          const psRes = await fetch(`/api/v1/backtests/${id}/period-stats`, { headers });
          if (psRes.ok) {
            const psData = await psRes.json();
            setPeriodStats({
              day: {
                avgProfit: psData.profit_day?.avg_profit || 0,
                maxProfit: psData.profit_day?.max_profit || 0,
                minProfit: psData.profit_day?.min_profit || 0,
                avgTrades: psData.trades_day?.avg_trades || 0,
                maxTrades: psData.trades_day?.max_trades || 0,
                minTrades: psData.trades_day?.min_trades || 0,
              },
              week: {
                avgProfit: psData.profit_week?.avg_profit || 0,
                maxProfit: psData.profit_week?.max_profit || 0,
                minProfit: psData.profit_week?.min_profit || 0,
                avgTrades: psData.trades_week?.avg_trades || 0,
                maxTrades: psData.trades_week?.max_trades || 0,
                minTrades: psData.trades_week?.min_trades || 0,
              },
              month: {
                avgProfit: psData.profit_month?.avg_profit || 0,
                maxProfit: psData.profit_month?.max_profit || 0,
                minProfit: psData.profit_month?.min_profit || 0,
                avgTrades: psData.trades_month?.avg_trades || 0,
                maxTrades: psData.trades_month?.max_trades || 0,
                minTrades: psData.trades_month?.min_trades || 0,
              },
              year: {
                avgProfit: psData.profit_year?.avg_profit || 0,
                maxProfit: psData.profit_year?.max_profit || 0,
                minProfit: psData.profit_year?.min_profit || 0,
                avgTrades: psData.trades_year?.avg_trades || 0,
                maxTrades: psData.trades_year?.max_trades || 0,
                minTrades: psData.trades_year?.min_trades || 0,
              },
            });
          }
        } catch (e) { console.error("Period stats fetch error", e); }

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

        {/* Metrics Grid - 6 cards, Net Profit and Total Trades are collapsible */}
        <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-6 items-start">
          {/* Net Profit - Collapsible */}
          <Collapsible className="col-span-1">
            <Card>
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Net Profit</CardTitle>
                  <div className="flex items-center gap-1">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    <ChevronDown className="h-3 w-3 text-muted-foreground" />
                  </div>
                </CardHeader>
              </CollapsibleTrigger>
              <CardContent>
                <div className={cn("text-2xl font-bold", Number(backtest.total_return || 0) >= 0 ? "text-green-500" : "text-red-500")}>
                  {Number(backtest.total_return || 0) >= 0 ? '+' : ''}${Number(backtest.final_equity ? Number(backtest.final_equity) - Number(backtest.initial_capital) : 0).toFixed(2)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {Number(backtest.total_return || 0) >= 0 ? '+' : ''}{Number(backtest.total_return || 0).toFixed(2)}% Return
                </p>
              </CardContent>
              <CollapsibleContent>
                <CardContent className="pt-3 border-t">
                  <p className="text-xs font-medium text-foreground mb-2">Profit per Period</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between"><span className="text-muted-foreground">Day</span><span className={cn(periodStats.day.avgProfit >= 0 ? "text-green-500" : "text-red-500")}>${periodStats.day.avgProfit.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Week</span><span className={cn(periodStats.week.avgProfit >= 0 ? "text-green-500" : "text-red-500")}>${periodStats.week.avgProfit.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Month</span><span className={cn(periodStats.month.avgProfit >= 0 ? "text-green-500" : "text-red-500")}>${periodStats.month.avgProfit.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Year</span><span className={cn(periodStats.year.avgProfit >= 0 ? "text-green-500" : "text-red-500")}>${periodStats.year.avgProfit.toFixed(2)}</span></div>
                  </div>
                  <p className="text-xs font-medium text-foreground mb-2 mt-3">Max/Min per Period</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between"><span className="text-muted-foreground">Day</span><span><span className="text-green-500">${periodStats.day.maxProfit.toFixed(0)}</span> / <span className="text-red-500">${periodStats.day.minProfit.toFixed(0)}</span></span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Week</span><span><span className="text-green-500">${periodStats.week.maxProfit.toFixed(0)}</span> / <span className="text-red-500">${periodStats.week.minProfit.toFixed(0)}</span></span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Month</span><span><span className="text-green-500">${periodStats.month.maxProfit.toFixed(0)}</span> / <span className="text-red-500">${periodStats.month.minProfit.toFixed(0)}</span></span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Year</span><span><span className="text-green-500">${periodStats.year.maxProfit.toFixed(0)}</span> / <span className="text-red-500">${periodStats.year.minProfit.toFixed(0)}</span></span></div>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>

          {/* Win Rate - Static */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Number(backtest.win_rate || 0).toFixed(1)}%</div>

              <p className="text-xs text-muted-foreground">
                {backtest.total_trades} Total Trades
              </p>
            </CardContent>
          </Card>

          {/* Profit Factor - Static */}
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

          {/* Max Drawdown - Static */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-500">{Number(backtest.max_drawdown || 0).toFixed(2)}%</div>
              <p className="text-xs text-muted-foreground">
                Peak to Trough
              </p>
            </CardContent>
          </Card>

          {/* Streaks - Static */}
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

          {/* Total Trades - Collapsible */}
          <Collapsible className="col-span-1">
            <Card>
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
                  <div className="flex items-center gap-1">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    <ChevronDown className="h-3 w-3 text-muted-foreground" />
                  </div>
                </CardHeader>
              </CollapsibleTrigger>
              <CardContent>
                <div className="text-2xl font-bold">{backtest.total_trades || 0}</div>
                <p className="text-xs text-muted-foreground">Executed trades</p>
              </CardContent>
              <CollapsibleContent>
                <CardContent className="pt-3 border-t">
                  <p className="text-xs font-medium text-foreground mb-2">Avg Trades per Period</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between"><span className="text-muted-foreground">Day</span><span>{periodStats.day.avgTrades.toFixed(1)}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Week</span><span>{periodStats.week.avgTrades.toFixed(1)}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Month</span><span>{periodStats.month.avgTrades.toFixed(1)}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Year</span><span>{periodStats.year.avgTrades.toFixed(1)}</span></div>
                  </div>
                  <p className="text-xs font-medium text-foreground mb-2 mt-3">Max/Min per Period</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between"><span className="text-muted-foreground">Day</span><span>{periodStats.day.maxTrades} / {periodStats.day.minTrades}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Week</span><span>{periodStats.week.maxTrades} / {periodStats.week.minTrades}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Month</span><span>{periodStats.month.maxTrades} / {periodStats.month.minTrades}</span></div>
                    <div className="flex justify-between"><span className="text-muted-foreground">Year</span><span>{periodStats.year.maxTrades} / {periodStats.year.minTrades}</span></div>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
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
