import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const marketData = [
  { symbol: 'BTC/USDT', price: 67845.20, change: 2.45, volume: '1.2B' },
  { symbol: 'ETH/USDT', price: 3521.80, change: 1.82, volume: '845M' },
  { symbol: 'SOL/USDT', price: 148.65, change: -3.21, volume: '425M' },
  { symbol: 'DOGE/USDT', price: 0.1245, change: 5.67, volume: '312M' },
  { symbol: 'XRP/USDT', price: 0.5234, change: -0.89, volume: '198M' },
];

export function MarketOverview() {
  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold text-foreground">Market Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {marketData.map((item) => {
            const isPositive = item.change >= 0;
            
            return (
              <div
                key={item.symbol}
                className="flex items-center justify-between rounded-lg border border-border bg-background/50 p-3 transition-all hover:bg-muted/30"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-bold text-foreground">
                    {item.symbol.split('/')[0].slice(0, 2)}
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{item.symbol}</p>
                    <p className="text-xs text-muted-foreground">Vol: {item.volume}</p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="font-mono text-sm font-medium text-foreground">
                    ${item.price.toLocaleString()}
                  </p>
                  <div className={cn(
                    "flex items-center justify-end gap-1 text-xs font-medium",
                    isPositive ? "text-primary" : "text-destructive"
                  )}>
                    {isPositive ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    {isPositive ? '+' : ''}{item.change.toFixed(2)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
