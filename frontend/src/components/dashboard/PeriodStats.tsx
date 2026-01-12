import { cn } from '@/lib/utils';

// Type definitions for period stats
export interface PeriodData {
    pnl: number;
    trades: number;
    wins: number;
    losses: number;
}

export interface PeriodStats {
    today: PeriodData;
    yesterday: PeriodData;
    this_week: PeriodData;
    last_week: PeriodData;
    this_month: PeriodData;
    last_month: PeriodData;
}

// Period rows: Day, Week, Month - each row has current and previous
const PERIOD_ROWS: Array<{
    current: keyof PeriodStats;
    previous: keyof PeriodStats;
    currentLabel: string;
    previousLabel: string;
}> = [
        { current: 'today', previous: 'yesterday', currentLabel: 'Today', previousLabel: 'Yesterday' },
        { current: 'this_week', previous: 'last_week', currentLabel: 'This Week', previousLabel: 'Last Week' },
        { current: 'this_month', previous: 'last_month', currentLabel: 'This Month', previousLabel: 'Last Month' },
    ];

// Color helper based on value
function getValueColor(value: number): string {
    if (value > 0) return 'text-primary'; // Green
    if (value < 0) return 'text-destructive'; // Red
    return 'text-foreground'; // White for zero
}

// Calculate win rate
function calcWinRate(wins: number, total: number): number {
    if (total === 0) return 0;
    return (wins / total) * 100;
}

interface PeriodStatsRowProps {
    periodStats: PeriodStats;
    metric: 'pnl' | 'winRate' | 'trades' | 'streak';
}

export function PeriodStatsRow({ periodStats, metric }: PeriodStatsRowProps) {
    return (
        <div className="mt-3 pt-3 border-t border-border/50 space-y-1.5">
            {PERIOD_ROWS.map(({ current, previous, currentLabel, previousLabel }) => {
                const currentData = periodStats[current];
                const previousData = periodStats[previous];

                let currentValue: number;
                let previousValue: number;
                let currentDisplay: string;
                let previousDisplay: string;

                switch (metric) {
                    case 'pnl':
                        currentValue = currentData.pnl;
                        previousValue = previousData.pnl;
                        // Calculate % change for current period compared to previous
                        const pnlPctChange = previousValue !== 0
                            ? ((currentValue - previousValue) / Math.abs(previousValue)) * 100
                            : (currentValue !== 0 ? 100 : 0);
                        const pctSign = pnlPctChange >= 0 ? '+' : '';
                        currentDisplay = `$${currentValue >= 0 ? '+' : ''}${currentValue.toFixed(2)} (${pctSign}${pnlPctChange.toFixed(0)}%)`;
                        previousDisplay = `$${previousValue >= 0 ? '+' : ''}${previousValue.toFixed(2)}`;
                        break;
                    case 'winRate':
                        currentValue = calcWinRate(currentData.wins, currentData.trades);
                        previousValue = calcWinRate(previousData.wins, previousData.trades);
                        currentDisplay = `${currentValue.toFixed(1)}%`;
                        previousDisplay = `${previousValue.toFixed(1)}%`;
                        break;
                    case 'trades':
                        currentValue = currentData.trades;
                        previousValue = previousData.trades;
                        currentDisplay = `${currentData.trades} (${currentData.wins}W/${currentData.losses}L)`;
                        previousDisplay = `${previousData.trades} (${previousData.wins}W/${previousData.losses}L)`;
                        break;
                    case 'streak':
                        // Show both win and loss streaks
                        currentValue = currentData.wins - currentData.losses;
                        previousValue = previousData.wins - previousData.losses;
                        currentDisplay = `${currentData.wins}W/${currentData.losses}L`;
                        previousDisplay = `${previousData.wins}W/${previousData.losses}L`;
                        break;
                }

                return (
                    <div key={current} className="flex items-center text-xs gap-4">
                        {/* Current period */}
                        <div className="flex items-baseline gap-1.5 flex-1">
                            <span className="text-foreground text-[10px] w-16">{currentLabel}</span>
                            <span className={cn('font-medium', getValueColor(currentValue))}>
                                {currentDisplay}
                            </span>
                        </div>

                        {/* Previous period */}
                        <div className="flex items-baseline gap-1.5 flex-1">
                            <span className="text-foreground text-[10px] w-16">{previousLabel}</span>
                            <span className={cn('font-medium', getValueColor(previousValue))}>
                                {previousDisplay}
                            </span>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

// Mock data generator for testing (will be replaced with API data)
export function generateMockPeriodStats(): PeriodStats {
    const mockPeriod = (): PeriodData => ({
        pnl: (Math.random() - 0.4) * 500,
        trades: Math.floor(Math.random() * 15),
        wins: Math.floor(Math.random() * 10),
        losses: Math.floor(Math.random() * 5),
    });

    return {
        today: mockPeriod(),
        yesterday: mockPeriod(),
        this_week: mockPeriod(),
        last_week: mockPeriod(),
        this_month: mockPeriod(),
        last_month: mockPeriod(),
    };
}
