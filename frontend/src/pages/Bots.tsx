import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useAppStore } from '@/lib/store';
import type { Bot } from '@/lib/types/bot';
import axios from 'axios';
import { 
  Plus, Search, Play, Pause, Square, Trash2, Settings, 
  TrendingUp, TrendingDown, Filter, MoreVertical, Eye, Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

const statusConfig: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: 'Active', color: 'border-primary/50 text-primary' },
  PAUSED: { label: 'Paused', color: 'border-accent/50 text-accent' },
  STOPPED: { label: 'Stopped', color: 'border-muted/50 text-muted-foreground' },
  ERROR: { label: 'Error', color: 'border-destructive/50 text-destructive' },
  STARTING: { label: 'Starting', color: 'border-yellow-500/50 text-yellow-500' },
  STOPPING: { label: 'Stopping', color: 'border-orange-500/50 text-orange-500' },
  // Fallback for lowercase
  running: { label: 'Running', color: 'border-primary/50 text-primary' },
  paused: { label: 'Paused', color: 'border-accent/50 text-accent' },
  stopped: { label: 'Stopped', color: 'border-muted/50 text-muted-foreground' },
  error: { label: 'Error', color: 'border-destructive/50 text-destructive' }
};

export default function Bots() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actioningBotId, setActioningBotId] = useState<string | null>(null);
  const navigate = useNavigate();
  
  const bots = useAppStore((state) => state.bots);
  const botsLoading = useAppStore((state) => state.botsLoading);
  const fetchBots = useAppStore((state) => state.fetchBots);
  const createBot = useAppStore((state) => state.createBot);
  const deleteBot = useAppStore((state) => state.deleteBot);
  const startBot = useAppStore((state) => state.startBot);
  const stopBot = useAppStore((state) => state.stopBot);
  const pauseBot = useAppStore((state) => state.pauseBot);
  const connections = useAppStore((state) => state.connections);
  const fetchConnections = useAppStore((state) => state.fetchConnections);
  const { toast } = useToast();
  
  // Fetch bots and connections on mount
  useEffect(() => {
    fetchBots().catch((error) => {
      toast({
        title: 'Error',
        description: 'Failed to load bots',
        variant: 'destructive',
      });
    });
    
    fetchConnections().catch((error) => {
      console.error('Failed to load connections:', error);
    });
  }, [fetchBots, fetchConnections, toast]);

  const filteredBots = bots.filter(bot => {
    const matchesSearch = bot.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          bot.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || bot.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const handleStart = async (bot: Bot) => {
    setActioningBotId(bot.id);
    try {
      await startBot(bot.id);
      toast({ title: `${bot.name} started` });
    } catch (error) {
      const message = axios.isAxiosError(error) 
        ? error.response?.data?.detail || 'Failed to start bot'
        : 'Failed to start bot';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setActioningBotId(null);
    }
  };

  const handleStop = async (bot: Bot) => {
    setActioningBotId(bot.id);
    try {
      await stopBot(bot.id);
      toast({ title: `${bot.name} stopped` });
    } catch (error) {
      const message = axios.isAxiosError(error) 
        ? error.response?.data?.detail || 'Failed to stop bot'
        : 'Failed to stop bot';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setActioningBotId(null);
    }
  };

  const handlePause = async (bot: Bot) => {
    setActioningBotId(bot.id);
    try {
      await pauseBot(bot.id);
      toast({ title: `${bot.name} paused` });
    } catch (error) {
      const message = axios.isAxiosError(error) 
        ? error.response?.data?.detail || 'Failed to pause bot'
        : 'Failed to pause bot';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setActioningBotId(null);
    }
  };

  const handleDelete = async (bot: Bot) => {
    setActioningBotId(bot.id);
    try {
      await deleteBot(bot.id);
      toast({ 
        title: 'Bot deleted',
        description: `${bot.name} has been removed`,
      });
    } catch (error) {
      const message = axios.isAxiosError(error) 
        ? error.response?.data?.detail || 'Failed to delete bot'
        : 'Failed to delete bot';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setActioningBotId(null);
    }
  };

  const handleCreateBot = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const formData = new FormData(e.currentTarget);
    const connectionId = formData.get('connection') as string;
    const selectedConnection = connections.find((c) => c.id === connectionId);
    const isPaper = selectedConnection
      ? ((selectedConnection as any).type === 'testnet' || (selectedConnection as any).is_testnet)
      : true;

    const botData = {
      name: formData.get('name') as string,
      exchange_connection_id: connectionId,
      strategy_id: formData.get('strategy') as string,
      symbol: formData.get('symbol') as string,
      capital: Number(formData.get('capital')) || 1000,
      leverage: Number(formData.get('leverage')) || 1,
      is_paper_trading: isPaper,
    };
    
    try {
      await createBot(botData);
      setIsCreateOpen(false);
      e.currentTarget.reset();
      toast({ 
        title: 'Bot created',
        description: 'Bot has been created successfully!',
      });
    } catch (error) {
      const message = axios.isAxiosError(error) 
        ? error.response?.data?.detail || 'Failed to create bot'
        : 'Failed to create bot';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Bot Management</h1>
            <p className="text-muted-foreground">Create, configure, and manage your trading bots</p>
          </div>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Create Bot
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Create New Bot</DialogTitle>
                <DialogDescription>
                  Configure your new trading bot with the settings below.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateBot} className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Bot Name</Label>
                  <Input id="name" name="name" placeholder="My Trading Bot" required />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="connection">Exchange Connection</Label>
                    <Select name="connection" required>
                      <SelectTrigger>
                        <SelectValue placeholder="Select connection" />
                      </SelectTrigger>
                      <SelectContent>
                        {connections.length === 0 ? (
                          <SelectItem value="none" disabled>No connections available</SelectItem>
                        ) : (
                          connections.map((conn) => (
                            <SelectItem key={conn.id} value={conn.id}>
                              {conn.name} ({(conn as any).exchange_type || conn.exchange})
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="symbol">Trading Pair</Label>
                    <Input id="symbol" name="symbol" placeholder="BTC/USDT" required />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Strategy (ID)</Label>
                  <Input name="strategy" placeholder="strategy-id-123" required />
                  <p className="text-xs text-muted-foreground">Enter strategy ID from Strategies page</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="capital">Capital (USDT)</Label>
                    <Input id="capital" name="capital" type="number" placeholder="1000" step="0.01" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="leverage">Leverage</Label>
                    <Input id="leverage" name="leverage" type="number" placeholder="1" min="1" max="125" />
                  </div>
                </div>
                {/* Trading Mode removed: derive paper/live from selected connection type */}
                <div className="flex gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)} className="flex-1">
                    Cancel
                  </Button>
                  <Button type="submit" className="flex-1" disabled={isSubmitting}>
                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Create Bot
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4">
          <div className="relative flex-1 md:max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search bots..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[150px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="stopped">Stopped</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Bots Grid */}
        {botsLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredBots.length === 0 ? (
          <Card className="border-border bg-card">
            <CardContent className="py-12 text-center">
              <Settings className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <p className="text-muted-foreground">
                {searchQuery || filterStatus !== 'all' 
                  ? 'No bots match your filters'
                  : 'No bots yet. Create your first bot to get started!'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredBots.map((bot) => {
              const isProfit = (bot.total_pnl || 0) >= 0;
              const config = statusConfig[bot.status] || statusConfig.STOPPED;

            return (
              <Card key={bot.id} className="border-border bg-card transition-all hover:shadow-lg hover:shadow-primary/5">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{bot.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{bot.symbol} • {bot.exchange}</p>
                    </div>
                    <Badge variant="outline" className={config.color}>
                      {config.label}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">P&L</p>
                      <p className={cn(
                        "flex items-center gap-1 font-mono font-semibold",
                        isProfit ? "text-primary" : "text-destructive"
                      )}>
                        {isProfit ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                        ${Math.abs(bot.total_pnl || 0).toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Win Rate</p>
                      <p className="font-mono font-semibold text-foreground">{(bot.win_rate || 0).toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Total Trades</p>
                      <p className="font-mono font-semibold text-foreground">{bot.total_trades || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Capital</p>
                      <p className="text-sm font-medium text-foreground">${bot.capital.toFixed(0)}</p>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-2">
                    {bot.status === 'ACTIVE' || bot.status === 'STARTING' ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => handlePause(bot)}
                          disabled={actioningBotId === bot.id}
                        >
                          {actioningBotId === bot.id ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <Pause className="mr-1 h-3 w-3" />
                          )}
                          Pause
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleStop(bot)}
                          disabled={actioningBotId === bot.id}
                        >
                          {actioningBotId === bot.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Square className="h-3 w-3" />
                          )}
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => handleStart(bot)}
                        disabled={actioningBotId === bot.id || bot.status === 'ERROR'}
                      >
                        {actioningBotId === bot.id ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <Play className="mr-1 h-3 w-3" />
                        )}
                        Start
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/bots/${bot.id}`)}
                    >
                      <Eye className="h-3 w-3" />
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm">
                          <MoreVertical className="h-3 w-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/bots/${bot.id}/settings`)}>
                          <Settings className="mr-2 h-4 w-4" /> Configure
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          className="text-destructive"
                          onClick={() => handleDelete(bot)}
                          disabled={actioningBotId === bot.id}
                        >
                          {actioningBotId === bot.id ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="mr-2 h-4 w-4" />
                          )}
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardContent>
              </Card>
            );
          })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
