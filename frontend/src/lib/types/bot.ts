export interface Bot {
  id: string;
  user_id: string;
  name: string;
  exchange_connection_id: string;
  strategy_id: string;
  symbol: string;
  status: string; // ACTIVE, PAUSED, STOPPED, ERROR, STARTING, STOPPING
  capital: number;
  leverage: number;
  max_position_size?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop?: boolean;
  is_paper_trading: boolean;
  created_at: string;
  updated_at: string;
  started_at?: string;
  stopped_at?: string;
  last_error?: string;
  
  // Metrics (optional, may come from separate endpoint)
  total_pnl?: number;
  total_trades?: number;
  win_rate?: number;
  current_position?: any;
}

export interface CreateBotRequest {
  name: string;
  exchange_connection_id: string;
  strategy_id: string;
  symbol: string;
  capital: number;
  leverage?: number;
  max_position_size?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop?: boolean;
  is_paper_trading?: boolean;
}

export interface UpdateBotRequest {
  name?: string;
  capital?: number;
  leverage?: number;
  max_position_size?: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop?: boolean;
}

export interface BotFilters {
  status?: string;
  exchange?: string;
  strategy?: string;
  symbol?: string;
  is_paper_trading?: boolean;
}

export interface BotMetrics {
  bot_id: string;
  total_pnl: number;
  total_pnl_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  current_position?: {
    symbol: string;
    side: string;
    size: number;
    entry_price: number;
    current_price: number;
    pnl: number;
    pnl_pct: number;
  };
}
