import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface SummaryCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  iconColor?: string;
}

export function SummaryCard({ 
  title, 
  value, 
  change, 
  changeType = 'neutral', 
  icon: Icon,
  iconColor = 'text-primary'
}: SummaryCardProps) {
  return (
    <Card className="border-border bg-card transition-all hover:shadow-lg hover:shadow-primary/5">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold text-foreground">{value}</p>
            {change && (
              <p className={cn(
                "text-sm font-medium",
                changeType === 'positive' && "text-primary",
                changeType === 'negative' && "text-destructive",
                changeType === 'neutral' && "text-muted-foreground"
              )}>
                {change}
              </p>
            )}
          </div>
          <div className={cn(
            "flex h-12 w-12 items-center justify-center rounded-xl",
            "bg-primary/10"
          )}>
            <Icon className={cn("h-6 w-6", iconColor)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
