import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/lib/api/client';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Play, Pause, Square, Eye, TrendingUp, TrendingDown, Target, Activity, Clock, Plus, AlertCircle, Search, Trash2, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
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

type BacktestStatus = 'running' | 'paused' | 'completed' | 'error' | 'pending';
type SortField = 'strategy' | 'symbol' | 'netProfit' | 'winRate' | 'status' | 'createdAt' | 'totalTrades' | 'maxDrawdown' | 'initialCapital' | 'leverage' | 'fundingRate' | 'makerFee' | 'takerFee' | 'slippagePercent' | 'exchange';
type SortDirection = 'asc' | 'desc';

interface BacktestItem {
  id: string;
  strategy: string; // Currently mapped from strategy_id manually or just using ID
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  leverage: number;
  fundingRate: number;
  makerFee: number;
  takerFee: number;
  slippagePercent: number;
  // Exchange connection info
  exchangeConnectionId: string;
  exchangeName: string;
  netProfit: number | null;
  netProfitPercent: number | null;
  winRate: number | null;
  maxDrawdown: number | null;
  sharpeRatio: number | null; // Not available in list view typically
  totalTrades: number | null;
  profitFactor: number | null; // Not available in list view typically
  status: BacktestStatus;
  progress: number;
  statusMessage: string | null; // NEW: User-friendly progress message
  createdAt: string;
  // Phase 2-3: New config fields
  signalTimeframe?: string;
  fillPolicy?: string;
}

// ... (keep existing statusConfig and shimmerStyle)

// Status configuration moved to keep file clean
const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  running: { label: 'Running', color: 'border-primary/50 text-primary bg-primary/10', icon: Play },
  pending: { label: 'Pending', color: 'border-yellow-500/50 text-yellow-500', icon: Clock },
  paused: { label: 'Paused', color: 'border-accent/50 text-accent', icon: Pause },
  completed: { label: 'Completed', color: 'border-muted/50 text-muted-foreground', icon: Square },
  error: { label: 'Error', color: 'border-destructive/50 text-destructive', icon: AlertCircle },
  failed: { label: 'Failed', color: 'border-destructive/50 text-destructive', icon: AlertCircle },
  cancelled: { label: 'Cancelled', color: 'border-muted/50 text-muted-foreground', icon: Square }
};

// Add shimmer animation
const shimmerStyle = document.createElement('style');
shimmerStyle.innerHTML = `
@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
`;
document.head.appendChild(shimmerStyle);

export default function Backtest() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [backtests, setBacktests] = useState<BacktestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [strategies, setStrategies] = useState<{ id: string; name: string; }[]>([]);
  const [exchanges, setExchanges] = useState<string[]>([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStrategy, setFilterStrategy] = useState<string>('all');
  const [filterSymbol, setFilterSymbol] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterExchange, setFilterExchange] = useState<string>('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const itemsPerPage = 10;

  // Strategy ID mapping - synced with backend seed_strategies.py
  const STRATEGY_ID_MAP: Record<string, string> = {
    "Grid Trading": "00000000-0000-0000-0000-000000000001",
    "Momentum Strategy": "00000000-0000-0000-0000-000000000002",
    "Mean Reversion": "00000000-0000-0000-0000-000000000003",
    "Arbitrage": "00000000-0000-0000-0000-000000000004",
    "Scalping": "00000000-0000-0000-0000-000000000005"
  };



  const fetchAvailableExchanges = async () => {
    try {
      const res = await apiClient.get('/api/v1/backtests/available-exchanges');
      const data = res.data;

      if (Array.isArray(data)) {
        setExchanges(data);
      }
    } catch (error) {
      console.error('Failed to load exchanges:', error);
      setExchanges([]);
    }
  };


  const fetchStrategies = async () => {
    console.log('[DEBUG] fetchStrategies START');
    try {
      const res = await apiClient.get('/api/v1/strategies');
      console.log('[DEBUG] fetchStrategies response received');

      const data = res.data;
      console.log('[DEBUG] fetchStrategies data:', data);
      if (Array.isArray(data)) {
        console.log('[DEBUG] Setting strategies:', data.length, 'items');
        setStrategies(data);
        console.log('[DEBUG] setStrategies COMPLETED');
      } else {
        console.error('Strategies API returned non-array:', data);
        setStrategies([]);
      }
    } catch (error) {
      console.error('Failed to load strategies:', error);
      setStrategies([]);
    }
    console.log('[DEBUG] fetchStrategies END');
  };

  const fetchBacktests = async () => {
    console.log('[DEBUG] fetchBacktests START');
    try {
      setLoading(true);
      // apiClient handles auth headers and 401s automatically
      const res = await apiClient.get('/api/v1/backtests?limit=100');
      console.log('[DEBUG] fetchBacktests response received');

      const data = res.data;
      console.log('[DEBUG] fetchBacktests data received:', data.backtests?.length, 'items');
      if (!data.backtests || !Array.isArray(data.backtests)) {
        console.error("Invalid backtests data:", data);
        setBacktests([]);
        return;
      }
      console.log('[DEBUG] Mapping backtests...');
      const mapped: BacktestItem[] = data.backtests.map((b: any) => ({
        id: b.id,
        strategy: b.strategy_name || strategies.find(s => s.id === b.strategy_id)?.name || 'Unknown Strategy',
        symbol: b.symbol || 'N/A',
        timeframe: b.timeframe || 'N/A',
        startDate: b.start_date,
        endDate: b.end_date,
        initialCapital: parseFloat(b.initial_capital),
        leverage: b.config?.leverage || 1,
        fundingRate: b.config?.funding_rate_daily !== undefined ? Number(b.config.funding_rate_daily) * 100 : 0.03,
        makerFee: b.config?.maker_fee_rate !== undefined ? Number(b.config.maker_fee_rate) * 100 : 0.02,
        takerFee: b.config?.taker_fee_rate !== undefined ? Number(b.config.taker_fee_rate) * 100 : 0.04,
        slippagePercent: b.config?.slippage_percent !== undefined ? Number(b.config.slippage_percent) * 100 : 0.1,
        exchangeConnectionId: b.exchange_connection_id,
        exchangeName: b.exchange_name || 'Unknown',
        netProfit: b.final_equity ? b.final_equity - b.initial_capital : null,
        netProfitPercent: b.total_return ? b.total_return * 100 : null,
        winRate: b.win_rate != null ? parseFloat(b.win_rate) : null,
        maxDrawdown: b.max_drawdown !== null ? parseFloat(b.max_drawdown) : null,
        sharpeRatio: null,
        totalTrades: b.total_trades,
        profitFactor: null,
        status: b.status.toLowerCase(),
        progress: b.progress_percent,
        statusMessage: b.status_message || null, // NEW: Progress message from backend
        createdAt: b.created_at,
        // Phase 2-3: New fields
        signalTimeframe: b.signal_timeframe || b.config?.signal_timeframe || '1m',
        fillPolicy: b.fill_policy || b.config?.fill_policy || 'optimistic',
      }));
      console.log('[DEBUG] setBacktests with', mapped.length, 'items');
      setBacktests(mapped);
      console.log('[DEBUG] setBacktests COMPLETED');
    } catch (error) {
      console.error('[DEBUG] fetchBacktests ERROR:', error);
      toast({ title: 'Error fetching backtests', variant: 'destructive' });
    } finally {
      setLoading(false);
      console.log('[DEBUG] fetchBacktests END');
    }
  };

  useEffect(() => {
    console.log('[DEBUG] Initial useEffect START');
    fetchBacktests();
    fetchStrategies();
    fetchAvailableExchanges();
    console.log('[DEBUG] Initial fetches triggered');
    // Poll for updates every 5 seconds if there are running backtests
    const interval = setInterval(() => {
      console.log('[DEBUG] Polling interval fired');
      setBacktests(prev => {
        const hasRunning = prev.some(b => b.status === 'running' || b.status === 'pending');
        if (hasRunning) {
          console.log('[DEBUG] Has running backtests, refetching...');
          fetchBacktests();
        }
        return prev;
      });
    }, 5000);
    return () => {
      console.log('[DEBUG] Cleaning up interval');
      clearInterval(interval);
    };
  }, []);

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
  const uniqueStrategies = useMemo(() => [...new Set(backtests.map(b => b.strategy))], [backtests]);
  const symbols = useMemo(() => [...new Set(backtests.map(b => b.symbol))], [backtests]);
  const uniqueExchanges = useMemo(() => [...new Set(backtests.map(b => b.exchangeName).filter(Boolean))], [backtests]);

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
      const matchesExchange = filterExchange === 'all' || bt.exchangeName === filterExchange;
      return matchesSearch && matchesStrategy && matchesSymbol && matchesStatus && matchesExchange;
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
            comparison = (a.netProfit || 0) - (b.netProfit || 0);
            break;
          case 'winRate':
            comparison = (a.winRate || 0) - (b.winRate || 0);
            break;
          case 'initialCapital':
            comparison = (a.initialCapital || 0) - (b.initialCapital || 0);
            break;
          case 'totalTrades':
            comparison = (a.totalTrades || 0) - (b.totalTrades || 0);
            break;
          case 'maxDrawdown':
            comparison = (a.maxDrawdown || 0) - (b.maxDrawdown || 0);
            break;
          case 'status':
            comparison = a.status.localeCompare(b.status);
            break;
          case 'createdAt':
            comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
            break;
          case 'leverage':
            comparison = (a.leverage || 0) - (b.leverage || 0);
            break;
          case 'fundingRate':
            comparison = (a.fundingRate || 0) - (b.fundingRate || 0);
            break;
          case 'makerFee':
            comparison = (a.makerFee || 0) - (b.makerFee || 0);
            break;
          case 'takerFee':
            comparison = (a.takerFee || 0) - (b.takerFee || 0);
            break;
          case 'slippagePercent':
            comparison = (a.slippagePercent || 0) - (b.slippagePercent || 0);
            break;
          case 'exchange':
            comparison = a.exchangeName.localeCompare(b.exchangeName);
            break;
        }
        return sortDirection === 'desc' ? -comparison : comparison;
      });
    }

    return result;
  }, [backtests, searchQuery, filterStrategy, filterSymbol, filterStatus, filterExchange, sortField, sortDirection]);


  // Pagination
  const totalPages = Math.ceil(filteredBacktests.length / itemsPerPage);
  const paginatedBacktests = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredBacktests.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredBacktests, currentPage, itemsPerPage]);

  // Reset page when filters change
  useEffect(() => {
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

  const handleCreateBacktest = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    // Get strategy ID and exchange name from form
    const strategyId = formData.get('strategy') as string;
    const exchangeName = formData.get('exchangeName') as string;

    // Validate strategy is selected
    if (!strategyId || strategyId === '__no_strategies__') {
      toast({ title: 'Please select a Strategy', variant: 'destructive' });
      return;
    }

    // Validate exchange is selected
    if (!exchangeName || exchangeName === '__no_exchanges__') {
      toast({ title: 'Please select an Exchange', variant: 'destructive' });
      return;
    }

    console.log("DEBUG: Strategy UUID =", strategyId);
    console.log("DEBUG: Exchange Name =", exchangeName);


    const payload = {
      strategy_id: strategyId,
      exchange_name: exchangeName,
      config: {
        symbol: formData.get('symbol'),
        timeframe: formData.get('timeframe'),
        // Convert date to datetime format (backend expects ISO datetime)
        start_date: `${formData.get('startDate')}T00:00:00`,
        end_date: `${formData.get('endDate')}T00:00:00`,
        initial_capital: Number(formData.get('initialCapital')),
        leverage: Number(formData.get('leverage')) || 1,
        taker_fee_rate: formData.get('takerFee') ? Number(formData.get('takerFee')) : 0.04,
        maker_fee_rate: formData.get('makerFee') ? Number(formData.get('makerFee')) : 0.02,
        funding_rate_daily: formData.get('fundingRate') ? Number(formData.get('fundingRate')) : 0.03,
        slippage_percent: formData.get('slippagePercent') ? Number(formData.get('slippagePercent')) : 0.1,
        position_sizing: 'percent_equity',
        position_size_percent: 100,
        mode: 'event_driven',
        // Phase 2-3: New config fields
        signal_timeframe: formData.get('signal_timeframe') || '1m',
        fill_policy: formData.get('fill_policy') || 'optimistic',
      }
    };

    console.log("DEBUG: Full payload =", JSON.stringify(payload, null, 2));

    try {
      console.log('Sending backtest request:', payload);

      const res = await apiClient.post('/api/v1/backtests', payload);

      toast({ title: 'Backtest started successfully' });
      setIsCreateOpen(false);

      // Refresh list
      fetchBacktests();
    } catch (error: any) {
      console.error("DEBUG: Catch error =", error);
      toast({ title: error.message || 'Failed to start backtest', variant: 'destructive' });
    }
  };


  const handleStop = async (id: string) => {
    try {
      await apiClient.post(`/api/v1/backtests/${id}/cancel`);

      toast({ title: 'Backtest cancelled' });
      fetchBacktests();
    } catch (error) {
      toast({ title: 'Failed to cancel backtest', variant: 'destructive' });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.delete(`/api/v1/backtests/${id}`);

      toast({ title: 'Backtest deleted' });
      // If deleted item was selected, remove from selection
      if (selectedIds.has(id)) {
        const next = new Set(selectedIds);
        next.delete(id);
        setSelectedIds(next);
      }
      fetchBacktests();
    } catch (error) {
      toast({ title: 'Failed to delete backtest', variant: 'destructive' });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    try {
      await Promise.all(Array.from(selectedIds).map(id =>
        apiClient.delete(`/api/v1/backtests/${id}`)
      ));
      toast({ title: `Deleted ${selectedIds.size} backtest(s)` });
      setSelectedIds(new Set());
      fetchBacktests();
    } catch (error) {
      toast({ title: 'Failed to delete some backtests', variant: 'destructive' });
    }
  };

  const totalBacktests = backtests.length;
  const profitableBacktests = backtests.filter(b => (b.netProfit || 0) > 0).length;
  // Filter for valid numeric win rates (not null, not 0, and is a number)
  const validWinRates = backtests.filter(b => typeof b.winRate === 'number' && b.winRate > 0);
  const avgWinRate = validWinRates.length > 0
    ? validWinRates.reduce((acc, b) => acc + (b.winRate as number), 0) / validWinRates.length
    : 0;

  // Note: Sharpe is not available in list view, so we validly can't show Avg Sharpe here without N+1 queries.
  // We will remove Avg Sharpe card or put placeholder.

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
                  <Select name="strategy" defaultValue={strategies[0]?.id || undefined} >
                    <SelectTrigger>
                      <SelectValue placeholder="Select strategy..." />
                    </SelectTrigger>
                    <SelectContent>
                      {strategies.length === 0 ? (
                        <SelectItem value="__no_strategies__" disabled>No strategies available</SelectItem>
                      ) : (
                        strategies.map(s => (
                          <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>

                </div>

                <div className="space-y-2">
                  <Label>Exchange <span className="text-destructive">*</span></Label>
                  <Select name="exchangeName" defaultValue={exchanges[0] || undefined}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select exchange..." />
                    </SelectTrigger>
                    <SelectContent>
                      {exchanges.length === 0 ? (
                        <SelectItem value="__no_exchanges__" disabled>No exchanges available</SelectItem>
                      ) : (
                        exchanges.map(e => (
                          <SelectItem key={e} value={e}>{e}</SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  {exchanges.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      Please add an exchange connection in Exchange settings first.
                    </p>
                  )}
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Trading Pair</Label>
                    <Input name="symbol" defaultValue="BTC/USDT" placeholder="e.g. BTC/USDT" required />
                  </div>
                  <div className="space-y-2">
                    <Label>Data Resolution</Label>
                    <Input value="1m (Fixed)" disabled className="bg-muted" />
                    <input type="hidden" name="timeframe" value="1m" />
                  </div>
                </div>

                {/* Phase 2-3: Advanced Config */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Signal Timeframe</Label>
                    <Select name="signal_timeframe" defaultValue="1m">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1m">1m (Standard)</SelectItem>
                        <SelectItem value="5m">5m (HTF)</SelectItem>
                        <SelectItem value="15m">15m (HTF)</SelectItem>
                        <SelectItem value="30m">30m (HTF)</SelectItem>
                        <SelectItem value="1h">1h (HTF)</SelectItem>
                        <SelectItem value="4h">4h (HTF)</SelectItem>
                        <SelectItem value="1d">1d (HTF)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Fill Policy</Label>
                    <Select name="fill_policy" defaultValue="optimistic">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="optimistic">Optimistic</SelectItem>
                        <SelectItem value="neutral">Neutral</SelectItem>
                        <SelectItem value="strict">Strict</SelectItem>
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

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Initial Capital ($)</Label>
                    <Input type="number" name="initialCapital" defaultValue="10000" required />
                  </div>
                  <div className="space-y-2">
                    <Label>Leverage (x)</Label>
                    <Input type="number" name="leverage" defaultValue="1" min="1" max="125" required />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Taker Fee (%)</Label>
                    <Input type="number" name="takerFee" defaultValue="0.04" step="0.01" />
                  </div>
                  <div className="space-y-2">
                    <Label>Maker Fee (%)</Label>
                    <Input type="number" name="makerFee" defaultValue="0.02" step="0.01" />
                  </div>
                  <div className="space-y-2">
                    <Label>Funding/Day (%)</Label>
                    <Input type="number" name="fundingRate" defaultValue="0.03" step="0.01" />
                  </div>
                  <div className="space-y-2">
                    <Label>Slippage (%)</Label>
                    <Input type="number" name="slippagePercent" defaultValue="0.1" min="0.1" max="5.0" step="0.1" />
                  </div>
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
        <div className="grid gap-4 md:grid-cols-3">
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
                    <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
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
              <Select value={filterExchange} onValueChange={setFilterExchange}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Exchange" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Exchanges</SelectItem>
                  {uniqueExchanges.map(e => (
                    <SelectItem key={e} value={e}>{e}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Bulk Actions */}
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2 pt-3">
                <span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>
                <Button variant="outline" size="sm" onClick={handleBulkDelete} className="gap-1 text-destructive hover:text-destructive">
                  <Trash2 className="h-3 w-3" />
                  Delete
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
                    <TableHead>
                      <button
                        onClick={() => handleSort('exchange')}
                        className="flex items-center hover:text-foreground transition-colors"
                      >
                        Exchange <SortIcon field="exchange" />
                      </button>
                    </TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('initialCapital')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Initial Capital ($) <SortIcon field="initialCapital" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('leverage')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Leverage <SortIcon field="leverage" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('fundingRate')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Funding <SortIcon field="fundingRate" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('makerFee')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Maker <SortIcon field="makerFee" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('takerFee')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Taker <SortIcon field="takerFee" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('slippagePercent')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Slippage <SortIcon field="slippagePercent" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button
                        onClick={() => handleSort('totalTrades')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Trades <SortIcon field="totalTrades" />
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
                        onClick={() => handleSort('maxDrawdown')}
                        className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                      >
                        Max DD <SortIcon field="maxDrawdown" />
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
                    <TableHead>
                      <button
                        onClick={() => handleSort('status')}
                        className="flex items-center hover:text-foreground transition-colors"
                      >
                        Status <SortIcon field="status" />
                      </button>
                    </TableHead>
                    <TableHead>
                      <button
                        onClick={() => handleSort('createdAt')}
                        className="flex items-center hover:text-foreground transition-colors"
                      >
                        Created At <SortIcon field="createdAt" />
                      </button>
                    </TableHead>
                    <TableHead className="text-center">Actions</TableHead>
                  </TableRow>

                </TableHeader>
                <TableBody>
                  {paginatedBacktests.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center h-24 text-muted-foreground">
                        No backtests found. Create one to get started.
                      </TableCell>
                    </TableRow>
                  ) : paginatedBacktests.map((backtest) => {
                    const isProfit = (backtest.netProfit || 0) >= 0;
                    const config = statusConfig[backtest.status] || statusConfig['pending'];
                    const Icon = config.icon;
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
                            <p className="text-xs text-muted-foreground">{backtest.signalTimeframe || backtest.timeframe}</p>
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-sm">{backtest.symbol}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="font-normal">
                            {backtest.exchangeName || 'Unknown'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{backtest.startDate} - {backtest.endDate}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ${backtest.initialCapital.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.leverage}x
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.fundingRate}%
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.makerFee}%
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.takerFee}%
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.slippagePercent}%
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.totalTrades ?? '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {backtest.netProfit !== null ? (
                              <>
                                {isProfit ? (
                                  <TrendingUp className="h-3 w-3 text-primary" />
                                ) : (
                                  <TrendingDown className="h-3 w-3 text-destructive" />
                                )}
                                <span className={cn("font-mono font-medium", isProfit ? "text-primary" : "text-destructive")}>
                                  {isProfit ? '+' : ''}${backtest.netProfit.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                                </span>
                              </>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </div>
                          {backtest.netProfitPercent != null && (
                            <p className={cn("text-xs", isProfit ? "text-primary/70" : "text-destructive/70")}>
                              {isProfit ? '+' : ''}{Number(backtest.netProfitPercent).toFixed(2)}%
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono text-destructive">
                          {backtest.maxDrawdown !== null ? `${backtest.maxDrawdown.toFixed(2)}%` : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {backtest.winRate != null ? `${Number(backtest.winRate).toFixed(1)}%` : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={config.color}>
                              <Icon className="mr-1 h-3 w-3" />
                              {config.label}
                            </Badge>
                            {backtest.status === 'running' && (
                              <div className="flex flex-col gap-1 w-full max-w-[140px]">
                                <div className="flex items-center gap-2">
                                  <div className="relative w-20 h-2 bg-secondary rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-primary transition-all duration-500 ease-out relative overflow-hidden"
                                      style={{ width: `${Math.max(backtest.progress || 0, 5)}%` }} // Minimum 5% visible
                                    >
                                      <div className="absolute inset-0 bg-white/30 w-full h-full animate-[shimmer_2s_infinite] -skew-x-12" style={{ transform: 'translateX(-100%)' }}></div>
                                    </div>
                                  </div>
                                  <span className="text-xs font-mono text-muted-foreground">{backtest.progress}%</span>
                                </div>
                                <span className="text-[10px] text-muted-foreground/80 truncate w-full" title={backtest.statusMessage || "Processing..."}>
                                  {backtest.statusMessage || (backtest.progress === 0 ? "Initializing..." : "Running...")}
                                </span>
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                          {new Date(backtest.createdAt).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-center gap-1">
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
                            {/* Delete button - always available for any status */}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(backtest.id)}
                              className="h-8 w-8 text-destructive hover:text-destructive"
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
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
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
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
