import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Download, TrendingUp, TrendingDown, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
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
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Bar,
  Cell,
  Line,
  Area,
  AreaChart,
  LineChart,
  ReferenceDot,
  CartesianGrid,
} from 'recharts';

// Mock backtest data
const mockBacktestData: Record<string, any> = {
  'bt-001': {
    id: 'bt-001',
    strategy: 'Grid Trading',
    symbol: 'BTC/USDT',
    timeframe: '1h',
    startDate: '2024-01-01',
    endDate: '2024-02-01',
    initialCapital: 10000,
    finalCapital: 12845,
    netProfit: 2845,
    netProfitPercent: 28.45,
    winRate: 67.5,
    maxDrawdown: -8.2,
    sharpeRatio: 1.92,
    totalTrades: 234,
    profitFactor: 2.1,
  },
  'bt-002': {
    id: 'bt-002',
    strategy: 'DCA',
    symbol: 'ETH/USDT',
    timeframe: '4h',
    startDate: '2024-01-15',
    endDate: '2024-02-15',
    initialCapital: 5000,
    finalCapital: 4680,
    netProfit: -320,
    netProfitPercent: -6.4,
    winRate: 42.3,
    maxDrawdown: -15.5,
    sharpeRatio: 0.85,
    totalTrades: 156,
    profitFactor: 0.87,
  },
  'bt-003': {
    id: 'bt-003',
    strategy: 'Trend Following',
    symbol: 'SOL/USDT',
    timeframe: '1d',
    startDate: '2024-02-01',
    endDate: '2024-03-01',
    initialCapital: 15000,
    finalCapital: 19250,
    netProfit: 4250,
    netProfitPercent: 28.33,
    winRate: 58.2,
    maxDrawdown: -12.1,
    sharpeRatio: 1.65,
    totalTrades: 89,
    profitFactor: 1.85,
  },
  'bt-004': {
    id: 'bt-004',
    strategy: 'Mean Reversion',
    symbol: 'BTC/USDT',
    timeframe: '15m',
    startDate: '2024-02-10',
    endDate: '2024-02-20',
    initialCapital: 8000,
    finalCapital: 9120,
    netProfit: 1120,
    netProfitPercent: 14.0,
    winRate: 72.1,
    maxDrawdown: -5.8,
    sharpeRatio: 2.15,
    totalTrades: 412,
    profitFactor: 2.45,
  },
};

// Generate candlestick data with trade signals
const generateCandleDataWithSignals = () => {
  const data = [];
  let price = 43500;
  const trades = [
    { index: 5, type: 'buy' },
    { index: 12, type: 'sell' },
    { index: 18, type: 'buy' },
    { index: 25, type: 'sell' },
    { index: 32, type: 'buy' },
    { index: 38, type: 'buy' },
    { index: 45, type: 'sell' },
  ];
  
  for (let i = 0; i < 50; i++) {
    const open = price;
    const change = (Math.random() - 0.5) * 500;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * 200;
    const low = Math.min(open, close) - Math.random() * 200;
    price = close;
    
    const trade = trades.find(t => t.index === i);
    
    data.push({
      time: `${String(i).padStart(2, '0')}:00`,
      index: i,
      open,
      high,
      low,
      close,
      isUp: close >= open,
      signal: trade?.type || null,
      signalPrice: trade ? (trade.type === 'buy' ? low - 100 : high + 100) : null,
    });
  }
  return data;
};

// Generate equity curve data
const generateEquityData = (initialCapital: number, finalCapital: number) => {
  const data = [];
  const days = 30;
  const totalGain = finalCapital - initialCapital;
  let balance = initialCapital;
  let maxBalance = initialCapital;
  
  for (let i = 0; i <= days; i++) {
    const dailyChange = (totalGain / days) + (Math.random() - 0.5) * (totalGain * 0.1);
    balance += dailyChange;
    maxBalance = Math.max(maxBalance, balance);
    const drawdown = ((balance - maxBalance) / maxBalance) * 100;
    const unrealizedPnl = (Math.random() - 0.3) * 200;
    
    data.push({
      day: i,
      date: `Day ${i}`,
      balance: Math.max(balance, initialCapital * 0.7),
      balanceWithUnrealized: Math.max(balance + unrealizedPnl, initialCapital * 0.7),
      drawdown: Math.min(drawdown, 0),
      netProfit: balance - initialCapital,
    });
  }
  return data;
};

// Mock open positions (for backtest, these are the final positions)
const mockOpenPositions = [
  { id: 1, symbol: 'BTC/USDT', side: 'long', size: 0.5, entryPrice: 43200, exitPrice: 43455, pnl: 127.5, pnlPercent: 0.59 },
  { id: 2, symbol: 'BTC/USDT', side: 'short', size: 0.3, entryPrice: 44100, exitPrice: 43800, pnl: 90.0, pnlPercent: 0.68 },
];

// Mock open orders (pending orders at end of backtest)
const mockOpenOrders = [
  { id: 1, symbol: 'BTC/USDT', type: 'limit', side: 'buy', price: 43000, amount: 0.25, status: 'unfilled' },
  { id: 2, symbol: 'BTC/USDT', type: 'limit', side: 'sell', price: 44500, amount: 0.15, status: 'unfilled' },
];

// Mock trade history
const mockTradeHistory = [
  { id: 1, symbol: 'BTC/USDT', side: 'buy', price: 43200, amount: 0.5, fee: 2.16, pnl: 127.5, time: '2024-01-15 13:45:00' },
  { id: 2, symbol: 'BTC/USDT', side: 'sell', price: 43350, amount: 0.3, fee: 1.30, pnl: -45.2, time: '2024-01-15 12:30:00' },
  { id: 3, symbol: 'BTC/USDT', side: 'buy', price: 43100, amount: 0.8, fee: 3.45, pnl: 210.8, time: '2024-01-15 11:15:00' },
  { id: 4, symbol: 'BTC/USDT', side: 'sell', price: 43500, amount: 0.25, fee: 1.09, pnl: 85.3, time: '2024-01-15 10:00:00' },
  { id: 5, symbol: 'BTC/USDT', side: 'buy', price: 42800, amount: 1.2, fee: 5.14, pnl: 320.0, time: '2024-01-14 22:30:00' },
  { id: 6, symbol: 'BTC/USDT', side: 'sell', price: 43600, amount: 0.4, fee: 1.74, pnl: -28.5, time: '2024-01-14 20:15:00' },
  { id: 7, symbol: 'BTC/USDT', side: 'buy', price: 43050, amount: 0.6, fee: 2.58, pnl: 156.2, time: '2024-01-14 18:00:00' },
];

const candleData = generateCandleDataWithSignals();

// Custom candlestick bar component
const CandlestickBar = ({ x, y, width, height, payload }: any) => {
  if (!payload) return null;
  const { open, close, high, low, isUp } = payload;
  const color = isUp ? 'hsl(var(--primary))' : 'hsl(var(--destructive))';
  
  const minPrice = Math.min(...candleData.map(d => d.low));
  const maxPrice = Math.max(...candleData.map(d => d.high));
  const priceRange = maxPrice - minPrice;
  const chartHeight = 200;
  
  const scaleY = (price: number) => chartHeight - ((price - minPrice) / priceRange) * chartHeight;
  const bodyHeight = Math.abs(close - open);
  const bodyTop = Math.max(open, close);
  
  return (
    <g>
      <line
        x1={x + width / 2}
        y1={scaleY(high)}
        x2={x + width / 2}
        y2={scaleY(low)}
        stroke={color}
        strokeWidth={1}
      />
      <rect
        x={x + 2}
        y={scaleY(bodyTop)}
        width={Math.max(width - 4, 2)}
        height={Math.max((bodyHeight / priceRange) * chartHeight, 2)}
        fill={color}
        stroke={color}
      />
    </g>
  );
};

// Trade signal marker component
const TradeSignalMarker = ({ cx, cy, payload }: any) => {
  if (!payload?.signal) return null;
  
  const isBuy = payload.signal === 'buy';
  const color = isBuy ? 'hsl(var(--primary))' : 'hsl(var(--destructive))';
  
  return (
    <g transform={`translate(${cx}, ${cy})`}>
      {isBuy ? (
        <>
          <polygon
            points="0,-12 -8,4 8,4"
            fill={color}
            stroke={color}
            strokeWidth={1}
          />
          <text x={0} y={15} textAnchor="middle" fontSize={9} fill={color} fontWeight="bold">
            BUY
          </text>
        </>
      ) : (
        <>
          <polygon
            points="0,12 -8,-4 8,-4"
            fill={color}
            stroke={color}
            strokeWidth={1}
          />
          <text x={0} y={-15} textAnchor="middle" fontSize={9} fill={color} fontWeight="bold">
            SELL
          </text>
        </>
      )}
    </g>
  );
};

export default function BacktestDetail() {
  const { backtestId } = useParams();
  const navigate = useNavigate();
  
  const backtest = mockBacktestData[backtestId || ''];
  
  if (!backtest) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-muted-foreground">Backtest not found</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/backtest')}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Backtests
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const equityData = generateEquityData(backtest.initialCapital, backtest.finalCapital);
  const isProfit = backtest.netProfit >= 0;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/backtest')}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-foreground">{backtest.strategy}</h1>
                <Badge variant="outline" className="border-primary/50 text-primary">Completed</Badge>
              </div>
              <p className="text-muted-foreground">{backtest.symbol} • {backtest.timeframe} • {backtest.startDate} to {backtest.endDate}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" /> Export Report
          </Button>
        </div>

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-6">
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Net P&L</p>
              <p className={cn("text-2xl font-bold", isProfit ? "text-primary" : "text-destructive")}>
                {isProfit ? '+' : ''}${backtest.netProfit.toLocaleString()}
              </p>
              <p className={cn("text-xs", isProfit ? "text-primary/70" : "text-destructive/70")}>
                {isProfit ? '+' : ''}{backtest.netProfitPercent.toFixed(2)}%
              </p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold text-foreground">{backtest.winRate.toFixed(1)}%</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Total Trades</p>
              <p className="text-2xl font-bold text-foreground">{backtest.totalTrades}</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Max Drawdown</p>
              <p className="text-2xl font-bold text-destructive">{backtest.maxDrawdown}%</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Sharpe Ratio</p>
              <p className="text-2xl font-bold text-foreground">{backtest.sharpeRatio.toFixed(2)}</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Profit Factor</p>
              <p className="text-2xl font-bold text-foreground">{backtest.profitFactor.toFixed(2)}</p>
            </CardContent>
          </Card>
        </div>

        {/* Price Chart with Trade Signals */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Price Chart with Trade Signals</CardTitle>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <ArrowUpCircle className="h-4 w-4 text-primary" />
                  <span className="text-muted-foreground">Buy Signal</span>
                </div>
                <div className="flex items-center gap-1">
                  <ArrowDownCircle className="h-4 w-4 text-destructive" />
                  <span className="text-muted-foreground">Sell Signal</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={candleData} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                  <XAxis 
                    dataKey="time" 
                    axisLine={false} 
                    tickLine={false}
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                    interval={9}
                  />
                  <YAxis 
                    domain={['dataMin - 200', 'dataMax + 200']}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                    orientation="right"
                    tickFormatter={(v) => v.toLocaleString()}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: 'hsl(var(--foreground))' }}
                    formatter={(value: any, name: string) => {
                      if (name === 'signal') return null;
                      return [typeof value === 'number' ? value.toFixed(2) : value, name];
                    }}
                  />
                  <Bar dataKey="close" shape={<CandlestickBar />}>
                    {candleData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.isUp ? 'hsl(var(--primary))' : 'hsl(var(--destructive))'} />
                    ))}
                  </Bar>
                  {/* Trade signal markers */}
                  {candleData.filter(d => d.signal).map((d, i) => (
                    <ReferenceDot
                      key={`signal-${i}`}
                      x={d.time}
                      y={d.signalPrice}
                      shape={<TradeSignalMarker />}
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Equity Curve Panel */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Equity Curve & Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Balance + Unrealized PnL */}
              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">Balance & Unrealized P&L</h4>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityData}>
                      <defs>
                        <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                      <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} tickFormatter={(v) => `$${(v/1000).toFixed(1)}k`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number) => [`$${value.toFixed(2)}`, 'Balance']}
                      />
                      <Area
                        type="monotone"
                        dataKey="balanceWithUnrealized"
                        stroke="hsl(var(--accent))"
                        strokeWidth={1}
                        strokeDasharray="4 4"
                        fillOpacity={0}
                        name="With Unrealized"
                      />
                      <Area
                        type="monotone"
                        dataKey="balance"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorBalance)"
                        name="Balance"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Drawdown */}
              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">Drawdown</h4>
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equityData}>
                      <defs>
                        <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                      <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(1)}%`} domain={['dataMin - 2', 0]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number) => [`${value.toFixed(2)}%`, 'Drawdown']}
                      />
                      <Area
                        type="monotone"
                        dataKey="drawdown"
                        stroke="hsl(var(--destructive))"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorDrawdown)"
                        name="Drawdown"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Net Profit Over Time */}
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-muted-foreground">Net Profit Over Time</h4>
              <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={equityData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                    <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                      formatter={(value: number) => [`$${value.toFixed(2)}`, 'Net Profit']}
                    />
                    <Line
                      type="monotone"
                      dataKey="netProfit"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={false}
                      name="Net Profit"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tables Section */}
        <Tabs defaultValue="positions" className="w-full">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="positions">Open Positions ({mockOpenPositions.length})</TabsTrigger>
            <TabsTrigger value="orders">Open Orders ({mockOpenOrders.length})</TabsTrigger>
            <TabsTrigger value="history">Trade History</TabsTrigger>
          </TabsList>

          <TabsContent value="positions" className="mt-4">
            <Card className="border-border bg-card">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Size</TableHead>
                      <TableHead className="text-right">Entry Price</TableHead>
                      <TableHead className="text-right">Exit Price</TableHead>
                      <TableHead className="text-right">P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockOpenPositions.map((pos) => (
                      <TableRow key={pos.id} className="border-border">
                        <TableCell className="font-medium">{pos.symbol}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={pos.side === 'long' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                            {pos.side.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">{pos.size}</TableCell>
                        <TableCell className="text-right font-mono">${pos.entryPrice.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">${pos.exitPrice.toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {pos.pnl >= 0 ? (
                              <TrendingUp className="h-3 w-3 text-primary" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-destructive" />
                            )}
                            <span className={cn("font-mono", pos.pnl >= 0 ? "text-primary" : "text-destructive")}>
                              {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)} ({pos.pnlPercent.toFixed(2)}%)
                            </span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
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
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockOpenOrders.map((order) => (
                      <TableRow key={order.id} className="border-border">
                        <TableCell className="font-medium">{order.symbol}</TableCell>
                        <TableCell className="uppercase text-muted-foreground">{order.type}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={order.side === 'buy' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                            {order.side.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">${order.price.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{order.amount}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="border-accent/50 text-accent">
                            {order.status.toUpperCase()}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="mt-4">
            <Card className="border-border bg-card">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead>Time</TableHead>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Fee</TableHead>
                      <TableHead className="text-right">P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockTradeHistory.map((trade) => (
                      <TableRow key={trade.id} className="border-border">
                        <TableCell className="font-mono text-sm text-muted-foreground">{trade.time}</TableCell>
                        <TableCell className="font-medium">{trade.symbol}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={trade.side === 'buy' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                            {trade.side.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">${trade.price.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{trade.amount}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">${trade.fee}</TableCell>
                        <TableCell className="text-right">
                          <span className={cn("font-mono", trade.pnl >= 0 ? "text-primary" : "text-destructive")}>
                            {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
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
