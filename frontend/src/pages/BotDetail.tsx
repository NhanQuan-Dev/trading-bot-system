import { useParams, useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAppStore } from '@/lib/store';
import { ArrowLeft, Play, Pause, Settings, TrendingUp, TrendingDown } from 'lucide-react';
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
  ReferenceLine,
} from 'recharts';

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

// Mock order depth data
const mockOrderDepth = {
  bids: [
    { price: 43450, amount: 2.5, total: 108625 },
    { price: 43440, amount: 1.8, total: 78192 },
    { price: 43430, amount: 3.2, total: 138976 },
    { price: 43420, amount: 0.9, total: 39078 },
    { price: 43410, amount: 4.1, total: 177981 },
  ],
  asks: [
    { price: 43460, amount: 1.2, total: 52152 },
    { price: 43470, amount: 2.8, total: 121716 },
    { price: 43480, amount: 1.5, total: 65220 },
    { price: 43490, amount: 3.6, total: 156564 },
    { price: 43500, amount: 2.0, total: 87000 },
  ],
};

// Mock recent trades
const mockRecentTrades = [
  { id: 1, time: '14:32:15', price: 43455, amount: 0.125, side: 'buy' },
  { id: 2, time: '14:32:12', price: 43452, amount: 0.350, side: 'sell' },
  { id: 3, time: '14:32:08', price: 43458, amount: 0.082, side: 'buy' },
  { id: 4, time: '14:32:05', price: 43451, amount: 0.215, side: 'buy' },
  { id: 5, time: '14:32:01', price: 43449, amount: 0.500, side: 'sell' },
  { id: 6, time: '14:31:58', price: 43455, amount: 0.178, side: 'buy' },
  { id: 7, time: '14:31:54', price: 43448, amount: 0.420, side: 'sell' },
  { id: 8, time: '14:31:50', price: 43460, amount: 0.095, side: 'buy' },
];

// Mock open positions
const mockOpenPositions = [
  { id: 1, symbol: 'BTC/USDT', side: 'long', size: 0.5, entryPrice: 43200, markPrice: 43455, pnl: 127.5, pnlPercent: 0.59, leverage: 10 },
  { id: 2, symbol: 'ETH/USDT', side: 'short', size: 2.0, entryPrice: 2280, markPrice: 2265, pnl: 30.0, pnlPercent: 0.66, leverage: 5 },
];

// Mock open orders
const mockOpenOrders = [
  { id: 1, symbol: 'BTC/USDT', type: 'limit', side: 'buy', price: 43000, amount: 0.25, filled: 0, status: 'open', createdAt: '2024-01-15 14:20:00' },
  { id: 2, symbol: 'BTC/USDT', type: 'limit', side: 'sell', price: 44000, amount: 0.15, filled: 0, status: 'open', createdAt: '2024-01-15 14:15:00' },
  { id: 3, symbol: 'BTC/USDT', type: 'stop-limit', side: 'sell', price: 42500, amount: 0.5, filled: 0, status: 'open', createdAt: '2024-01-15 14:10:00' },
];

// Mock trade history
const mockTradeHistory = [
  { id: 1, symbol: 'BTC/USDT', side: 'buy', price: 43200, amount: 0.5, fee: 2.16, total: 21602.16, time: '2024-01-15 13:45:00' },
  { id: 2, symbol: 'BTC/USDT', side: 'sell', price: 43350, amount: 0.3, fee: 1.30, total: 13003.70, time: '2024-01-15 12:30:00' },
  { id: 3, symbol: 'BTC/USDT', side: 'buy', price: 43100, amount: 0.8, fee: 3.45, total: 34483.45, time: '2024-01-15 11:15:00' },
  { id: 4, symbol: 'BTC/USDT', side: 'sell', price: 43500, amount: 0.25, fee: 1.09, total: 10873.91, time: '2024-01-15 10:00:00' },
  { id: 5, symbol: 'BTC/USDT', side: 'buy', price: 42800, amount: 1.2, fee: 5.14, total: 51365.14, time: '2024-01-14 22:30:00' },
];

const candleData = generateCandleData();

const statusConfig = {
  running: { label: 'Running', color: 'border-primary/50 text-primary' },
  paused: { label: 'Paused', color: 'border-accent/50 text-accent' },
  stopped: { label: 'Stopped', color: 'border-muted/50 text-muted-foreground' },
  error: { label: 'Error', color: 'border-destructive/50 text-destructive' }
};

// Custom candlestick component for recharts
const CandlestickBar = ({ x, y, width, height, payload }: any) => {
  if (!payload) return null;
  const { open, close, high, low, isUp } = payload;
  const color = isUp ? 'hsl(var(--primary))' : 'hsl(var(--destructive))';
  
  const bodyHeight = Math.abs(close - open);
  const wickTop = high;
  const wickBottom = low;
  const bodyTop = Math.max(open, close);
  
  // Scale calculations
  const minPrice = Math.min(...candleData.map(d => d.low));
  const maxPrice = Math.max(...candleData.map(d => d.high));
  const priceRange = maxPrice - minPrice;
  const chartHeight = 250;
  
  const scaleY = (price: number) => chartHeight - ((price - minPrice) / priceRange) * chartHeight;
  
  return (
    <g>
      {/* Wick */}
      <line
        x1={x + width / 2}
        y1={scaleY(wickTop)}
        x2={x + width / 2}
        y2={scaleY(wickBottom)}
        stroke={color}
        strokeWidth={1}
      />
      {/* Body */}
      <rect
        x={x + 2}
        y={scaleY(bodyTop)}
        width={Math.max(width - 4, 2)}
        height={Math.max((bodyHeight / priceRange) * chartHeight, 2)}
        fill={isUp ? color : color}
        stroke={color}
      />
    </g>
  );
};

export default function BotDetail() {
  const { botId } = useParams();
  const navigate = useNavigate();
  const bots = useAppStore((state) => state.bots);
  const updateBot = useAppStore((state) => state.updateBot);
  
  const bot = bots.find(b => b.id === botId);
  
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

  const config = statusConfig[bot.status];
  const isProfit = bot.pnl >= 0;

  const handleToggle = () => {
    if (bot.status === 'running') {
      updateBot(bot.id, { status: 'paused' });
    } else {
      updateBot(bot.id, { status: 'running' });
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
              <p className="text-muted-foreground">{bot.symbol} • {bot.exchange} • {bot.strategy}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleToggle} disabled={bot.status === 'error'}>
              {bot.status === 'running' ? (
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

        {/* Summary Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Total P&L</p>
              <p className={cn("text-2xl font-bold", isProfit ? "text-primary" : "text-destructive")}>
                {isProfit ? '+' : ''}${bot.pnl.toFixed(2)}
              </p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Win Rate</p>
              <p className="text-2xl font-bold text-foreground">{bot.winRate.toFixed(1)}%</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">Total Trades</p>
              <p className="text-2xl font-bold text-foreground">{bot.totalTrades}</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground">P&L %</p>
              <p className={cn("text-2xl font-bold", bot.pnlPercent >= 0 ? "text-primary" : "text-destructive")}>
                {bot.pnlPercent >= 0 ? '+' : ''}{bot.pnlPercent.toFixed(2)}%
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Candlestick Chart */}
          <Card className="border-border bg-card lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Price Chart</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={candleData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <XAxis 
                      dataKey="time" 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                      interval={9}
                    />
                    <YAxis 
                      domain={['dataMin - 100', 'dataMax + 100']}
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
                      formatter={(value: any, name: string) => [
                        typeof value === 'number' ? value.toFixed(2) : value,
                        name.charAt(0).toUpperCase() + name.slice(1)
                      ]}
                    />
                    <Bar dataKey="close" shape={<CandlestickBar />}>
                      {candleData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.isUp ? 'hsl(var(--primary))' : 'hsl(var(--destructive))'} />
                      ))}
                    </Bar>
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Order Depth & Recent Trades */}
          <div className="space-y-4">
            {/* Order Depth */}
            <Card className="border-border bg-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Order Depth</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[180px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border hover:bg-transparent">
                        <TableHead className="h-8 text-xs">Price</TableHead>
                        <TableHead className="h-8 text-right text-xs">Amount</TableHead>
                        <TableHead className="h-8 text-right text-xs">Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mockOrderDepth.asks.slice().reverse().map((ask, i) => (
                        <TableRow key={`ask-${i}`} className="border-0 hover:bg-muted/30">
                          <TableCell className="py-1 font-mono text-xs text-destructive">{ask.price.toLocaleString()}</TableCell>
                          <TableCell className="py-1 text-right font-mono text-xs">{ask.amount}</TableCell>
                          <TableCell className="py-1 text-right font-mono text-xs text-muted-foreground">{ask.total.toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="border-y border-border bg-muted/20">
                        <TableCell colSpan={3} className="py-1 text-center font-mono text-sm font-semibold text-foreground">
                          43,455.00
                        </TableCell>
                      </TableRow>
                      {mockOrderDepth.bids.map((bid, i) => (
                        <TableRow key={`bid-${i}`} className="border-0 hover:bg-muted/30">
                          <TableCell className="py-1 font-mono text-xs text-primary">{bid.price.toLocaleString()}</TableCell>
                          <TableCell className="py-1 text-right font-mono text-xs">{bid.amount}</TableCell>
                          <TableCell className="py-1 text-right font-mono text-xs text-muted-foreground">{bid.total.toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Recent Trades */}
            <Card className="border-border bg-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Recent Trades</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[180px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border hover:bg-transparent">
                        <TableHead className="h-8 text-xs">Time</TableHead>
                        <TableHead className="h-8 text-right text-xs">Price</TableHead>
                        <TableHead className="h-8 text-right text-xs">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mockRecentTrades.map((trade) => (
                        <TableRow key={trade.id} className="border-0 hover:bg-muted/30">
                          <TableCell className="py-1 font-mono text-xs text-muted-foreground">{trade.time}</TableCell>
                          <TableCell className={cn("py-1 text-right font-mono text-xs", trade.side === 'buy' ? "text-primary" : "text-destructive")}>
                            {trade.price.toLocaleString()}
                          </TableCell>
                          <TableCell className="py-1 text-right font-mono text-xs">{trade.amount}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

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
                      <TableHead className="text-right">Mark Price</TableHead>
                      <TableHead className="text-right">P&L</TableHead>
                      <TableHead className="text-right">Leverage</TableHead>
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
                        <TableCell className="text-right font-mono">${pos.markPrice.toLocaleString()}</TableCell>
                        <TableCell className={cn("text-right font-mono", pos.pnl >= 0 ? "text-primary" : "text-destructive")}>
                          <div className="flex items-center justify-end gap-1">
                            {pos.pnl >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                            ${Math.abs(pos.pnl).toFixed(2)} ({pos.pnlPercent}%)
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">{pos.leverage}x</TableCell>
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
                      <TableHead className="text-right">Filled</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockOpenOrders.map((order) => (
                      <TableRow key={order.id} className="border-border">
                        <TableCell className="font-medium">{order.symbol}</TableCell>
                        <TableCell className="capitalize">{order.type}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={order.side === 'buy' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                            {order.side.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">${order.price.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{order.amount}</TableCell>
                        <TableCell className="text-right font-mono">{order.filled}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="border-accent/50 text-accent">{order.status}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{order.createdAt}</TableCell>
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
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Fee</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead>Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockTradeHistory.map((trade) => (
                      <TableRow key={trade.id} className="border-border">
                        <TableCell className="font-medium">{trade.symbol}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={trade.side === 'buy' ? 'border-primary/50 text-primary' : 'border-destructive/50 text-destructive'}>
                            {trade.side.toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">${trade.price.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{trade.amount}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">${trade.fee}</TableCell>
                        <TableCell className="text-right font-mono">${trade.total.toLocaleString()}</TableCell>
                        <TableCell className="text-muted-foreground">{trade.time}</TableCell>
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
