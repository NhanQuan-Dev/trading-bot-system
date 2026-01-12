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
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { Plus } from "lucide-react";
import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  BarChart3,
  Zap,
  Eye,
  Copy
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiClient } from '@/lib/api/client';

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
  code_content?: string;
  parameter_values?: Record<string, any>;
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
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [strategyDetails, setStrategyDetails] = useState<BackendStrategy | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const { toast } = useToast();

  const handleViewDetails = async (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setStrategyDetails(null);

    try {
      const res = await apiClient.get<BackendStrategy>(`/api/v1/strategies/${strategy.id}`);
      setStrategyDetails(res.data);
    } catch (error) {
      console.error("Failed to fetch strategy details", error);
      toast({
        title: "Error",
        description: "Failed to load strategy details",
        variant: "destructive"
      });
    }
  };

  const [newStrategy, setNewStrategy] = useState({
    name: '',
    type: 'CUSTOM',
    description: '',
    code_content: `from src.trading.strategies.base import StrategyBase
import pandas as pd

class CustomStrategy(StrategyBase):
    name = "MyCustomStrategy"
    
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        
    async def on_tick(self, market_data):
        # Your trading logic here
        pass`,
    parameters: '{}'
  });

  const handleCreate = async () => {
    try {
      let parsedParams = {};
      try {
        parsedParams = JSON.parse(newStrategy.parameters);
      } catch (e) {
        toast({
          title: "Invalid Parameters",
          description: "Parameters must be valid JSON",
          variant: "destructive"
        });
        return;
      }

      await apiClient.post('/api/v1/strategies/', {
        name: newStrategy.name,
        strategy_type: newStrategy.type,
        description: newStrategy.description,
        parameters: parsedParams,
        code_content: newStrategy.code_content
      });

      toast({
        title: "Success",
        description: "Strategy created successfully",
      });
      setIsCreateOpen(false);
      window.location.reload();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create strategy",
        variant: "destructive"
      });
    }
  };

  useEffect(() => {
    apiClient.get('/api/v1/strategies')
      .then(res => {
        const data: BackendStrategy[] = res.data;
        const mappedStrategies: Strategy[] = data.map(s => ({
          id: s.id,
          name: s.name,
          type: mapStrategyType(s.strategy_type),
          description: s.description,
          activeBots: s.is_active ? 1 : 0,
          totalTrades: s.total_trades || 0,
          winRate: s.win_rate || 0,
          avgPnl: 0,
          totalPnl: s.total_profit_loss || 0,
          sharpeRatio: 0,
          maxDrawdown: s.max_drawdown || 0,
          profitFactor: 0,
          avgHoldTime: '0h',
          status: s.is_active ? 'active' : 'inactive',
        }));
        setStrategies(mappedStrategies);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch strategies", err);
        setStrategies([]);
        setLoading(false);
      });
  }, []);

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
      <Dialog open={!!selectedStrategy} onOpenChange={(open) => {
        if (!open) {
          setSelectedStrategy(null);
          setStrategyDetails(null);
        }
      }}>
        <DialogContent className="max-w-[800px] max-h-[90vh] overflow-y-auto">
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
            <div className="space-y-6 mt-4">
              {strategyDetails ? (
                <>
                  <div className="space-y-2">
                    <Label>Default Parameters (JSON)</Label>
                    <div className="bg-muted p-4 rounded-md overflow-x-auto">
                      <pre className="text-xs font-mono">
                        {JSON.stringify(strategyDetails.parameter_values || {}, null, 2)}
                      </pre>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Strategy Code</Label>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 gap-1"
                        onClick={() => {
                          navigator.clipboard.writeText(strategyDetails.code_content || '');
                          toast({ description: "Code copied to clipboard" });
                        }}
                      >
                        <Copy className="h-3 w-3" />
                        <span className="text-xs">Copy</span>
                      </Button>
                    </div>
                    <div className="bg-muted p-4 rounded-md overflow-x-auto">
                      <pre className="text-xs font-mono min-h-[300px]">
                        {strategyDetails.code_content || '# No code content available'}
                      </pre>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setSelectedStrategy(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Strategy</DialogTitle>
            <DialogDescription>
              Define a new trading strategy using Python code.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={newStrategy.name}
                  onChange={(e) => setNewStrategy({ ...newStrategy, name: e.target.value })}
                  placeholder="My Strategy"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="type">Type</Label>
                <Select
                  value={newStrategy.type}
                  onValueChange={(val) => setNewStrategy({ ...newStrategy, type: val })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GRID">Grid Trading</SelectItem>
                    <SelectItem value="DCA">DCA</SelectItem>
                    <SelectItem value="TREND_FOLLOWING">Trend Following</SelectItem>
                    <SelectItem value="MEAN_REVERSION">Mean Reversion</SelectItem>
                    <SelectItem value="SCALPING">Scalping</SelectItem>
                    <SelectItem value="ARBITRAGE">Arbitrage</SelectItem>
                    <SelectItem value="CUSTOM">Custom Strategy</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={newStrategy.description}
                onChange={(e) => setNewStrategy({ ...newStrategy, description: e.target.value })}
                placeholder="Describe your strategy logic..."
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="code">Python Code (Hot Reload Supported)</Label>
              <Textarea
                id="code"
                value={newStrategy.code_content}
                onChange={(e) => setNewStrategy({ ...newStrategy, code_content: e.target.value })}
                className="font-mono min-h-[300px] text-xs"
                spellCheck={false}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="parameters">Default Parameters (JSON)</Label>
              <Textarea
                id="parameters"
                value={newStrategy.parameters}
                onChange={(e) => setNewStrategy({ ...newStrategy, parameters: e.target.value })}
                className="font-mono h-[100px]"
                placeholder="{}"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Create Strategy</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Strategy Management</h1>
            <p className="text-muted-foreground">Monitor and manage all trading strategies</p>
          </div>
          <Button onClick={() => setIsCreateOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Create Strategy
          </Button>
        </div>

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
                          onClick={() => handleViewDetails(strategy)}
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

        <div className="grid gap-6 lg:grid-cols-2">
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
