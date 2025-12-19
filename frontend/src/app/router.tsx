import { Routes, Route } from "react-router-dom";

// Portfolio feature
import DashboardPage from "@/features/portfolio/components/DashboardPage";
import PerformancePage from "@/features/portfolio/components/PerformancePage";

// Bots feature
import BotsPage from "@/features/bots/components/BotsPage";
import BotDetailPage from "@/features/bots/components/BotDetailPage";

// Trading feature
import StrategiesPage from "@/features/trading/components/StrategiesPage";

// Risk feature
import RiskPage from "@/features/risk/components/RiskPage";

// Backtest feature
import BacktestPage from "@/features/backtest/components/BacktestPage";

// Alerts feature
import AlertsPage from "@/features/alerts/components/AlertsPage";

// Auth feature
import ConnectionsPage from "@/features/auth/components/ConnectionsPage";

// App pages
import SettingsPage from "./SettingsPage";
import NotFoundPage from "./NotFoundPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/performance" element={<PerformancePage />} />
      
      <Route path="/bots" element={<BotsPage />} />
      <Route path="/bots/:botId" element={<BotDetailPage />} />
      
      <Route path="/strategies" element={<StrategiesPage />} />
      
      <Route path="/risk" element={<RiskPage />} />
      
      <Route path="/backtest" element={<BacktestPage />} />
      
      <Route path="/alerts" element={<AlertsPage />} />
      
      <Route path="/connections" element={<ConnectionsPage />} />
      
      <Route path="/settings" element={<SettingsPage />} />
      
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
