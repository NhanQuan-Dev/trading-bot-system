import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { useState, useMemo } from 'react';

const generateData = (days: number) => {
  const data = [];
  let value = 20000;
  const now = Date.now();
  
  for (let i = days; i >= 0; i--) {
    const change = (Math.random() - 0.45) * 500;
    value = Math.max(value + change, 15000);
    data.push({
      date: new Date(now - i * 86400000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: Math.round(value * 100) / 100,
      hodl: 20000 + (days - i) * 50
    });
  }
  return data;
};

export function EquityChart() {
  const [period, setPeriod] = useState('7d');
  
  const data = useMemo(() => {
    const days = period === '24h' ? 1 : period === '7d' ? 7 : 30;
    return generateData(days);
  }, [period]);

  return (
    <Card className="border-border bg-card">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold text-foreground">Equity Curve</CardTitle>
        <Tabs value={period} onValueChange={setPeriod}>
          <TabsList className="bg-muted">
            <TabsTrigger value="24h" className="text-xs">24h</TabsTrigger>
            <TabsTrigger value="7d" className="text-xs">7d</TabsTrigger>
            <TabsTrigger value="1M" className="text-xs">1M</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(142, 76%, 46%)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(142, 76%, 46%)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorHodl" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(38, 92%, 50%)" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="hsl(38, 92%, 50%)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 20%)" />
              <XAxis 
                dataKey="date" 
                stroke="hsl(215, 15%, 60%)" 
                fontSize={12}
                tickLine={false}
              />
              <YAxis 
                stroke="hsl(215, 15%, 60%)" 
                fontSize={12}
                tickLine={false}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(220, 18%, 12%)',
                  border: '1px solid hsl(220, 15%, 20%)',
                  borderRadius: '8px',
                  color: 'hsl(210, 20%, 98%)'
                }}
                formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
              />
              <Area
                type="monotone"
                dataKey="hodl"
                stroke="hsl(38, 92%, 50%)"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorHodl)"
                name="HODL"
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="hsl(142, 76%, 46%)"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorValue)"
                name="Portfolio"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 flex justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-primary" />
            <span className="text-muted-foreground">Portfolio</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-accent" />
            <span className="text-muted-foreground">HODL</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
