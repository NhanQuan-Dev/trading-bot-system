import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { LineChart, Play, Pause, Square, RefreshCw, Eye, TrendingUp, TrendingDown, Target, Activity, Clock, Plus, AlertCircle, Search, RotateCcw, Trash2, Download, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

type BacktestStatus = 'running' | 'paused' | 'completed' | 'error';
type SortField = 'strategy' | 'symbol' | 'netProfit' | 'winRate' | 'sharpeRatio' | 'status' | 'createdAt';
type SortDirection = 'asc' | 'desc';

interface BacktestItem {
  id: string;
  strategy: string;
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  netProfit: number;
  netProfitPercent: number;
  winRate: number;
  maxDrawdown: number;
  sharpeRatio: number;
  totalTrades: number;
  profitFactor: number;
  status: BacktestStatus;
  progress: number;
  createdAt: string;
}

const statusConfig = {
  running: { label: 'Running', color: 'border-primary/50 text-primary', icon: Play },
  paused: { label: 'Paused', color: 'border-accent/50 text-accent', icon: Pause },
  completed: { label: 'Completed', color: 'border-muted/50 text-muted-foreground', icon: Square },
  error: { label: 'Error', color: 'border-destructive/50 text-destructive', icon: AlertCircle }
};

// Mock backtest history data
const initialBacktestHistory: BacktestItem[] = [
  { 
    id: 'bt-001', 
    strategy: 'Grid Trading', 
    symbol: 'BTC/USDT', 
    timeframe: '1h',
    startDate: '2024-01-01', 
    endDate: '2024-02-01', 
    initialCapital: 10000,
    netProfit: 2845, 
    netProfitPercent: 28.45,
    winRate: 67.5, 
    maxDrawdown: -8.2,
    sharpeRatio: 1.92,
    totalTrades: 234,
    profitFactor: 2.1,
    status: 'completed',
    progress: 100,
    createdAt: '2024-02-01 14:30:00'
  },
  { 
    id: 'bt-002', 
    strategy: 'DCA', 
    symbol: 'ETH/USDT', 
    timeframe: '4h',
    startDate: '2024-01-15', 
    endDate: '2024-02-15', 
    initialCapital: 5000,
    netProfit: -320, 
    netProfitPercent: -6.4,
    winRate: 42.3, 
    maxDrawdown: -15.5,
    sharpeRatio: 0.85,
    totalTrades: 156,
    profitFactor: 0.87,
    status: 'running',
    progress: 65,
    createdAt: '2024-02-15 10:15:00'
  },
  { 
    id: 'bt-003', 
    strategy: 'Trend Following', 
    symbol: 'SOL/USDT', 
    timeframe: '1d',
    startDate: '2024-02-01', 
    endDate: '2024-03-01', 
    initialCapital: 15000,
    netProfit: 4250, 
    netProfitPercent: 28.33,
    winRate: 58.2, 
    maxDrawdown: -12.1,
    sharpeRatio: 1.65,
    totalTrades: 89,
    profitFactor: 1.85,
    status: 'paused',
    progress: 45,
    createdAt: '2024-03-01 09:00:00'
  },
  { 
    id: 'bt-004', 
    strategy: 'Mean Reversion', 
    symbol: 'BTC/USDT', 
    timeframe: '15m',
    startDate: '2024-02-10', 
    endDate: '2024-02-20', 
    initialCapital: 8000,
    netProfit: 1120, 
    netProfitPercent: 14.0,
    winRate: 72.1, 
    maxDrawdown: -5.8,
    sharpeRatio: 2.15,
    totalTrades: 412,
    profitFactor: 2.45,
    status: 'error',
    progress: 30,
    createdAt: '2024-02-20 16:45:00'
  },
];

export default function Backtest() {
  const navigate = useNavigate();
  const [backtests, setBacktests] = useState<BacktestItem[]>(initialBacktestHistory);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStrategy, setFilterStrategy] = useState<string>('all');
  const [filterSymbol, setFilterSymbol] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const itemsPerPage = 10;
  const { toast } = useToast();

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortDirection === 'desc') {
        setSortDirection('asc');
      } else {
        setSortField(null);
        setSortDirection('desc');
      }
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    return sortDirection === 'desc' 
      ? <ArrowDown className="h-3 w-3 ml-1" /> 
      : <ArrowUp className="h-3 w-3 ml-1" />;
  };

  // Get unique strategies and symbols for filters
  const strategies = useMemo(() => [...new Set(backtests.map(b => b.strategy))], [backtests]);
  const symbols = useMemo(() => [...new Set(backtests.map(b => b.symbol))], [backtests]);

  // Filtered and sorted backtests
  const filteredBacktests = useMemo(() => {
    let result = backtests.filter(bt => {
      const matchesSearch = searchQuery === '' || 
        bt.strategy.toLowerCase().includes(searchQuery.toLowerCase()) ||
        bt.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        bt.id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStrategy = filterStrategy === 'all' || bt.strategy === filterStrategy;
      const matchesSymbol = filterSymbol === 'all' || bt.symbol === filterSymbol;
      const matchesStatus = filterStatus === 'all' || bt.status === filterStatus;
      return matchesSearch && matchesStrategy && matchesSymbol && matchesStatus;
    });

    // Apply sorting
    if (sortField) {
      result = [...result].sort((a, b) => {
        let comparison = 0;
        switch (sortField) {
          case 'strategy':
            comparison = a.strategy.localeCompare(b.strategy);
            break;
          case 'symbol':
            comparison = a.symbol.localeCompare(b.symbol);
            break;
          case 'netProfit':
            comparison = a.netProfit - b.netProfit;
            break;
          case 'winRate':
            comparison = a.winRate - b.winRate;
            break;
          case 'sharpeRatio':
            comparison = a.sharpeRatio - b.sharpeRatio;
            break;
          case 'status':
            comparison = a.status.localeCompare(b.status);
            break;
          case 'createdAt':
            comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
            break;
        }
        return sortDirection === 'desc' ? -comparison : comparison;
      });
    }

    return result;
  }, [backtests, searchQuery, filterStrategy, filterSymbol, filterStatus, sortField, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(filteredBacktests.length / itemsPerPage);
  const paginatedBacktests = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredBacktests.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredBacktests, currentPage, itemsPerPage]);

  // Reset page when filters change
  useMemo(() => {
    setCurrentPage(1);
  }, [searchQuery, filterStrategy, filterSymbol, filterStatus]);

  // Selection helpers
  const isAllSelected = paginatedBacktests.length > 0 && paginatedBacktests.every(bt => selectedIds.has(bt.id));
  const isSomeSelected = paginatedBacktests.some(bt => selectedIds.has(bt.id));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedBacktests.map(bt => bt.id)));
    }
  };

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleStart = (id: string) => {
    setBacktests(prev => prev.map(bt => 
      bt.id === id ? { ...bt, status: 'running' as BacktestStatus } : bt
    ));
    toast({ title: 'Backtest started' });
  };

  const handlePause = (id: string) => {
    setBacktests(prev => prev.map(bt => 
      bt.id === id ? { ...bt, status: 'paused' as BacktestStatus } : bt
    ));
    toast({ title: 'Backtest paused' });
  };

  const handleStop = (id: string) => {
    setBacktests(prev => prev.map(bt => 
      bt.id === id ? { ...bt, status: 'completed' as BacktestStatus, progress: 100 } : bt
    ));
    toast({ title: 'Backtest stopped' });
  };

  const handleRetry = (id: string) => {
    setBacktests(prev => prev.map(bt => 
      bt.id === id ? { ...bt, status: 'running' as BacktestStatus, progress: 0 } : bt
    ));
    toast({ title: 'Backtest restarted' });
  };

  // Bulk actions
  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    setBacktests(prev => prev.filter(bt => !selectedIds.has(bt.id)));
    toast({ title: `Deleted ${selectedIds.size} backtest(s)` });
    setSelectedIds(new Set());
  };

  const handleBulkRestart = () => {
    if (selectedIds.size === 0) return;
    setBacktests(prev => prev.map(bt => 
      selectedIds.has(bt.id) ? { ...bt, status: 'running' as BacktestStatus, progress: 0 } : bt
    ));
    toast({ title: `Restarted ${selectedIds.size} backtest(s)` });
    setSelectedIds(new Set());
  };

  const handleExportCSV = () => {
    const dataToExport = selectedIds.size > 0 
      ? backtests.filter(bt => selectedIds.has(bt.id))
      : filteredBacktests;
    
    const headers = ['ID', 'Strategy', 'Symbol', 'Timeframe', 'Start Date', 'End Date', 'Initial Capital', 'Net Profit', 'Net Profit %', 'Win Rate', 'Max Drawdown', 'Sharpe Ratio', 'Total Trades', 'Profit Factor', 'Status', 'Progress', 'Created At'];
    const csvRows = [
      headers.join(','),
      ...dataToExport.map(bt => [
        bt.id,
        bt.strategy,
        bt.symbol,
        bt.timeframe,
        bt.startDate,
        bt.endDate,
        bt.initialCapital,
        bt.netProfit,
        bt.netProfitPercent,
        bt.winRate,
        bt.maxDrawdown,
        bt.sharpeRatio,
        bt.totalTrades,
        bt.profitFactor,
        bt.status,
        bt.progress,
        bt.createdAt
      ].join(','))
    ];
    
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backtest-results-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast({ title: `Exported ${dataToExport.length} backtest(s) to CSV` });
  };

  const handleCreateBacktest = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const newBacktest: BacktestItem = {
      id: `bt-${Date.now()}`,
      strategy: formData.get('strategy') as string,
      symbol: formData.get('symbol') as string,
      timeframe: formData.get('timeframe') as string,
      startDate: formData.get('startDate') as string,
      endDate: formData.get('endDate') as string,
      initialCapital: Number(formData.get('initialCapital')),
      netProfit: 0,
      netProfitPercent: 0,
      winRate: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
      totalTrades: 0,
      profitFactor: 0,
      status: 'running',
      progress: 0,
      createdAt: new Date().toISOString()
    };
    setBacktests(prev => [newBacktest, ...prev]);
    setIsCreateOpen(false);
    toast({ title: 'Backtest created and started!' });
  };

  // Summary metrics
  const totalBacktests = backtests.length;
  const profitableBacktests = backtests.filter(b => b.netProfit > 0).length;
  const avgWinRate = backtests.reduce((acc, b) => acc + b.winRate, 0) / totalBacktests;
  const avgSharpe = backtests.reduce((acc, b) => acc + b.sharpeRatio, 0) / totalBacktests;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Backtest Engine</h1>
            <p className="text-muted-foreground">Test and optimize your trading strategies with historical data</p>
          </div>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Create Backtest
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>New Backtest</DialogTitle>
                <DialogDescription>
                  Set up your strategy parameters for backtesting.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateBacktest} className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>Strategy</Label>
                  <Select name="strategy" defaultValue="Grid Trading">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Grid Trading">Grid Trading</SelectItem>
                      <SelectItem value="DCA">DCA</SelectItem>
                      <SelectItem value="Trend Following">Trend Following</SelectItem>
                      <SelectItem value="Mean Reversion">Mean Reversion</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Trading Pair</Label>
                    <Select name="symbol" defaultValue="BTC/USDT">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BTC/USDT">BTC/USDT</SelectItem>
                        <SelectItem value="ETH/USDT">ETH/USDT</SelectItem>
                        <SelectItem value="SOL/USDT">SOL/USDT</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Timeframe</Label>
                    <Select name="timeframe" defaultValue="1h">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15m">15 Minutes</SelectItem>
                        <SelectItem value="1h">1 Hour</SelectItem>
                        <SelectItem value="4h">4 Hours</SelectItem>
                        <SelectItem value="1d">1 Day</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Start Date</Label>
                    <Input type="date" name="startDate" defaultValue="2024-01-01" required />
                  </div>
                  <div className="space-y-2">
                    <Label>End Date</Label>
                    <Input type="date" name="endDate" defaultValue="2024-03-01" required />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Initial Capital ($)</Label>
                  <Input type="number" name="initialCapital" defaultValue="10000" required />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)} className="flex-1">
                    Cancel
                  </Button>
                  <Button type="submit" className="flex-1 gap-2">
                    <Play className="h-4 w-4" />
                    Run Backtest
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Total Backtests</p>
              </div>
              <p className="mt-1 text-2xl font-bold text-foreground">{totalBacktests}</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Profitable</p>
              </div>
              <p className="mt-1 text-2xl font-bold text-primary">{profitableBacktests}/{totalBacktests}</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Avg Win Rate</p>
              </div>
              <p className="mt-1 text-2xl font-bold text-foreground">{avgWinRate.toFixed(1)}%</p>
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <LineChart className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Avg Sharpe</p>
              </div>
              <p className="mt-1 text-2xl font-bold text-foreground">{avgSharpe.toFixed(2)}</p>
            </CardContent>
          </Card>
        </div>

        {/* Backtest History Table */}
        <Card className="border-border bg-card">
          <CardHeader>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Backtest History</CardTitle>
                <CardDescription>View and analyze your previous backtests</CardDescription>
              </div>
            </div>
            {/* Search and Filters */}
            <div className="flex flex-wrap gap-3 pt-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by strategy, symbol, or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={filterStrategy} onValueChange={setFilterStrategy}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Strategy" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Strategies</SelectItem>
                  {strategies.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterSymbol} onValueChange={setFilterSymbol}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Symbol" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Symbols</SelectItem>
                  {symbols.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="paused">Paused</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* Bulk Actions */}
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2 pt-3">
                <span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>
                <Button variant="outline" size="sm" onClick={handleBulkRestart} className="gap-1">
                  <RotateCcw className="h-3 w-3" />
                  Restart
                </Button>
                <Button variant="outline" size="sm" onClick={handleBulkDelete} className="gap-1 text-destructive hover:text-destructive">
                  <Trash2 className="h-3 w-3" />
                  Delete
                </Button>
                <Button variant="outline" size="sm" onClick={handleExportCSV} className="gap-1">
                  <Download className="h-3 w-3" />
                  Export CSV
                </Button>
              </div>
            )}
            {selectedIds.size === 0 && (
              <div className="flex items-center gap-2 pt-3">
                <Button variant="outline" size="sm" onClick={handleExportCSV} className="gap-1">
                  <Download className="h-3 w-3" />
                  Export All to CSV
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="w-[40px]">
                      <Checkbox 
                        checked={isAllSelected}
                        onCheckedChange={toggleSelectAll}
                        aria-label="Select all"
                        className={isSomeSelected && !isAllSelected ? "opacity-50" : ""}
                      />
                    </TableHead>
                    <TableHead>
                      <button 
                        onClick={() => handleSort('strategy')} 
                        className="flex items-center hover:text-foreground transition-colors"
                      >
                        Strategy <SortIcon field="strategy" />
                      </button>
                    </TableHead>
                    <TableHead>
                      <button 
                        onClick={() => handleSort('symbol')} 
                        className="flex items-center hover:text-foreground transition-colors"
                      >
                        Symbol <SortIcon field="symbol" />
                      </button>
                    </TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>
                      <button 
                        onClick={() => handleSort('status')} 
                        className="flex items-center hover:text-foreground transition-colors"
                      >
                        Status <SortIcon field="status" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button 
                        onClick={() => handleSort('netProfit')} 
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Net P&L <SortIcon field="netProfit" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button 
                        onClick={() => handleSort('winRate')} 
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Win Rate <SortIcon field="winRate" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button 
                        onClick={() => handleSort('sharpeRatio')} 
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Sharpe <SortIcon field="sharpeRatio" />
                      </button>
                    </TableHead>
                    <TableHead className="text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedBacktests.map((backtest) => {
                    const isProfit = backtest.netProfit >= 0;
                    const config = statusConfig[backtest.status];
                    return (
                      <TableRow key={backtest.id} className="border-border">
                        <TableCell>
                          <Checkbox 
                            checked={selectedIds.has(backtest.id)}
                            onCheckedChange={() => toggleSelect(backtest.id)}
                            aria-label={`Select ${backtest.id}`}
                          />
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium text-foreground">{backtest.strategy}</p>
                            <p className="text-xs text-muted-foreground">{backtest.timeframe}</p>
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-sm">{backtest.symbol}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{backtest.startDate} - {backtest.endDate}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={config.color}>
                              {config.label}
                            </Badge>
                            {backtest.status === 'running' && (
                              <div className="flex items-center gap-1">
                                <Progress value={backtest.progress} className="h-1 w-16" />
                                <span className="text-xs text-muted-foreground">{backtest.progress}%</span>
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {isProfit ? (
                              <TrendingUp className="h-3 w-3 text-primary" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-destructive" />
                            )}
                            <span className={cn("font-mono font-medium", isProfit ? "text-primary" : "text-destructive")}>
                              {isProfit ? '+' : ''}${backtest.netProfit.toLocaleString()}
                            </span>
                          </div>
                          <p className={cn("text-xs", isProfit ? "text-primary/70" : "text-destructive/70")}>
                            {isProfit ? '+' : ''}{backtest.netProfitPercent.toFixed(2)}%
                          </p>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.winRate.toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.sharpeRatio.toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-center gap-1">
                            {backtest.status === 'running' ? (
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => handlePause(backtest.id)}
                                className="h-8 w-8"
                                title="Pause"
                              >
                                <Pause className="h-4 w-4" />
                              </Button>
                            ) : backtest.status === 'paused' ? (
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => handleStart(backtest.id)}
                                className="h-8 w-8"
                                title="Resume"
                              >
                                <Play className="h-4 w-4" />
                              </Button>
                            ) : null}
                            {(backtest.status === 'running' || backtest.status === 'paused') && (
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => handleStop(backtest.id)}
                                className="h-8 w-8"
                                title="Stop"
                              >
                                <Square className="h-4 w-4" />
                              </Button>
                            )}
                            {backtest.status === 'error' && (
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => handleRetry(backtest.id)}
                                className="h-8 w-8 text-accent"
                                title="Retry"
                              >
                                <RotateCcw className="h-4 w-4" />
                              </Button>
                            )}
                            <Button 
                              variant="ghost" 
                              size="icon"
                              onClick={() => navigate(`/backtest/${backtest.id}`)}
                              className="h-8 w-8"
                              title="View Details"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-border px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  Showing {((currentPage - 1) * itemsPerPage) + 1}-{Math.min(currentPage * itemsPerPage, filteredBacktests.length)} of {filteredBacktests.length}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                      <Button
                        key={page}
                        variant={currentPage === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                        className="h-8 w-8 p-0"
                      >
                        {page}
                      </Button>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
