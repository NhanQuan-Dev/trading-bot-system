import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Shield, AlertTriangle, TrendingDown, DollarSign, Pause, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { useToast } from '@/hooks/use-toast';

export default function Risk() {
  const [maxExposure, setMaxExposure] = useState(30);
  const [maxDailyLoss, setMaxDailyLoss] = useState(5);
  const [cooldownEnabled, setCooldownEnabled] = useState(true);
  const [emergencyStop, setEmergencyStop] = useState(false);
  const { toast } = useToast();

  const currentExposure = 13.1;
  const currentDailyLoss = 2.3;

  const handleEmergencyStop = () => {
    setEmergencyStop(true);
    toast({
      title: "Emergency Stop Activated",
      description: "All bots have been paused immediately",
      variant: "destructive"
    });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-foreground">Risk Manager</h1>
              <p className="text-muted-foreground">Configure global risk parameters and limits</p>
            </div>
          </div>
          <Button 
            variant="destructive" 
            className="gap-2"
            onClick={handleEmergencyStop}
            disabled={emergencyStop}
          >
            <Pause className="h-4 w-4" />
            {emergencyStop ? 'All Bots Stopped' : 'Emergency Stop All'}
          </Button>
        </div>

        {/* Risk Overview */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="border-border bg-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <DollarSign className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Current Exposure</p>
                  <p className="text-2xl font-bold text-foreground">{currentExposure}%</p>
                </div>
              </div>
              <Progress 
                value={(currentExposure / maxExposure) * 100} 
                className="mt-4 h-2"
              />
              <p className="mt-2 text-xs text-muted-foreground">Limit: {maxExposure}%</p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  currentDailyLoss > maxDailyLoss * 0.8 ? "bg-destructive/10" : "bg-accent/10"
                )}>
                  <TrendingDown className={cn(
                    "h-5 w-5",
                    currentDailyLoss > maxDailyLoss * 0.8 ? "text-destructive" : "text-accent"
                  )} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Daily Loss</p>
                  <p className="text-2xl font-bold text-foreground">{currentDailyLoss}%</p>
                </div>
              </div>
              <Progress 
                value={(currentDailyLoss / maxDailyLoss) * 100} 
                className="mt-4 h-2"
              />
              <p className="mt-2 text-xs text-muted-foreground">Limit: {maxDailyLoss}%</p>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                  <Activity className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Active Positions</p>
                  <p className="text-2xl font-bold text-foreground">7</p>
                </div>
              </div>
              <div className="mt-4 text-sm text-muted-foreground">
                <span className="text-primary">3 Long</span> • <span className="text-destructive">4 Short</span>
              </div>
            </CardContent>
          </Card>

          <Card className={cn(
            "border-border bg-card",
            emergencyStop && "border-destructive/50"
          )}>
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg",
                  emergencyStop ? "bg-destructive/10" : "bg-primary/10"
                )}>
                  <Shield className={cn(
                    "h-5 w-5",
                    emergencyStop ? "text-destructive" : "text-primary"
                  )} />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">System Status</p>
                  <p className={cn(
                    "text-xl font-bold",
                    emergencyStop ? "text-destructive" : "text-primary"
                  )}>
                    {emergencyStop ? 'STOPPED' : 'HEALTHY'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Risk Configuration */}
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle>Global Risk Limits</CardTitle>
              <CardDescription>Configure maximum thresholds for automated risk management</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Max Total Exposure</Label>
                  <span className="text-sm text-muted-foreground">{maxExposure}%</span>
                </div>
                <Input
                  type="range"
                  min={10}
                  max={100}
                  value={maxExposure}
                  onChange={(e) => setMaxExposure(Number(e.target.value))}
                  className="cursor-pointer"
                />
                <p className="text-xs text-muted-foreground">
                  Percentage of total balance allowed in active positions
                </p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Max Daily Loss</Label>
                  <span className="text-sm text-muted-foreground">{maxDailyLoss}%</span>
                </div>
                <Input
                  type="range"
                  min={1}
                  max={20}
                  value={maxDailyLoss}
                  onChange={(e) => setMaxDailyLoss(Number(e.target.value))}
                  className="cursor-pointer"
                />
                <p className="text-xs text-muted-foreground">
                  All bots will stop if daily loss exceeds this limit
                </p>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div>
                  <p className="font-medium text-foreground">Loss Streak Cooldown</p>
                  <p className="text-sm text-muted-foreground">Pause trading after 3 consecutive losses</p>
                </div>
                <Switch checked={cooldownEnabled} onCheckedChange={setCooldownEnabled} />
              </div>

              <Button className="w-full">Save Configuration</Button>
            </CardContent>
          </Card>

          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle>Risk Per Bot</CardTitle>
              <CardDescription>Individual bot risk allocation and limits</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { name: 'BTC Grid Bot', exposure: 5.2, limit: 10, status: 'ok' },
                  { name: 'ETH DCA Bot', exposure: 3.8, limit: 8, status: 'ok' },
                  { name: 'SOL Trend', exposure: 2.5, limit: 5, status: 'warning' },
                  { name: 'DOGE Scalper', exposure: 1.6, limit: 5, status: 'error' },
                ].map((bot) => (
                  <div key={bot.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={cn(
                          "h-2 w-2 rounded-full",
                          bot.status === 'ok' && "bg-primary",
                          bot.status === 'warning' && "bg-accent",
                          bot.status === 'error' && "bg-destructive"
                        )} />
                        <span className="font-medium text-foreground">{bot.name}</span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {bot.exposure}% / {bot.limit}%
                      </span>
                    </div>
                    <Progress 
                      value={(bot.exposure / bot.limit) * 100} 
                      className="h-2"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Warning Banner */}
        {emergencyStop && (
          <Card className="border-destructive/50 bg-destructive/10">
            <CardContent className="flex items-center gap-4 p-4">
              <AlertTriangle className="h-8 w-8 text-destructive" />
              <div className="flex-1">
                <h3 className="font-semibold text-destructive">Emergency Stop Active</h3>
                <p className="text-sm text-muted-foreground">
                  All trading bots have been paused. Review your positions before resuming.
                </p>
              </div>
              <Button 
                variant="outline" 
                onClick={() => setEmergencyStop(false)}
              >
                Resume Trading
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
