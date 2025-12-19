import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Bell, BellRing, AlertTriangle, CheckCircle, Info, Trash2, Plus, Volume2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Alert {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

const mockAlerts: Alert[] = [
  { id: '1', type: 'success', title: 'Take Profit Hit', message: 'BTC Grid Bot closed position at $68,200 with +$125 profit', timestamp: new Date().toISOString(), read: false },
  { id: '2', type: 'warning', title: 'High Drawdown', message: 'SOL Trend bot reached -5% drawdown', timestamp: new Date(Date.now() - 3600000).toISOString(), read: false },
  { id: '3', type: 'error', title: 'Connection Lost', message: 'Bybit connection interrupted - attempting reconnect', timestamp: new Date(Date.now() - 7200000).toISOString(), read: true },
  { id: '4', type: 'info', title: 'Bot Started', message: 'ETH DCA Bot started successfully', timestamp: new Date(Date.now() - 14400000).toISOString(), read: true },
  { id: '5', type: 'success', title: 'New Trade Executed', message: 'BTC Grid Bot opened LONG position at $67,500', timestamp: new Date(Date.now() - 21600000).toISOString(), read: true },
];

const alertConfig = {
  info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  success: { icon: CheckCircle, color: 'text-primary', bg: 'bg-primary/10' },
  warning: { icon: AlertTriangle, color: 'text-accent', bg: 'bg-accent/10' },
  error: { icon: AlertTriangle, color: 'text-destructive', bg: 'bg-destructive/10' },
};

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>(mockAlerts);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [desktopNotifications, setDesktopNotifications] = useState(true);

  const unreadCount = alerts.filter(a => !a.read).length;

  const markAsRead = (id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, read: true } : a));
  };

  const deleteAlert = (id: string) => {
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  const clearAll = () => {
    setAlerts([]);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Bell className="h-8 w-8 text-primary" />
              {unreadCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-xs font-bold text-destructive-foreground">
                  {unreadCount}
                </span>
              )}
            </div>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Alerts</h1>
              <p className="text-muted-foreground">Stay informed about your trading activity</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={clearAll} disabled={alerts.length === 0}>
              Clear All
            </Button>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New Alert Rule
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Alert Settings */}
          <Card className="border-border bg-card lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-lg">Notification Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div className="flex items-center gap-3">
                  <Volume2 className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium text-foreground">Sound Alerts</p>
                    <p className="text-sm text-muted-foreground">Play sound for new alerts</p>
                  </div>
                </div>
                <Switch checked={soundEnabled} onCheckedChange={setSoundEnabled} />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div className="flex items-center gap-3">
                  <BellRing className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium text-foreground">Desktop Notifications</p>
                    <p className="text-sm text-muted-foreground">Show system notifications</p>
                  </div>
                </div>
                <Switch checked={desktopNotifications} onCheckedChange={setDesktopNotifications} />
              </div>

              <div className="pt-4">
                <h4 className="mb-3 font-medium text-foreground">Active Rules</h4>
                <div className="space-y-2">
                  {[
                    { name: 'P&L Alert', condition: 'When daily P&L > $500' },
                    { name: 'Drawdown Alert', condition: 'When drawdown > 5%' },
                    { name: 'Connection Alert', condition: 'When connection lost' },
                  ].map((rule) => (
                    <div key={rule.name} className="rounded-lg bg-muted/50 p-3">
                      <p className="font-medium text-foreground">{rule.name}</p>
                      <p className="text-xs text-muted-foreground">{rule.condition}</p>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Alert Inbox */}
          <Card className="border-border bg-card lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">Alert Inbox</CardTitle>
            </CardHeader>
            <CardContent>
              {alerts.length === 0 ? (
                <div className="py-12 text-center">
                  <Bell className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="text-muted-foreground">No alerts yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {alerts.map((alert) => {
                    const config = alertConfig[alert.type];
                    const Icon = config.icon;

                    return (
                      <div
                        key={alert.id}
                        className={cn(
                          "flex items-start gap-4 rounded-lg border border-border p-4 transition-all",
                          !alert.read && "bg-muted/30"
                        )}
                        onClick={() => markAsRead(alert.id)}
                      >
                        <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", config.bg)}>
                          <Icon className={cn("h-5 w-5", config.color)} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-foreground">{alert.title}</h4>
                            <div className="flex items-center gap-2">
                              {!alert.read && (
                                <Badge variant="secondary" className="text-xs">New</Badge>
                              )}
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  deleteAlert(alert.id);
                                }}
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                          <p className="mt-1 text-sm text-muted-foreground">{alert.message}</p>
                          <p className="mt-2 text-xs text-muted-foreground">
                            {new Date(alert.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
