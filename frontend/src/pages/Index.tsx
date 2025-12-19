import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { SummaryCard } from '@/components/dashboard/SummaryCard';
import { EquityChart } from '@/components/dashboard/EquityChart';
import { BotStatusGrid } from '@/components/dashboard/BotStatusGrid';
import { MarketOverview } from '@/components/dashboard/MarketOverview';
import { WelcomeSetup } from '@/components/setup/WelcomeSetup';
import { useAppStore } from '@/lib/store';
import { Wallet, TrendingUp, Bot, DollarSign } from 'lucide-react';

export default function Index() {
  const isSetup = useAppStore((state) => state.isSetup);
  const totalBalance = useAppStore((state) => state.totalBalance);
  const dailyPnl = useAppStore((state) => state.dailyPnl);
  const totalExposure = useAppStore((state) => state.totalExposure);
  const bots = useAppStore((state) => state.bots);

  if (!isSetup) {
    return <WelcomeSetup />;
  }

  const activeBots = bots.filter(b => b.status === 'running').length;
  const totalTrades = bots.reduce((sum, bot) => sum + bot.totalTrades, 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Real-time monitoring of your trading bots</p>
        </div>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            title="Total Balance"
            value={`$${totalBalance.toLocaleString()}`}
            change="+8.2% from last month"
            changeType="positive"
            icon={Wallet}
          />
          <SummaryCard
            title="24h P&L"
            value={`$${dailyPnl.toLocaleString()}`}
            change={`+${((dailyPnl / totalBalance) * 100).toFixed(2)}%`}
            changeType="positive"
            icon={TrendingUp}
          />
          <SummaryCard
            title="Active Bots"
            value={`${activeBots} / ${bots.length}`}
            change={`${totalTrades} trades today`}
            changeType="neutral"
            icon={Bot}
          />
          <SummaryCard
            title="Total Exposure"
            value={`$${totalExposure.toLocaleString()}`}
            change={`${((totalExposure / totalBalance) * 100).toFixed(1)}% of balance`}
            changeType="neutral"
            icon={DollarSign}
          />
        </div>

        {/* Charts and Widgets */}
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <EquityChart />
          </div>
          <div>
            <MarketOverview />
          </div>
        </div>

        {/* Bot Status */}
        <BotStatusGrid />
      </div>
    </DashboardLayout>
  );
}
