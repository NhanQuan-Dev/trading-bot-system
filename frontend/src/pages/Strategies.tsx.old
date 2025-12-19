import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Target, 
  BarChart3, 
  Zap,
  Plus,
  Settings,
  Play,
  Copy
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Strategy interface
interface Strategy {
  id: string;
  name: string;
  type: 'Grid Trading' | 'DCA' | 'Trend Following' | 'Mean Reversion' | 'Scalping' | 'Arbitrage';
  description: string;
  activeBots: number;
  totalTrades: number;
  winRate: number;
  avgPnl: number;
  totalPnl: number;
  sharpeRatio: number;
  maxDrawdown: number;
  profitFactor: number;
  avgHoldTime: string;
  status: 'active' | 'inactive' | 'testing';
}

// Mock strategies data
const mockStrategies: Strategy[] = [
  {
    id: '1',
    name: 'Grid Trading',
    type: 'Grid Trading',
    description: 'Place buy and sell orders at preset intervals around a set price',
    activeBots: 3,
    totalTrades: 456,
    winRate: 72.5,
    avgPnl: 15.45,
    totalPnl: 7045.20,
    sharpeRatio: 1.85,
    maxDrawdown: 8.2,
    profitFactor: 2.1,
    avgHoldTime: '2h 15m',
    status: 'active'
  },
  {
    id: '2',
    name: 'DCA (Dollar Cost Averaging)',
    type: 'DCA',
    description: 'Invest fixed amounts at regular intervals regardless of price',
    activeBots: 2,
    totalTrades: 189,
    winRate: 78.3,
    avgPnl: 22.10,
    totalPnl: 4176.90,
    sharpeRatio: 2.15,
    maxDrawdown: 5.5,
    profitFactor: 2.8,
    avgHoldTime: '12h 30m',
    status: 'active'
  },
  {
    id: '3',
    name: 'Trend Following',
    type: 'Trend Following',
    description: 'Follow the market momentum using moving averages and trend indicators',
    activeBots: 1,
    totalTrades: 78,
    winRate: 45.2,
    avgPnl: -8.50,
    totalPnl: -663.00,
    sharpeRatio: 0.65,
    maxDrawdown: 18.5,
    profitFactor: 0.85,
    avgHoldTime: '6h 45m',
    status: 'active'
  },
  {
    id: '4',
    name: 'Mean Reversion',
    type: 'Mean Reversion',
    description: 'Trade based on price returning to its historical average',
    activeBots: 1,
    totalTrades: 134,
    winRate: 58.2,
    avgPnl: 8.75,
    totalPnl: 1172.50,
    sharpeRatio: 1.25,
    maxDrawdown: 12.3,
    profitFactor: 1.45,
    avgHoldTime: '4h 20m',
    status: 'active'
  },
  {
    id: '5',
    name: 'Scalping',
    type: 'Scalping',
    description: 'Make many small profits on minor price changes throughout the day',
    activeBots: 0,
    totalTrades: 892,
    winRate: 62.1,
    avgPnl: 3.25,
    totalPnl: 2899.00,
    sharpeRatio: 1.45,
    maxDrawdown: 6.8,
    profitFactor: 1.75,
    avgHoldTime: '15m',
    status: 'testing'
  },
  {
    id: '6',
    name: 'Arbitrage',
    type: 'Arbitrage',
    description: 'Exploit price differences between exchanges or trading pairs',
    activeBots: 0,
    totalTrades: 0,
    winRate: 0,
    avgPnl: 0,
    totalPnl: 0,
    sharpeRatio: 0,
    maxDrawdown: 0,
    profitFactor: 0,
    avgHoldTime: '-',
    status: 'inactive'
  }
];

function getStatusColor(status: Strategy['status']) {
  switch (status) {
    case 'active': return 'bg-primary/20 text-primary border-primary/30';
    case 'testing': return 'bg-warning/20 text-warning border-warning/30';
    case 'inactive': return 'bg-muted text-muted-foreground border-border';
  }
}

function getTypeIcon(type: Strategy['type']) {
  switch (type) {
    case 'Grid Trading': return '📊';
    case 'DCA': return '💰';
    case 'Trend Following': return '📈';
    case 'Mean Reversion': return '🔄';
    case 'Scalping': return '⚡';
    case 'Arbitrage': return '🔀';
  }
}

function MetricCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend 
}: { 
  title: string; 
  value: string; 
  subtitle?: string; 
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
}) {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{title}</p>
              <p className={cn(
                "text-lg font-bold",
                trend === 'up' && "text-primary",
                trend === 'down' && "text-destructive",
                trend === 'neutral' && "text-foreground"
              )}>
                {value}
              </p>
              {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
            </div>
          </div>
          {trend && (
            trend === 'up' ? (
              <TrendingUp className="h-4 w-4 text-primary" />
            ) : trend === 'down' ? (
              <TrendingDown className="h-4 w-4 text-destructive" />
            ) : null
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function Strategies() {
  // Calculate aggregate metrics
  const totalStrategies = mockStrategies.length;
  const activeStrategies = mockStrategies.filter(s => s.status === 'active').length;
  const totalPnl = mockStrategies.reduce((acc, s) => acc + s.totalPnl, 0);
  const avgWinRate = mockStrategies.filter(s => s.totalTrades > 0).reduce((acc, s) => acc + s.winRate, 0) / 
    mockStrategies.filter(s => s.totalTrades > 0).length;
  const bestStrategy = mockStrategies.reduce((best, s) => s.totalPnl > best.totalPnl ? s : best);
  const avgSharpe = mockStrategies.filter(s => s.sharpeRatio > 0).reduce((acc, s) => acc + s.sharpeRatio, 0) /
    mockStrategies.filter(s => s.sharpeRatio > 0).length;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Strategy Management</h1>
            <p className="text-muted-foreground">Monitor and manage all trading strategies</p>
          </div>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Create Strategy
          </Button>
        </div>

        {/* Summary Metrics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total Strategies"
            value={totalStrategies.toString()}
            subtitle={`${activeStrategies} active`}
            icon={Activity}
            trend="neutral"
          />
          <MetricCard
            title="Total P&L"
            value={`$${totalPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
            subtitle="All strategies combined"
            icon={totalPnl >= 0 ? TrendingUp : TrendingDown}
            trend={totalPnl >= 0 ? 'up' : 'down'}
          />
          <MetricCard
            title="Avg Win Rate"
            value={`${avgWinRate.toFixed(1)}%`}
            subtitle="Across all strategies"
            icon={Target}
            trend={avgWinRate >= 50 ? 'up' : 'down'}
          />
          <MetricCard
            title="Avg Sharpe Ratio"
            value={avgSharpe.toFixed(2)}
            subtitle={`Best: ${bestStrategy.name}`}
            icon={BarChart3}
            trend={avgSharpe >= 1 ? 'up' : 'neutral'}
          />
        </div>

        {/* Strategy Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-primary" />
              All Strategies
            </CardTitle>
            <CardDescription>
              Performance metrics for each trading strategy
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-muted-foreground">Strategy</TableHead>
                  <TableHead className="text-muted-foreground text-center">Status</TableHead>
                  <TableHead className="text-muted-foreground text-center">Active Bots</TableHead>
                  <TableHead className="text-muted-foreground text-right">Win Rate</TableHead>
                  <TableHead className="text-muted-foreground text-right">Total P&L</TableHead>
                  <TableHead className="text-muted-foreground text-right">Sharpe</TableHead>
                  <TableHead className="text-muted-foreground text-right">Max DD</TableHead>
                  <TableHead className="text-muted-foreground text-right">Profit Factor</TableHead>
                  <TableHead className="text-muted-foreground text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockStrategies.map((strategy) => (
                  <TableRow key={strategy.id} className="border-border">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{getTypeIcon(strategy.type)}</span>
                        <div>
                          <p className="font-medium text-foreground">{strategy.name}</p>
                          <p className="text-xs text-muted-foreground max-w-[200px] truncate">
                            {strategy.description}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline" className={cn("capitalize", getStatusColor(strategy.status))}>
                        {strategy.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className="font-medium text-foreground">{strategy.activeBots}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      {strategy.totalTrades > 0 ? (
                        <div className="space-y-1">
                          <span className={cn(
                            "font-medium",
                            strategy.winRate >= 50 ? "text-primary" : "text-destructive"
                          )}>
                            {strategy.winRate.toFixed(1)}%
                          </span>
                          <Progress 
                            value={strategy.winRate} 
                            className="h-1 w-16 ml-auto" 
                          />
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={cn(
                        "font-medium",
                        strategy.totalPnl >= 0 ? "text-primary" : "text-destructive"
                      )}>
                        {strategy.totalPnl >= 0 ? '+' : ''}${strategy.totalPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={cn(
                        "font-medium",
                        strategy.sharpeRatio >= 1 ? "text-primary" : 
                        strategy.sharpeRatio > 0 ? "text-warning" : "text-muted-foreground"
                      )}>
                        {strategy.sharpeRatio > 0 ? strategy.sharpeRatio.toFixed(2) : '-'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={cn(
                        "font-medium",
                        strategy.maxDrawdown > 15 ? "text-destructive" :
                        strategy.maxDrawdown > 10 ? "text-warning" : "text-primary"
                      )}>
                        {strategy.maxDrawdown > 0 ? `${strategy.maxDrawdown.toFixed(1)}%` : '-'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={cn(
                        "font-medium",
                        strategy.profitFactor >= 1.5 ? "text-primary" :
                        strategy.profitFactor >= 1 ? "text-warning" : "text-destructive"
                      )}>
                        {strategy.profitFactor > 0 ? strategy.profitFactor.toFixed(2) : '-'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-center gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Settings className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Strategy Performance Details */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Best Performing Strategy */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <TrendingUp className="h-5 w-5" />
                Best Performing Strategy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <span className="text-3xl">{getTypeIcon(bestStrategy.type)}</span>
                <div>
                  <h3 className="text-lg font-bold text-foreground">{bestStrategy.name}</h3>
                  <p className="text-sm text-muted-foreground">{bestStrategy.description}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Total P&L</p>
                  <p className="text-lg font-bold text-primary">
                    +${bestStrategy.totalPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Win Rate</p>
                  <p className="text-lg font-bold text-foreground">{bestStrategy.winRate.toFixed(1)}%</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Sharpe Ratio</p>
                  <p className="text-lg font-bold text-foreground">{bestStrategy.sharpeRatio.toFixed(2)}</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Profit Factor</p>
                  <p className="text-lg font-bold text-foreground">{bestStrategy.profitFactor.toFixed(2)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Strategy Type Distribution */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                Strategy Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {mockStrategies.filter(s => s.status !== 'inactive').map((strategy) => {
                const totalActivePnl = mockStrategies.filter(s => s.status !== 'inactive')
                  .reduce((acc, s) => acc + Math.abs(s.totalPnl), 0);
                const percentage = totalActivePnl > 0 ? (Math.abs(strategy.totalPnl) / totalActivePnl) * 100 : 0;
                
                return (
                  <div key={strategy.id} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span>{getTypeIcon(strategy.type)}</span>
                        <span className="text-foreground">{strategy.name}</span>
                      </div>
                      <span className={cn(
                        "font-medium",
                        strategy.totalPnl >= 0 ? "text-primary" : "text-destructive"
                      )}>
                        {strategy.totalPnl >= 0 ? '+' : ''}${strategy.totalPnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                    <Progress value={percentage} className="h-2" />
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
