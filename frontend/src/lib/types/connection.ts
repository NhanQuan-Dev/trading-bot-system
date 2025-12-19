/**
 * Exchange Connection Types
 */

export interface ExchangeConnection {
  id: string;
  user_id?: string;
  exchange: string;
  exchange_type?: string;
  name: string;
  api_key: string;
  is_active: boolean;
  is_testnet: boolean;
  status?: string; // CONNECTED, DISCONNECTED, CONNECTING, ERROR
  created_at: string;
  updated_at?: string;
  last_used_at?: string;
}

export interface CreateConnectionRequest {
  exchange_type: string;
  name: string;
  api_key: string;
  secret_key: string;
  passphrase?: string;
  testnet_api_key?: string;
  testnet_secret_key?: string;
  is_testnet?: boolean;
  spot_trade?: boolean;
  futures_trade?: boolean;
  margin_trade?: boolean;
  read_only?: boolean;
  withdraw?: boolean;
}

export interface UpdateConnectionRequest {
  name?: string;
  api_key?: string;
  api_secret?: string;
  is_active?: boolean;
}

export interface TestConnectionRequest {
  connection_id: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  account_info?: {
    balance: number;
    currency: string;
  };
}

export interface AccountInfo {
  exchange: string;
  balances: Array<{
    asset: string;
    free: number;
    locked: number;
  }>;
  positions?: Array<{
    symbol: string;
    size: number;
    side: 'long' | 'short';
    entry_price: number;
  }>;
}
