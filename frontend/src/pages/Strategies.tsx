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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  BarChart3,
  Zap,
  Eye
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Strategy interface
interface Strategy {
  id: string;
  name: string;
  type: 'Grid Trading' | 'DCA' | 'Trend Following' | 'Mean Reversion' | 'Scalping' | 'Arbitrage' | 'Custom Strategy';
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

// Backend response shape
interface BackendStrategy {
  id: string;
  name: string;
  strategy_type: string;
  description: string;
  is_active: boolean;
  total_trades: number;
  win_rate: number;
  total_profit_loss: number;
  max_drawdown: number;
  // Add other fields if needed, but these are the ones used in the UI mostly
}

const mapStrategyType = (type: string): Strategy['type'] => {
  switch (type?.toUpperCase()) {
    case 'GRID': return 'Grid Trading';
    case 'DCA': return 'DCA';
    case 'TREND_FOLLOWING': return 'Trend Following';
    case 'MEAN_REVERSION': return 'Mean Reversion';
    case 'SCALPING': return 'Scalping';
    case 'ARBITRAGE': return 'Arbitrage';
    case 'MARTINGALE': return 'Custom Strategy';
    default: return 'Custom Strategy';
  }
};


// Mock strategies data removed
const mockStrategies: Strategy[] = []; // Initial empty state

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

import { useEffect } from 'react';

// ... (other imports)

export default function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);

  useEffect(() => {
    fetch('/api/v1/strategies')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data: BackendStrategy[]) => {
        const mappedStrategies: Strategy[] = data.map(s => ({
          id: s.id,
          name: s.name,
          type: mapStrategyType(s.strategy_type),
          description: s.description,
          activeBots: s.is_active ? 1 : 0, // Simplified mapping as backend doesn't give active bot count directly in list yet? Or it does? 
          // Wait, backend response `StrategyResponse` has `total_trades`, `win_rate`, `total_profit_loss`, `max_drawdown`
          totalTrades: s.total_trades || 0,
          winRate: s.win_rate || 0,
          avgPnl: 0, // Not in list response
          totalPnl: s.total_profit_loss || 0,
          sharpeRatio: 0, // Not in list response
          maxDrawdown: s.max_drawdown || 0,
          profitFactor: 0, // Not in list response
          avgHoldTime: '0h', // Not in list response
          status: s.is_active ? 'active' : 'inactive',
        }));
        setStrategies(mappedStrategies);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch strategies", err);
        setStrategies([]); // Ensure it's empty array on error
        setLoading(false);
      });
  }, []);

  // Calculate aggregate metrics
  const totalStrategies = strategies.length;
  const activeStrategies = strategies.filter(s => s.status === 'active').length;
  const totalPnl = strategies.reduce((acc, s) => acc + s.totalPnl, 0);
  const winRateStrategies = strategies.filter(s => s.totalTrades > 0);
  const avgWinRate = winRateStrategies.length > 0
    ? winRateStrategies.reduce((acc, s) => acc + s.winRate, 0) / winRateStrategies.length
    : 0;

  const bestStrategy = strategies.length > 0
    ? strategies.reduce((best, s) => s.totalPnl > best.totalPnl ? s : best, strategies[0])
    : null;

  const sharpeStrategies = strategies.filter(s => s.sharpeRatio > 0);
  const avgSharpe = sharpeStrategies.length > 0
    ? sharpeStrategies.reduce((acc, s) => acc + s.sharpeRatio, 0) / sharpeStrategies.length
    : 0;

  if (loading) {
    return <div className="p-8 text-center">Loading strategies...</div>;
  }

  return (
    <DashboardLayout>
      <Dialog open={!!selectedStrategy} onOpenChange={(open) => !open && setSelectedStrategy(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedStrategy && getTypeIcon(selectedStrategy.type)}
              {selectedStrategy?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedStrategy?.description}
            </DialogDescription>
          </DialogHeader>
          {selectedStrategy && (
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">Total P&L</p>
                <p className={cn("text-lg font-bold", selectedStrategy.totalPnl >= 0 ? "text-primary" : "text-destructive")}>
                  {selectedStrategy.totalPnl >= 0 ? '+' : ''}${selectedStrategy.totalPnl.toLocaleString()}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">Win Rate</p>
                <p className={cn("text-lg font-bold", selectedStrategy.winRate >= 50 ? "text-primary" : "text-destructive")}>
                  {selectedStrategy.winRate}%
                </p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">Sharpe Ratio</p>
                <p className="text-lg font-bold">{selectedStrategy.sharpeRatio}</p>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">Active Bots</p>
                <p className="text-lg font-bold">{selectedStrategy.activeBots}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Strategy Management</h1>
            <p className="text-muted-foreground">Monitor and manage all trading strategies</p>
          </div>
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
            subtitle={bestStrategy ? `Best: ${bestStrategy.name}` : 'No strategies'}
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
                {strategies.map((strategy) => (
                  <TableRow key={strategy.id} className="border-border">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{getTypeIcon(strategy.type)}</span>
                        <div>
                          <p className="font-medium text-foreground">{strategy.name}</p>
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
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title="View Details"
                          onClick={() => setSelectedStrategy(strategy)}
                        >
                          <Eye className="h-4 w-4" />
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
              {bestStrategy ? (
                <>
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
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
                  <p>No active strategies</p>
                </div>
              )}
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
              {strategies.filter(s => s.status !== 'inactive').map((strategy) => {
                const totalActivePnl = strategies.filter(s => s.status !== 'inactive')
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
