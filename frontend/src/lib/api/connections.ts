import apiClient from './client';
import type {
  ExchangeConnection,
  CreateConnectionRequest,
  UpdateConnectionRequest,
  TestConnectionRequest,
  TestConnectionResponse,
  AccountInfo,
} from '../types/connection';

export const connectionsApi = {
  /**
   * Get all exchange connections for the current user
   */
  list: async (): Promise<ExchangeConnection[]> => {
    const response = await apiClient.get('/api/v1/exchanges/connections');
    return response.data;
  },

  /**
   * Create a new exchange connection
   */
  create: async (data: CreateConnectionRequest): Promise<ExchangeConnection> => {
    const response = await apiClient.post('/api/v1/exchanges/connections', data);
    return response.data;
  },

  /**
   * Update an existing connection
   */
  update: async (id: string, data: UpdateConnectionRequest): Promise<ExchangeConnection> => {
    const response = await apiClient.put(`/api/v1/exchanges/connections/${id}`, data);
    return response.data;
  },

  /**
   * Delete a connection
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/exchanges/connections/${id}`);
  },

  /**
   * Test connection credentials - uses refresh endpoint to test and update status
   */
  test: async (data: TestConnectionRequest): Promise<TestConnectionResponse> => {
    const response = await apiClient.post(`/api/connections/${data.connection_id}/refresh`);
    // Map refresh response to TestConnectionResponse format
    const testResult = response.data.test_result || {};
    return {
      success: testResult.success ?? false,
      message: testResult.message || testResult.error || 'Connection test completed',
    };
  },

  /**
   * Get account info for a connection
   */
  getAccount: async (id: string): Promise<AccountInfo> => {
    const response = await apiClient.get(`/api/v1/exchanges/connections/${id}/account`);
    return response.data;
  },
};
