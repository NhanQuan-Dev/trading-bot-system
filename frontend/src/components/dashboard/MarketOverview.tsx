import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

// Market data removed - using real API

import { useEffect, useState } from 'react';

export function MarketOverview() {
  const [marketData, setMarketData] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const headers: HeadersInit = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch('/api/v1/market-data/overview?limit=5', { headers });
        if (res.ok) {
          const data = await res.json();
          // Use highest volume items
          const items = data.highest_volume || [];
          setMarketData(items.map((item: any) => ({
            symbol: item.symbol,
            price: item.last_price || 0,
            change: item.price_change_percent_24h || 0,
            volume: formatVolume(item.volume_24h || 0)
          })));
        }
      } catch (error) {
        console.error('Failed to fetch market overview');
      }
    };
    fetchData();
  }, []);

  const formatVolume = (vol: number) => {
    if (vol >= 1e9) return (vol / 1e9).toFixed(1) + 'B';
    if (vol >= 1e6) return (vol / 1e6).toFixed(1) + 'M';
    if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
    return vol.toFixed(0);
  };
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
