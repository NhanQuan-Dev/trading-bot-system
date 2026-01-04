import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, User, LoginData, RegisterData } from './api/auth';
import { connectionsApi } from './api/connections';
import { botsApi } from './api/bots';
import type { ExchangeConnection, CreateConnectionRequest, UpdateConnectionRequest } from './types/connection';
import type { Bot, CreateBotRequest, UpdateBotRequest, BotFilters } from './types/bot';

// Bot type now imported from types/bot.ts

export interface Connection {
  id: string;
  name: string;
  exchange: string;
  type: 'live' | 'testnet';
  status: 'connected' | 'disconnected' | 'error';
  lastSync: string;
}

export interface Trade {
  id: string;
  botId: string;
  symbol: string;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  pnl: number;
  timestamp: string;
  status: 'open' | 'closed';
}

interface AppState {
  // Setup state
  isSetup: boolean;
  setIsSetup: (value: boolean) => void;

  // Auth state
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authInitialized: boolean;

  // Auth actions
  login: (credentials: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;

  // Bot state
  bots: Bot[];
  botsLoading: boolean;
  fetchBots: (filters?: BotFilters) => Promise<void>;
  getBot: (id: string) => Promise<Bot>;
  createBot: (data: CreateBotRequest) => Promise<void>;
  updateBot: (id: string, data: UpdateBotRequest) => Promise<void>;
  deleteBot: (id: string) => Promise<void>;
  startBot: (id: string) => Promise<void>;
  stopBot: (id: string) => Promise<void>;
  pauseBot: (id: string) => Promise<void>;

  // Connections state
  connections: ExchangeConnection[];
  connectionsLoading: boolean;
  fetchConnections: () => Promise<void>;
  createConnection: (data: CreateConnectionRequest) => Promise<void>;
  updateConnection: (id: string, data: UpdateConnectionRequest) => Promise<void>;
  deleteConnection: (id: string) => Promise<void>;

  trades: Trade[];
  addTrade: (trade: Trade) => void;

  totalBalance: number;
  dailyPnl: number;
  totalExposure: number;
}

// Mock data removed - using real API

// Mock data removed

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Setup state
      isSetup: false,
      setIsSetup: (value) => set({ isSetup: value }),

      // Auth state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      authInitialized: false,

      // Auth actions
      login: async (credentials) => {
        set({ isLoading: true });
        try {
          const response = await authApi.login(credentials);

          // Save tokens
          localStorage.setItem('access_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);

          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            authInitialized: true,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (data) => {
        set({ isLoading: true });
        try {
          const response = await authApi.register(data);

          // Save tokens
          localStorage.setItem('access_token', response.access_token);
          localStorage.setItem('refresh_token', response.refresh_token);

          set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            authInitialized: true,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        authApi.logout();
        set({
          user: null,
          isAuthenticated: false,
        });
      },

      checkAuth: async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
          set({ isAuthenticated: false, user: null, authInitialized: true });
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({ user, isAuthenticated: true, authInitialized: true });
        } catch {
          set({ isAuthenticated: false, user: null, authInitialized: true });
          authApi.logout();
        }
      },

      // Bot state & actions
      bots: [],
      botsLoading: false,

      fetchBots: async (filters?: BotFilters) => {
        set({ botsLoading: true });
        try {
          const bots = await botsApi.list(filters);
          set({ bots, botsLoading: false });
        } catch (error) {
          console.error('Failed to fetch bots:', error);
          set({ botsLoading: false });
          throw error;
        }
      },

      getBot: async (id: string) => {
        try {
          return await botsApi.get(id);
        } catch (error) {
          console.error('Failed to get bot:', error);
          throw error;
        }
      },

      createBot: async (data: CreateBotRequest) => {
        set({ botsLoading: true });
        try {
          const bot = await botsApi.create(data);
          set((state) => ({
            bots: [...state.bots, bot],
            botsLoading: false
          }));
        } catch (error) {
          console.error('Failed to create bot:', error);
          set({ botsLoading: false });
          throw error;
        }
      },

      updateBot: async (id: string, data: UpdateBotRequest) => {
        set({ botsLoading: true });
        try {
          const updatedBot = await botsApi.update(id, data);
          set((state) => ({
            bots: state.bots.map(b => b.id === id ? updatedBot : b),
            botsLoading: false
          }));
        } catch (error) {
          console.error('Failed to update bot:', error);
          set({ botsLoading: false });
          throw error;
        }
      },

      deleteBot: async (id: string) => {
        set({ botsLoading: true });
        try {
          await botsApi.delete(id);
          set((state) => ({
            bots: state.bots.filter(b => b.id !== id),
            botsLoading: false
          }));
        } catch (error) {
          console.error('Failed to delete bot:', error);
          set({ botsLoading: false });
          throw error;
        }
      },

      startBot: async (id: string) => {
        try {
          const updatedBot = await botsApi.start(id);
          // Only update state if we got a valid bot back
          if (updatedBot && updatedBot.id) {
            set((state) => ({
              bots: state.bots.map(b => b.id === id ? updatedBot : b)
            }));
          } else {
            console.error('startBot: Invalid response - bot data missing');
            const bots = await botsApi.list();
            set({ bots });
          }
        } catch (error) {
          console.error('Failed to start bot:', error);
          throw error;
        }
      },

      stopBot: async (id: string) => {
        try {
          const updatedBot = await botsApi.stop(id);
          // Only update state if we got a valid bot back
          if (updatedBot && updatedBot.id) {
            set((state) => ({
              bots: state.bots.map(b => b.id === id ? updatedBot : b)
            }));
          } else {
            console.error('stopBot: Invalid response - bot data missing');
            const bots = await botsApi.list();
            set({ bots });
          }
        } catch (error) {
          console.error('Failed to stop bot:', error);
          throw error;
        }
      },

      pauseBot: async (id: string) => {
        try {
          const updatedBot = await botsApi.pause(id);
          // Only update state if we got a valid bot back
          if (updatedBot && updatedBot.id) {
            set((state) => ({
              bots: state.bots.map(b => b.id === id ? updatedBot : b)
            }));
          } else {
            console.error('pauseBot: Invalid response - bot data missing');
            // Refetch bots to ensure consistent state
            const bots = await botsApi.list();
            set({ bots });
          }
        } catch (error) {
          console.error('Failed to pause bot:', error);
          throw error;
        }
      },

      // Connections state & actions
      connections: [],
      connectionsLoading: false,

      fetchConnections: async () => {
        set({ connectionsLoading: true });
        try {
          const connections = await connectionsApi.list();
          set({ connections, connectionsLoading: false });
        } catch (error) {
          console.error('Failed to fetch connections:', error);
          set({ connectionsLoading: false });
          throw error;
        }
      },

      createConnection: async (data: CreateConnectionRequest) => {
        set({ connectionsLoading: true });
        try {
          const connection = await connectionsApi.create(data);
          set((state) => ({
            connections: [...(Array.isArray(state.connections) ? state.connections : []), connection],
            connectionsLoading: false
          }));
        } catch (error) {
          console.error('Failed to create connection:', error);
          set({ connectionsLoading: false });
          throw error;
        }
      },

      updateConnection: async (id: string, data: UpdateConnectionRequest) => {
        set({ connectionsLoading: true });
        try {
          const updatedConnection = await connectionsApi.update(id, data);
          set((state) => ({
            connections: state.connections.map(c =>
              c.id === id ? updatedConnection : c
            ),
            connectionsLoading: false
          }));
        } catch (error) {
          console.error('Failed to update connection:', error);
          set({ connectionsLoading: false });
          throw error;
        }
      },

      deleteConnection: async (id: string) => {
        set({ connectionsLoading: true });
        try {
          await connectionsApi.delete(id);
          set((state) => ({
            connections: state.connections.filter(c => c.id !== id),
            connectionsLoading: false
          }));
        } catch (error) {
          console.error('Failed to delete connection:', error);
          set({ connectionsLoading: false });
          throw error;
        }
      },

      trades: [],
      addTrade: (trade) => set((state) => ({ trades: [...state.trades, trade] })),

      totalBalance: 0,
      dailyPnl: 0,
      totalExposure: 0
    }),
    {
      name: 'trading-dashboard-storage',
      // Don't persist auth state (tokens stored in localStorage separately)
      partialize: (state) => ({
        isSetup: state.isSetup,
        // Persist other non-auth state as needed
      }),
    }
  )
);
