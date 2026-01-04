import apiClient from './client';
import type {
  Bot,
  CreateBotRequest,
  UpdateBotRequest,
  BotFilters,
  BotMetrics,
} from '../types/bot';

export const botsApi = {
  /**
   * Get all bots with optional filters
   */
  list: async (filters?: BotFilters): Promise<Bot[]> => {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.exchange) params.append('exchange', filters.exchange);
    if (filters?.strategy) params.append('strategy', filters.strategy);
    if (filters?.symbol) params.append('symbol', filters.symbol);
    if (filters?.is_paper_trading !== undefined) {
      params.append('is_paper_trading', String(filters.is_paper_trading));
    }

    const response = await apiClient.get(`/api/v1/bots?${params.toString()}`);
    return response.data;
  },

  /**
   * Get a single bot by ID
   */
  get: async (id: string): Promise<Bot> => {
    const response = await apiClient.get(`/api/v1/bots/${id}`);
    return response.data;
  },

  /**
   * Create a new bot
   */
  create: async (data: CreateBotRequest): Promise<Bot> => {
    const response = await apiClient.post('/api/v1/bots', data);
    return response.data;
  },

  /**
   * Update an existing bot
   */
  update: async (id: string, data: UpdateBotRequest): Promise<Bot> => {
    const response = await apiClient.patch(`/api/v1/bots/${id}`, data);
    return response.data;
  },

  /**
   * Delete a bot
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/bots/${id}`);
  },

  /**
   * Start a bot
   */
  start: async (id: string): Promise<Bot> => {
    const response = await apiClient.post(`/api/v1/bots/${id}/start`);
    // Handle both formats: {bot: {...}} or direct bot object
    const data = response.data;
    if (data.bot) {
      return data.bot;
    }
    // Response might be the bot directly or have different structure
    if (data.id) {
      return data;
    }
    console.warn('start: Unexpected response format:', data);
    return data;
  },

  /**
   * Stop a bot
   */
  stop: async (id: string): Promise<Bot> => {
    const response = await apiClient.post(`/api/v1/bots/${id}/stop`);
    // Handle both formats: {bot: {...}} or direct bot object
    const data = response.data;
    if (data.bot) {
      return data.bot;
    }
    if (data.id) {
      return data;
    }
    console.warn('stop: Unexpected response format:', data);
    return data;
  },

  /**
   * Pause a bot (if supported by backend)
   */
  pause: async (id: string): Promise<Bot> => {
    const response = await apiClient.post(`/api/v1/bots/${id}/pause`);
    // Handle both formats: {bot: {...}} or direct bot object
    const data = response.data;
    if (data.bot) {
      return data.bot;
    }
    if (data.id) {
      return data;
    }
    console.warn('pause: Unexpected response format:', data);
    return data;
  },

  /**
   * Get bot metrics/statistics
   */
  getMetrics: async (id: string): Promise<BotMetrics> => {
    const response = await apiClient.get(`/api/v1/bots/${id}/metrics`);
    return response.data;
  },
};
