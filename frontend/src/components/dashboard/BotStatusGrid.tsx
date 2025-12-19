import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAppStore, Bot } from '@/lib/store';
import { Play, Pause, Square, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const statusConfig = {
  running: { label: 'Running', color: 'bg-primary', icon: Play },
  paused: { label: 'Paused', color: 'bg-accent', icon: Pause },
  stopped: { label: 'Stopped', color: 'bg-muted', icon: Square },
  error: { label: 'Error', color: 'bg-destructive', icon: AlertCircle }
};

export function BotStatusGrid() {
  const bots = useAppStore((state) => state.bots);
  const updateBot = useAppStore((state) => state.updateBot);

  const handleToggle = (bot: Bot) => {
    if (bot.status === 'running') {
      updateBot(bot.id, { status: 'paused' });
    } else if (bot.status === 'paused' || bot.status === 'stopped') {
      updateBot(bot.id, { status: 'running' });
    }
  };

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-foreground">Active Bots</CardTitle>
          <Badge variant="outline" className="text-xs">
            {bots.filter(b => b.status === 'running').length} / {bots.length} Active
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {bots.map((bot) => {
            const config = statusConfig[bot.status];
            const StatusIcon = config.icon;
            const isProfit = bot.pnl >= 0;
            
            return (
              <div
                key={bot.id}
                className="flex items-center justify-between rounded-lg border border-border bg-background/50 p-4 transition-all hover:bg-muted/30"
              >
                <div className="flex items-center gap-4">
                  <div className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    bot.status === 'running' && "bg-primary/10",
                    bot.status === 'paused' && "bg-accent/10",
                    bot.status === 'error' && "bg-destructive/10",
                    bot.status === 'stopped' && "bg-muted/50"
                  )}>
                    <StatusIcon className={cn(
                      "h-5 w-5",
                      bot.status === 'running' && "text-primary",
                      bot.status === 'paused' && "text-accent",
                      bot.status === 'error' && "text-destructive",
                      bot.status === 'stopped' && "text-muted-foreground"
                    )} />
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{bot.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {bot.symbol} • {bot.exchange}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className={cn(
                      "flex items-center gap-1 font-mono text-sm font-medium",
                      isProfit ? "text-primary" : "text-destructive"
                    )}>
                      {isProfit ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingDown className="h-4 w-4" />
                      )}
                      ${Math.abs(bot.pnl).toFixed(2)}
                    </div>
                    <p className={cn(
                      "text-xs",
                      isProfit ? "text-primary" : "text-destructive"
                    )}>
                      {isProfit ? '+' : ''}{bot.pnlPercent.toFixed(2)}%
                    </p>
                  </div>

                  <Badge
                    variant="outline"
                    className={cn(
                      "min-w-[80px] justify-center",
                      bot.status === 'running' && "border-primary/50 text-primary",
                      bot.status === 'paused' && "border-accent/50 text-accent",
                      bot.status === 'error' && "border-destructive/50 text-destructive"
                    )}
                  >
                    {config.label}
                  </Badge>

                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleToggle(bot)}
                    disabled={bot.status === 'error'}
                    className="h-8 w-8"
                  >
                    {bot.status === 'running' ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
