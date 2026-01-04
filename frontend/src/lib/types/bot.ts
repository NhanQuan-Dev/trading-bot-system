export interface BotConfiguration {
  bot_type: string;
  symbol: string;
  exchange_connection_id: string;
  max_position_size: number;
  max_open_orders: number;
  leverage: number;
  strategy_params: Record<string, any>;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  max_daily_loss?: number;
}

export interface Bot {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  configuration: BotConfiguration;
  status: string;
  is_active: boolean;
  metrics: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    total_profit: number;
    total_loss: number;
    net_profit: number;
    win_rate: number;
    avg_profit: number;
    avg_loss: number;
    max_drawdown: number;
    profit_factor: number;
    sharpe_ratio?: number;
  };
  created_at: string;
  updated_at: string;
  started_at?: string;
  stopped_at?: string;
  last_trade_at?: string;
  error_message?: string;

  // Helpers for UI backward compatibility (mapping to config)
  symbol?: string;
  capital?: number;
  strategy_id?: string;
  exchange_connection_id?: string;
  total_profit_loss?: number | string; // From API Response
  total_pnl?: number | string;  // Can be string from WS match
  win_rate?: number;
  total_trades?: number;

  // NEW: Streak tracking (from DB columns)
  winning_trades?: number;
  losing_trades?: number;
  current_win_streak?: number;
  current_loss_streak?: number;
  max_win_streak?: number;
  max_loss_streak?: number;
}

export interface CreateBotRequest {
  name: string;
  description?: string;
  strategy_id: string;

  // Flattened Configuration
  bot_type?: string;
  symbol: string;
  exchange_connection_id: string;
  base_quantity?: number;
  quote_quantity?: number;
  max_active_orders?: number;
  leverage?: number;
  risk_percentage?: number;
  take_profit_percentage?: number;
  stop_loss_percentage?: number;
  risk_level?: string;

  max_daily_loss?: number;
  max_drawdown?: number;
  strategy_settings?: Record<string, any>;
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
