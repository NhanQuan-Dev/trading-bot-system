import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAppStore } from '@/lib/store';
import { connectionsApi } from '@/lib/api/connections';
import type { ExchangeConnection, CreateConnectionRequest } from '@/lib/types/connection';
import { Plus, Link2, Trash2, RefreshCw, Eye, EyeOff, Shield, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import axios from 'axios';
import { cn } from '@/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

const exchangeLogos: Record<string, string> = {
  Binance: '🟡',
  BINANCE: '🟡',
  Bybit: '🟠',
  BYBIT: '🟠',
  OKX: '⚪',
  Kraken: '🟣',
};

const statusConfig: Record<string, { icon: any; color: string; label: string }> = {
  CONNECTED: { icon: CheckCircle, color: 'text-primary', label: 'Connected' },
  DISCONNECTED: { icon: XCircle, color: 'text-muted-foreground', label: 'Disconnected' },
  CONNECTING: { icon: Loader2, color: 'text-yellow-500', label: 'Connecting' },
  ERROR: { icon: AlertCircle, color: 'text-destructive', label: 'Error' },
  // Fallback for undefined status
  active: { icon: CheckCircle, color: 'text-primary', label: 'Active' },
  inactive: { icon: XCircle, color: 'text-muted-foreground', label: 'Inactive' },
};

export default function Connections() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [isRefreshing, setIsRefreshing] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  const connections = useAppStore((state) => state.connections);
  const connectionsLoading = useAppStore((state) => state.connectionsLoading);
  const fetchConnections = useAppStore((state) => state.fetchConnections);
  const createConnection = useAppStore((state) => state.createConnection);
  const deleteConnection = useAppStore((state) => state.deleteConnection);
  const { toast } = useToast();

  // Fetch connections on mount
  useEffect(() => {
    fetchConnections().catch((error) => {
      console.error('Failed to load connections:', error);
      toast({
        title: 'Error loading connections',
        description: 'Please try refreshing the page',
        variant: 'destructive',
      });
    });
  }, [fetchConnections, toast]);

  const handleCreateConnection = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);

    const formData = new FormData(e.currentTarget);
    const connectionData: CreateConnectionRequest = {
      name: formData.get('name') as string,
      exchange_type: formData.get('exchange') as string,
      api_key: formData.get('apiKey') as string,
      secret_key: formData.get('secretKey') as string,
      is_testnet: formData.get('type') === 'testnet',
      futures_trade: true, // Default to futures trading
    };

    try {
      await createConnection(connectionData);
      setIsCreateOpen(false);

      toast({
        title: 'Connection created',
        description: 'Exchange connection added successfully!',
      });
    } catch (error) {
      let errorMessage = 'Failed to create connection';
      if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map((err: any) => err.msg).join(', ');
        }
      }
      toast({
        title: 'Error',
        description: errorMessage + (error instanceof Error ? `: ${error.message}` : ''),
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTestConnection = async (connectionId: string) => {
    setIsTesting(true);

    try {
      const result = await connectionsApi.test({ connection_id: connectionId });

      toast({
        title: result.success ? 'Connection successful' : 'Connection failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      });
    } catch (error) {
      toast({
        title: 'Test failed',
        description: 'Failed to test connection',
        variant: 'destructive',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = async (connection: ExchangeConnection) => {
    try {
      await deleteConnection(connection.id);
      toast({
        title: 'Connection deleted',
        description: `${connection.name} has been removed`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete connection',
        variant: 'destructive',
      });
    }
  };

  const toggleSecret = (id: string) => {
    setShowSecrets(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Connections</h1>
            <p className="text-muted-foreground">Manage your exchange API connections securely</p>
          </div>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Add Connection
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  Add Exchange Connection
                </DialogTitle>
                <DialogDescription>
                  Your API keys are encrypted locally using AES-256 and never leave your machine.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateConnection} className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Connection Name</Label>
                  <Input id="name" name="name" placeholder="My Binance Account" required />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Exchange</Label>
                    <Select name="exchange" defaultValue="BINANCE">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BINANCE">🟡 Binance</SelectItem>
                        <SelectItem value="BYBIT">🟠 Bybit</SelectItem>
                        <SelectItem value="OKX">⚪ OKX</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select name="type" defaultValue="live">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="live">Live Trading</SelectItem>
                        <SelectItem value="testnet">Testnet</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="apiKey">API Key</Label>
                  <Input id="apiKey" name="apiKey" placeholder="Enter your API key" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="secretKey">Secret Key</Label>
                  <Input id="secretKey" name="secretKey" type="password" placeholder="Enter your secret key" required />
                </div>
                <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
                  <p className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    Keys are encrypted with your Master Passphrase before storage
                  </p>
                </div>
                <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)} className="flex-1">
                    Cancel
                  </Button>
                  <Button type="submit" className="flex-1" disabled={isSubmitting}>
                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Add Connection
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Security Notice */}
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Local Secure Vault</h3>
              <p className="text-sm text-muted-foreground">
                All API keys are encrypted with AES-256 using your Master Passphrase and stored locally.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Connections Grid */}
        {connectionsLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : connections.length === 0 ? (
          <Card className="border-border bg-card">
            <CardContent className="py-12 text-center">
              <Link2 className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <p className="text-muted-foreground">No connections yet. Add your first exchange API to get started!</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {connections.map((connection) => {
              // Use backend status field, fallback to is_active
              const status = (connection as any).status || (connection.is_active ? 'CONNECTED' : 'DISCONNECTED');
              const config = statusConfig[status] || statusConfig.DISCONNECTED;
              const StatusIcon = config.icon;
              const statusColor = config.color;

              return (
                <Card key={connection.id} className="border-border bg-card">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted text-2xl">
                          {exchangeLogos[((connection as any).exchange_type || connection.exchange)] || '🔗'}
                        </div>
                        <div>
                          <CardTitle className="text-lg">{connection.name}</CardTitle>
                          <CardDescription>{(connection as any).exchange_type || connection.exchange}</CardDescription>
                        </div>
                      </div>
                      <Badge
                        variant={!connection.is_testnet ? 'default' : 'secondary'}
                        className={!connection.is_testnet ? 'bg-primary/10 text-primary' : ''}
                      >
                        {!connection.is_testnet ? 'Live' : 'Testnet'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusIcon className={cn("h-4 w-4", statusColor, status === 'CONNECTING' && 'animate-spin')} />
                        <span className={cn("text-sm", statusColor)}>
                          {config.label}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        Created: {new Date(connection.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between rounded-lg bg-muted/50 p-2">
                        <span className="text-sm text-muted-foreground">API Key</span>
                        <div className="flex items-center gap-2">
                          <code className="text-xs">
                            {showSecrets[connection.id] ? connection.api_key.substring(0, 8) + '...' : '••••••••'}
                          </code>
                          <button
                            onClick={() => toggleSecret(connection.id)}
                            className="text-muted-foreground hover:text-foreground"
                          >
                            {showSecrets[connection.id] ? (
                              <EyeOff className="h-3 w-3" />
                            ) : (
                              <Eye className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2 pt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => handleTestConnection(connection.id)}
                        disabled={isTesting}
                      >
                        {isTesting && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                        {!isTesting && <RefreshCw className="mr-1 h-3 w-3" />}
                        Test
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDelete(connection)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
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
