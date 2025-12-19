import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/lib/store';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart
} from 'recharts';
import { TrendingUp, TrendingDown, Target, Percent, Activity, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';

const monthlyData = [
  { month: 'Jan', pnl: 1250 },
  { month: 'Feb', pnl: 890 },
  { month: 'Mar', pnl: -320 },
  { month: 'Apr', pnl: 1560 },
  { month: 'May', pnl: 2100 },
  { month: 'Jun', pnl: 1890 },
];

const tradeDistribution = [
  { name: 'Win', value: 156, color: 'hsl(142, 76%, 46%)' },
  { name: 'Loss', value: 68, color: 'hsl(0, 72%, 55%)' },
];

const drawdownData = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  drawdown: -Math.random() * 8
}));

export default function Performance() {
  const bots = useAppStore((state) => state.bots);
  const trades = useAppStore((state) => state.trades);

  const totalPnL = bots.reduce((sum, bot) => sum + bot.pnl, 0);
  const avgWinRate = bots.reduce((sum, bot) => sum + bot.winRate, 0) / bots.length;
  const totalTrades = bots.reduce((sum, bot) => sum + bot.totalTrades, 0);
  const maxDrawdown = -5.2;
  const sharpeRatio = 1.85;
  const profitFactor = 2.3;

  const metrics = [
    { label: 'Total P&L', value: `$${totalPnL.toFixed(2)}`, icon: DollarSign, positive: totalPnL >= 0 },
    { label: 'Win Rate', value: `${avgWinRate.toFixed(1)}%`, icon: Target, positive: avgWinRate >= 50 },
    { label: 'Sharpe Ratio', value: sharpeRatio.toFixed(2), icon: Activity, positive: sharpeRatio >= 1 },
    { label: 'Max Drawdown', value: `${maxDrawdown.toFixed(1)}%`, icon: TrendingDown, positive: false },
    { label: 'Profit Factor', value: profitFactor.toFixed(2), icon: Percent, positive: profitFactor >= 1.5 },
    { label: 'Total Trades', value: totalTrades.toString(), icon: TrendingUp, positive: true },
  ];

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
            <TabsTrigger value="monthly">Monthly P&L</TabsTrigger>
            <TabsTrigger value="distribution">Trade Distribution</TabsTrigger>
            <TabsTrigger value="drawdown">Drawdown</TabsTrigger>
          </TabsList>

          <TabsContent value="monthly">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>Monthly P&L</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthlyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 20%)" />
                      <XAxis dataKey="month" stroke="hsl(215, 15%, 60%)" />
                      <YAxis stroke="hsl(215, 15%, 60%)" tickFormatter={(v) => `$${v}`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(220, 18%, 12%)',
                          border: '1px solid hsl(220, 15%, 20%)',
                          borderRadius: '8px',
                          color: 'hsl(210, 20%, 98%)'
                        }}
                        formatter={(value: number) => [`$${value}`, 'P&L']}
                      />
                      <Bar
                        dataKey="pnl"
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
                          <stop offset="5%" stopColor="hsl(0, 72%, 55%)" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="hsl(0, 72%, 55%)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 20%)" />
                      <XAxis dataKey="day" stroke="hsl(215, 15%, 60%)" />
                      <YAxis stroke="hsl(215, 15%, 60%)" tickFormatter={(v) => `${v}%`} />
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

        {/* Trade Journal */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle>Recent Trades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {trades.map((trade) => (
                <div
                  key={trade.id}
                  className="flex items-center justify-between rounded-lg border border-border bg-background/50 p-4"
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg",
                      trade.side === 'buy' ? "bg-primary/10" : "bg-destructive/10"
                    )}>
                      {trade.side === 'buy' ? (
                        <TrendingUp className="h-5 w-5 text-primary" />
                      ) : (
                        <TrendingDown className="h-5 w-5 text-destructive" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-foreground">{trade.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {trade.side.toUpperCase()} • {trade.quantity} @ ${trade.price.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={cn(
                      "font-mono font-semibold",
                      trade.pnl >= 0 ? "text-primary" : "text-destructive"
                    )}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(trade.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
