import { useEffect } from 'react';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { PublicRoute } from "./components/auth/PublicRoute";
import { useAppStore } from '@/lib/store';
import Index from "./pages/Index";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Bots from "./pages/Bots";
import BotDetail from "./pages/BotDetail";
import Strategies from "./pages/Strategies";
import Connections from "./pages/Connections";
import Performance from "./pages/Performance";
import Alerts from "./pages/Alerts";
import Risk from "./pages/Risk";
import Backtest from "./pages/Backtest";
import BacktestDetail from "./pages/BacktestDetail";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const AppContent = () => {
  const checkAuth = useAppStore((state) => state.checkAuth);

  // Initialize auth on app mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes - redirects to / if already authenticated */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>
        
        {/* Protected routes - redirects to /login if not authenticated */}
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Index />} />
          <Route path="/bots" element={<Bots />} />
          <Route path="/bots/:botId" element={<BotDetail />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/backtest/:backtestId" element={<BacktestDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AppContent />
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
