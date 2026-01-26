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
import { Play, Pause, Square, Eye, TrendingUp, TrendingDown, Target, Activity, Clock, Plus, AlertCircle, Search, Trash2, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown, HelpCircle, Settings2 } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
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
type SortField = 'strategy' | 'symbol' | 'netProfit' | 'winRate' | 'status' | 'createdAt' | 'totalTrades' | 'maxDrawdown' | 'initialCapital' | 'leverage' | 'fundingRate' | 'makerFee' | 'takerFee' | 'slippagePercent' | 'exchange' | 'marketFillPolicy' | 'limitFillPolicy' | 'pricePathAssumption';
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
  marketFillPolicy?: string;
  limitFillPolicy?: string;
  pricePathAssumption?: string;
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
  const [strategies, setStrategies] = useState<{ id: string; name: string; required_timeframes?: string[] }[]>([]);
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
  // Phase 2-3: Form state for Radix Select components (they don't sync with formData)
  const [formSignalTimeframe, setFormSignalTimeframe] = useState('1m');
  const [formFillPolicy, setFormFillPolicy] = useState('optimistic');
  const [formMarketFillPolicy, setFormMarketFillPolicy] = useState('close');
  const [formLimitFillPolicy, setFormLimitFillPolicy] = useState('cross');
  const [formPricePathAssumption, setFormPricePathAssumption] = useState('neutral');
  const [formStrategyId, setFormStrategyId] = useState<string>('');
  const [formExchangeName, setFormExchangeName] = useState('');
  const [formSymbol, setFormSymbol] = useState('BTC/USDT');
  const [formInitialCapital, setFormInitialCapital] = useState('10000');
  const [formStartDate, setFormStartDate] = useState('2024-01-01');
  const [formEndDate, setFormEndDate] = useState('2024-12-31');
  const [formLeverage, setFormLeverage] = useState('20');
  const [formExecutionDelayBars, setFormExecutionDelayBars] = useState('0');
  const [formSlippagePercent, setFormSlippagePercent] = useState('0.1');
  const [formTakerFee, setFormTakerFee] = useState('0.04');

  const [formMakerFee, setFormMakerFee] = useState('0.02');
  const [formFundingRate, setFormFundingRate] = useState('0.03');
  // Phase 2: Condition Timeframes
  const [formConditionTimeframes, setFormConditionTimeframes] = useState<string[]>([]);
  const [showAdvancedColumns, setShowAdvancedColumns] = useState(false);
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


  // Reset form state when dialog opens
  useEffect(() => {
    if (isCreateOpen) {
      setFormSignalTimeframe('1m');
      setFormFillPolicy('optimistic');
      setFormMarketFillPolicy('close');
      setFormLimitFillPolicy('cross');
      setFormPricePathAssumption('neutral');
      setFormExchangeName(exchanges[0] || '');
      setFormSymbol('BTC/USDT');
      setFormInitialCapital('10000');
      setFormStartDate('2024-01-01');
      setFormEndDate('2024-12-31');
      setFormLeverage('20');
      setFormExecutionDelayBars('0');
      setFormSlippagePercent('0.1');
      setFormTakerFee('0.04');
      setFormMakerFee('0.02');
      setFormFundingRate('0.03');
      setFormConditionTimeframes([]);
    }
  }, [isCreateOpen]);

  // Handle Strategy Selection Changes
  // Also re-run when dialog opens (isCreateOpen) to handle re-opening with same strategy selected
  useEffect(() => {
    if (!isCreateOpen) return; // Only run when dialog is open

    const selectedStrategy = strategies.find(s => s.id === formStrategyId);
    if (selectedStrategy?.required_timeframes && selectedStrategy.required_timeframes.length > 0) {
      // Multi-Timeframe: Auto-select required TFs
      setFormConditionTimeframes(selectedStrategy.required_timeframes);
    } else {
      // Single Timeframe: Reset
      setFormConditionTimeframes([]);
    }
  }, [formStrategyId, strategies, isCreateOpen]);

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
        marketFillPolicy: b.market_fill_policy || b.config?.market_fill_policy || 'close',
        limitFillPolicy: b.limit_fill_policy || b.config?.limit_fill_policy || 'cross',
        pricePathAssumption: b.price_path_assumption || b.config?.price_path_assumption || 'neutral',
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
    const strategyId = formStrategyId;
    const exchangeName = formExchangeName;

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
        symbol: formSymbol,
        timeframe: '1m',
        // Convert date to datetime format (backend expects ISO datetime)
        start_date: `${formStartDate}T00:00:00`,
        end_date: `${formEndDate}T23:59:59`,
        initial_capital: Number(formInitialCapital),
        leverage: Number(formLeverage) || 1,
        taker_fee_rate: formTakerFee ? Number(formTakerFee) : 0.04,
        maker_fee_rate: formMakerFee ? Number(formMakerFee) : 0.02,
        funding_rate_daily: formFundingRate ? Number(formFundingRate) : 0.03,
        slippage_percent: formSlippagePercent ? Number(formSlippagePercent) : 0.1,
        position_sizing: 'percent_equity',
        position_size_percent: 100,
        mode: 'event_driven',
        // Phase 2-3: New config fields (now all controlled)
        signal_timeframe: formSignalTimeframe,
        market_fill_policy: formMarketFillPolicy,
        limit_fill_policy: formLimitFillPolicy,
        price_path_assumption: formPricePathAssumption,
        execution_delay_bars: Number(formExecutionDelayBars) || 0,
        condition_timeframes: formConditionTimeframes.length > 0 ? formConditionTimeframes : undefined,
      }
    };

    console.log("DEBUG: Full payload =", JSON.stringify(payload, null, 2));

    // Optimistic UI: Close dialog immediately for responsiveness
    setIsCreateOpen(false);

    // Fire-and-forget API call - don't await
    apiClient.post('/api/v1/backtests', payload)
      .then(() => {
        toast({ title: 'Backtest started successfully' });
        fetchBacktests(); // Refresh to get real data
      })
      .catch((error: any) => {
        console.error("DEBUG: Catch error =", error);
        toast({ title: error.message || 'Failed to start backtest', variant: 'destructive' });
        fetchBacktests(); // Refresh in case of error too
      });
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
            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>New Backtest</DialogTitle>
                <DialogDescription>
                  Set up your strategy parameters for backtesting.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateBacktest} className="space-y-4">
                <Tabs defaultValue="general" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="general">General</TabsTrigger>
                    <TabsTrigger value="execution">Execution</TabsTrigger>
                    <TabsTrigger value="simulation">Simulation</TabsTrigger>
                    <TabsTrigger value="fees">Fees</TabsTrigger>
                  </TabsList>

                  <TabsContent value="general" className="space-y-4 pt-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Strategy <span className="text-destructive">*</span></Label>
                        <Select name="strategyId" value={formStrategyId} onValueChange={setFormStrategyId}>
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
                        <Select name="exchangeName" value={formExchangeName} onValueChange={setFormExchangeName}>
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
                      </div>
                    </div>

                    {exchanges.length === 0 && (
                      <p className="text-xs text-muted-foreground">
                        Please add an exchange connection in Exchange settings first.
                      </p>
                    )}

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Trading Pair</Label>
                        <Input name="symbol" value={formSymbol} onChange={(e) => setFormSymbol(e.target.value)} placeholder="e.g. BTC/USDT" required />
                      </div>
                      <div className="space-y-2">
                        <Label>Initial Capital ($)</Label>
                        <Input type="number" name="initialCapital" value={formInitialCapital} onChange={(e) => setFormInitialCapital(e.target.value)} required />
                      </div>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Start Date</Label>
                        <Input type="date" name="startDate" value={formStartDate} onChange={(e) => setFormStartDate(e.target.value)} required />
                      </div>
                      <div className="space-y-2">
                        <Label>End Date</Label>
                        <Input type="date" name="endDate" value={formEndDate} onChange={(e) => setFormEndDate(e.target.value)} required />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Leverage (x)</Label>
                      <Input type="number" name="leverage" value={formLeverage} onChange={(e) => setFormLeverage(e.target.value)} min="1" max="125" required />
                    </div>
                  </TabsContent>

                  <TabsContent value="execution" className="space-y-4 pt-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Signal Timeframe</Label>
                        <Select value={formSignalTimeframe} onValueChange={setFormSignalTimeframe}>
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
                        <Label>Data Resolution</Label>
                        <Input value="1m (Fixed)" disabled className="bg-muted text-xs h-9" />
                        <input type="hidden" name="timeframe" value="1m" />
                      </div>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5">
                          <Label>Execution Delay (bars)</Label>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground hover:text-foreground transition-colors" />
                            </TooltipTrigger>
                            <TooltipContent side="right" className="max-w-[300px] text-xs">
                              <p>
                                Execution Delay mô phỏng độ trễ thực tế từ khi có tín hiệu đến khi lệnh được khớp trên sàn (do độ trễ mạng, xử lý API).
                              </p>
                              <p className="mt-1">
                                Việc cài đặt độ trễ giúp kết quả backtest sát với thực tế hơn, tránh kỳ vọng quá cao vào các chiến thuật nhạy cảm với thời gian.
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <Input type="number" name="executionDelayBars" value={formExecutionDelayBars} onChange={(e) => setFormExecutionDelayBars(e.target.value)} min="0" step="1" />
                      </div>
                      <div className="space-y-2">
                        <Label>Slippage (%)</Label>
                        <Input type="number" name="slippagePercent" value={formSlippagePercent} onChange={(e) => setFormSlippagePercent(e.target.value)} min="0.0" max="5.0" step="0.1" />
                      </div>
                    </div>

                    {/* Condition Timeframes - Only show for Multi-Timeframe strategies (or if manual selection allowed) */
                      /* User Rule: "Single Timeframe... hiển thị như cũ... không có check timeframe checkbox" */
                      /* User Rule: "Multi Timeframe... auto tick check toàn bộ... không cho người dùng thay đổi" */
                      (() => {
                        const selectedStrat = strategies.find(s => s.id === formStrategyId);
                        const isMultiTimeframe = selectedStrat?.required_timeframes && selectedStrat.required_timeframes.length > 0;

                        if (!isMultiTimeframe) return null;

                        return (
                          <div className="space-y-3 pt-2">
                            <div className="flex items-center gap-1.5">
                              <Label>Condition Timeframes (Required by Strategy)</Label>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground hover:text-foreground transition-colors" />
                                </TooltipTrigger>
                                <TooltipContent side="right" className="max-w-[300px] text-xs">
                                  These timeframes are required by the selected strategy logic.
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <div className="flex flex-wrap gap-4 border rounded-md p-3 bg-muted/20 opacity-80 cursor-not-allowed">
                              {['5m', '15m', '30m', '1h', '4h', '1d'].map((tf) => (
                                <div key={tf} className="flex items-center space-x-2">
                                  <Checkbox
                                    id={`ctf-${tf}`}
                                    checked={formConditionTimeframes.includes(tf)}
                                    disabled={true} // Always disabled as per requirement
                                  />
                                  <Label htmlFor={`ctf-${tf}`} className="text-sm font-normal cursor-not-allowed">{tf}</Label>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })()}
                  </TabsContent>

                  <TabsContent value="simulation" className="space-y-4 pt-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5">
                          <Label>Market Fill Price</Label>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground hover:text-foreground transition-colors" />
                            </TooltipTrigger>
                            <TooltipContent side="right" className="max-w-[350px] text-xs">
                              <p className="font-semibold mb-1">Giá khớp lệnh thị trường (Market):</p>
                              <p>Chọn mức giá giả định để khớp các lệnh Market (hoặc entry tín hiệu):</p>
                              <ul className="list-disc pl-4 mt-1 space-y-1">
                                <li><strong>Close:</strong> Khớp tại giá đóng cửa của nến (Standard).</li>
                                <li><strong>Low:</strong> Khớp tại giá thấp nhất (Lạc quan cho lệnh Buy).</li>
                                <li><strong>High:</strong> Khớp tại giá cao nhất (Bi quan cho lệnh Buy).</li>
                              </ul>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <Select value={formMarketFillPolicy} onValueChange={setFormMarketFillPolicy}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="close">Close (Standard)</SelectItem>
                            <SelectItem value="low">Low Price</SelectItem>
                            <SelectItem value="high">High Price</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5">
                          <Label>Limit Fill Condition</Label>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground hover:text-foreground transition-colors" />
                            </TooltipTrigger>
                            <TooltipContent side="right" className="max-w-[350px] text-xs">
                              <p className="font-semibold mb-1">Điều kiện khớp lệnh giới hạn (Limit):</p>
                              <p>Quyết định khi nào một lệnh Limit/TP/SL được coi là đã khớp:</p>
                              <ul className="list-disc pl-4 mt-1 space-y-1">
                                <li><strong>Touch:</strong> Khớp ngay khi giá chạm mức Limit.</li>
                                <li><strong>Cross:</strong> Chỉ khớp khi giá thực sự vượt qua mức Limit (Thực tế hơn).</li>
                                <li><strong>Cross + Volume:</strong> Yêu cầu vượt qua và giả định có đủ thanh khoản.</li>
                              </ul>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <Select value={formLimitFillPolicy} onValueChange={setFormLimitFillPolicy}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="touch">Touch (Optimistic)</SelectItem>
                            <SelectItem value="cross">Cross (Realistic)</SelectItem>
                            <SelectItem value="cross_volume">Cross + Volume</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5">
                        <Label>Conflict Resolution (TP/SL)</Label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <HelpCircle className="h-3.5 w-3.5 cursor-help text-muted-foreground hover:text-foreground transition-colors" />
                          </TooltipTrigger>
                          <TooltipContent side="right" className="max-w-[350px] text-xs">
                            <p className="font-semibold mb-1">Giải quyết xung đột SL/TP:</p>
                            <p>Khi cả TP và SL đều bị chạm trong cùng một cây nến 1 phút:</p>
                            <ul className="list-disc pl-4 mt-1 space-y-1">
                              <li><strong>SL First:</strong> Ưu tiên khớp SL trước (Bảo thủ/An toàn).</li>
                              <li><strong>TP First:</strong> Ưu tiên khớp TP trước (Lạc quan).</li>
                              <li><strong>Realistic:</strong> Engine tự tính toán dựa trên hướng di chuyển của nến.</li>
                            </ul>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Select value={formPricePathAssumption} onValueChange={setFormPricePathAssumption}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="neutral">SL First (Conservative)</SelectItem>
                          <SelectItem value="optimistic">TP First (Optimistic)</SelectItem>
                          <SelectItem value="realistic">Realistic Path</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </TabsContent>

                  <TabsContent value="fees" className="space-y-4 pt-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Taker Fee (%)</Label>
                        <Input type="number" name="takerFee" value={formTakerFee} onChange={(e) => setFormTakerFee(e.target.value)} step="0.01" />
                      </div>
                      <div className="space-y-2">
                        <Label>Maker Fee (%)</Label>
                        <Input type="number" name="makerFee" value={formMakerFee} onChange={(e) => setFormMakerFee(e.target.value)} step="0.01" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Funding/Day (%)</Label>
                      <Input type="number" name="fundingRate" value={formFundingRate} onChange={(e) => setFormFundingRate(e.target.value)} step="0.01" />
                    </div>
                    <div className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
                      <p>Các thông số phí và funding giúp mô phỏng chính xác hơn lợi nhuận thực tế sau khi trừ đi các chi phí giao dịch và duy trì vị thế.</p>
                    </div>
                  </TabsContent>
                </Tabs>

                <div className="flex gap-3 pt-4 border-t mt-4">
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
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAdvancedColumns(!showAdvancedColumns)}
                className={cn("h-10 gap-2 transition-all", showAdvancedColumns && "bg-primary/10 border-primary/50 text-primary")}
              >
                <Settings2 className="h-4 w-4" />
                {showAdvancedColumns ? "Hide Advanced" : "Show Advanced"}
              </Button>
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
                    {showAdvancedColumns && (
                      <>
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
                            onClick={() => handleSort('marketFillPolicy')}
                            className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                          >
                            Market Fill <SortIcon field="marketFillPolicy" />
                          </button>
                        </TableHead>
                        <TableHead className="text-right">
                          <button
                            onClick={() => handleSort('limitFillPolicy')}
                            className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                          >
                            Limit Cond <SortIcon field="limitFillPolicy" />
                          </button>
                        </TableHead>
                        <TableHead className="text-right">
                          <button
                            onClick={() => handleSort('pricePathAssumption')}
                            className="flex items-center justify-end w-full hover:text-foreground transition-colors"
                          >
                            Conflict Res <SortIcon field="pricePathAssumption" />
                          </button>
                        </TableHead>
                      </>
                    )}
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
                      <TableCell colSpan={showAdvancedColumns ? 21 : 14} className="text-center h-24 text-muted-foreground">
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
                        {showAdvancedColumns && (
                          <>
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
                            <TableCell className="text-right font-mono capitalize">
                              {backtest.marketFillPolicy}
                            </TableCell>
                            <TableCell className="text-right font-mono capitalize">
                              {backtest.limitFillPolicy}
                            </TableCell>
                            <TableCell className="text-right font-mono capitalize">
                              {backtest.pricePathAssumption}
                            </TableCell>
                          </>
                        )}
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
