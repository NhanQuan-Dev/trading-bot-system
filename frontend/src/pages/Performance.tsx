import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Area, AreaChart
} from 'recharts';
import { TrendingUp, TrendingDown, Target, Percent, Activity, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';

// API Response Interfaces
interface PerformanceOverview {
  total_return_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
}

interface MonthlyPerformance {
  month: string;
  return_pct: number;
  trades_count: number;
  win_rate: number;
}

interface DailyReturn {
  date: string;
  return_pct: number;
  cumulative_return_pct: number;
}

interface BotPerformance {
  bot_id: string; // Backend might send int but safely handle as string/number
  bot_name: string;
  total_pnl: number;
  win_rate: number;
  sharpe_ratio: number;
  trades_count: number;
}

export default function Performance() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<PerformanceOverview | null>(null);
  const [monthlyData, setMonthlyData] = useState<MonthlyPerformance[]>([]);
  const [dailyReturns, setDailyReturns] = useState<DailyReturn[]>([]);
  const [botPerformance, setBotPerformance] = useState<BotPerformance[]>([]);
  const [tradeDistribution, setTradeDistribution] = useState<{ name: string, value: number, color: string }[]>([]);
  const [drawdownData, setDrawdownData] = useState<{ date: string, drawdown: number }[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch all required data in parallel
        const [overviewRes, monthlyRes, dailyRes, botRes] = await Promise.all([
          fetch('/api/performance/overview'),
          fetch('/api/performance/returns/monthly?months=12'),
          fetch('/api/performance/returns/daily?days=90'),
          fetch('/api/performance/metrics/by-bot')
        ]);

        if (overviewRes.ok) {
          const data = await overviewRes.json();
          setOverview(data);
        }

        let totalTrades = 0;
        if (monthlyRes.ok) {
          const data: MonthlyPerformance[] = await monthlyRes.json();
          setMonthlyData(data);
          totalTrades = data.reduce((sum, item) => sum + item.trades_count, 0);
        }

        if (dailyRes.ok) {
          const data: DailyReturn[] = await dailyRes.json();
          setDailyReturns(data);

          // Calculate drawdown curve
          let peak = -Infinity;
          const drawdowns = data.map(d => {
            // Assuming cumulative_return_pct starts around 0
            // Equity approximation: 100 * (1 + ret/100)
            const equity = 100 * (1 + d.cumulative_return_pct / 100);
            if (equity > peak) peak = equity;
            const dd = peak === 0 ? 0 : ((equity - peak) / peak) * 100;
            return {
              date: d.date,
              drawdown: dd
            };
          });
          setDrawdownData(drawdowns);
        }

        if (botRes.ok) {
          const data = await botRes.json();
          setBotPerformance(data);
        }

        // Calculate trade distribution if we have total trades and win rate
        // If overview is available, use its win rate. Otherwise derive from monthly if possible.
        // We need 'await' for json() so overview might be set effectively in next render, 
        // but here we are in same closure. We used separate awaits above but didn't assign to vars early enough?
        // Actually Promise.all returns responses, we parse them sequentially.
        // Let's rely on the parsed data locally.

      } catch (error) {
        console.error("Failed to fetch performance data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Effect to update derived state like distribution once data is loaded
  useEffect(() => {
    if (overview && monthlyData.length > 0) {
      const totalTrades = monthlyData.reduce((sum, m) => sum + m.trades_count, 0);
      const winRate = overview.win_rate / 100;
      const wins = Math.round(totalTrades * winRate);
      const losses = totalTrades - wins;

      setTradeDistribution([
        { name: 'Win', value: wins, color: 'hsl(142, 76%, 46%)' },
        { name: 'Loss', value: losses, color: 'hsl(0, 72%, 55%)' },
      ]);
    }
  }, [overview, monthlyData]);

  // Derived metrics for UI
  const metrics = [
    {
      label: 'Total Return',
      value: overview ? `${overview.total_return_pct >= 0 ? '+' : ''}${overview.total_return_pct.toFixed(2)}%` : '0.00%',
      icon: DollarSign,
      positive: (overview?.total_return_pct || 0) >= 0
    },
    {
      label: 'Win Rate',
      value: overview ? `${overview.win_rate.toFixed(1)}%` : '0.0%',
      icon: Target,
      positive: (overview?.win_rate || 0) >= 50
    },
    {
      label: 'Sharpe Ratio',
      value: overview ? overview.sharpe_ratio.toFixed(2) : '0.00',
      icon: Activity,
      positive: (overview?.sharpe_ratio || 0) >= 1
    },
    {
      label: 'Max Drawdown',
      value: overview ? `${overview.max_drawdown.toFixed(1)}%` : '0.0%',
      icon: TrendingDown,
      positive: false
    },
    {
      label: 'Profit Factor',
      value: overview ? overview.profit_factor.toFixed(2) : '0.00',
      icon: Percent,
      positive: (overview?.profit_factor || 0) >= 1.5
    },
    {
      label: 'Total Trades',
      value: monthlyData.reduce((acc, m) => acc + m.trades_count, 0).toString(),
      icon: TrendingUp,
      positive: true
    },
  ];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center p-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading performance metrics...</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Performance Analytics</h1>
          <p className="text-muted-foreground">Comprehensive analysis of your trading performance</p>
        </div>

        {/* Key Metrics */}
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          {metrics.map((metric) => (
            <Card key={metric.label} className="border-border bg-card">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <metric.icon className={cn(
                    "h-4 w-4",
                    metric.positive ? "text-primary" : "text-destructive"
                  )} />
                  <span className="text-xs text-muted-foreground">{metric.label}</span>
                </div>
                <p className={cn(
                  "mt-1 text-xl font-bold",
                  metric.positive ? "text-primary" : "text-destructive"
                )}>
                  {metric.value}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Charts */}
        <Tabs defaultValue="monthly" className="space-y-4">
          <TabsList className="bg-muted">
            <TabsTrigger value="monthly">Monthly Returns</TabsTrigger>
            <TabsTrigger value="distribution">Trade Distribution</TabsTrigger>
            <TabsTrigger value="drawdown">Drawdown</TabsTrigger>
          </TabsList>

          <TabsContent value="monthly">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>Monthly Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthlyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 20%)" />
                      <XAxis dataKey="month" stroke="hsl(215, 15%, 60%)" />
                      <YAxis stroke="hsl(215, 15%, 60%)" tickFormatter={(v) => `${v}%`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(220, 18%, 12%)',
                          border: '1px solid hsl(220, 15%, 20%)',
                          borderRadius: '8px',
                          color: 'hsl(210, 20%, 98%)'
                        }}
                        formatter={(value: number) => [`${value}%`, 'Return']}
                      />
                      <Bar
                        dataKey="return_pct"
                        fill="hsl(142, 76%, 46%)"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="distribution">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>Win/Loss Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                {tradeDistribution.length > 0 ? (
                  <div className="flex items-center justify-center">
                    <div className="h-[350px] w-[350px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={tradeDistribution}
                            cx="50%"
                            cy="50%"
                            innerRadius={80}
                            outerRadius={140}
                            paddingAngle={2}
                            dataKey="value"
                          >
                            {tradeDistribution.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              backgroundColor: 'hsl(220, 18%, 12%)',
                              border: '1px solid hsl(220, 15%, 20%)',
                              borderRadius: '8px',
                              color: 'hsl(210, 20%, 98%)'
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="space-y-4">
                      {tradeDistribution.map((item) => (
                        <div key={item.name} className="flex items-center gap-3">
                          <div
                            className="h-4 w-4 rounded"
                            style={{ backgroundColor: item.color }}
                          />
                          <div>
                            <p className="font-medium text-foreground">{item.name}</p>
                            <p className="text-sm text-muted-foreground">{item.value} trades</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex h-[350px] items-center justify-center text-muted-foreground">
                    No trade data available
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="drawdown">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>Underwater Drawdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={drawdownData}>
                      <defs>
                        <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(0, 72%, 55%)" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="hsl(0, 72%, 55%)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 20%)" />
                      <XAxis dataKey="date" stroke="hsl(215, 15%, 60%)" />
                      <YAxis stroke="hsl(215, 15%, 60%)" tickFormatter={(v) => `${v.toFixed(1)}%`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(220, 18%, 12%)',
                          border: '1px solid hsl(220, 15%, 20%)',
                          borderRadius: '8px',
                          color: 'hsl(210, 20%, 98%)'
                        }}
                        formatter={(value: number) => [`${value.toFixed(2)}%`, 'Drawdown']}
                      />
                      <Area
                        type="monotone"
                        dataKey="drawdown"
                        stroke="hsl(0, 72%, 55%)"
                        fillOpacity={1}
                        fill="url(#colorDrawdown)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
