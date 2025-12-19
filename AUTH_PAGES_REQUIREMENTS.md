# Authentication Pages Requirements

**Project**: Trading Bot Platform  
**Task**: Implement Login & Register Pages  
**Priority**: 🔴 **CRITICAL BLOCKER**  
**Estimated Effort**: 4-6 hours  
**Created**: December 17, 2025

---

## 📋 Overview

Cần tạo 2 pages authentication (Login & Register) để integrate với backend FastAPI. Project hiện tại đang dùng mock auth, cần thay thế bằng real API integration.

### Context
- **Backend**: FastAPI với JWT authentication (access + refresh token)
- **Frontend**: React + TypeScript + Vite + shadcn/ui
- **State Management**: Zustand với persist middleware
- **Routing**: React Router v6
- **Form Library**: React Hook Form + Zod validation
- **API Client**: Cần tạo axios client với interceptors

---

## 🎯 Requirements Summary

### Required Deliverables
1. ✅ **Login Page** (`frontend/src/pages/Login.tsx`)
2. ✅ **Register Page** (`frontend/src/pages/Register.tsx`)
3. ✅ **Auth API Service** (`frontend/src/lib/api/auth.ts`)
4. ✅ **API Client** (`frontend/src/lib/api/client.ts`)
5. ✅ **Auth Store Updates** (update `frontend/src/lib/store.ts`)
6. ✅ **Protected Route Wrapper** (`frontend/src/components/auth/ProtectedRoute.tsx`)
7. ✅ **Public Route Guard** (`frontend/src/components/auth/PublicRoute.tsx`) - NEW
8. ✅ **Logout UI in Sidebar** (update `frontend/src/components/layout/Sidebar.tsx`) - NEW
9. ✅ **Route Updates** (update `frontend/src/App.tsx`)

---

## 🔌 Backend API Integration

### Available Endpoints

```typescript
// Base URL
const API_BASE_URL = 'http://localhost:8000';

// Endpoints
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/users/me
PATCH  /api/v1/users/me
```

### API Schemas

#### 1. Register Request/Response
```typescript
// POST /api/v1/auth/register
interface RegisterRequest {
  username: string;        // Required, 3-50 chars
  email: string;          // Required, valid email
  password: string;       // Required, min 8 chars
  full_name?: string;     // Optional
}

interface AuthResponse {
  access_token: string;   // JWT, 30 min expiry
  refresh_token: string;  // JWT, 7 day expiry
  token_type: "bearer";
  user: {
    id: string;           // UUID
    username: string;
    email: string;
    full_name: string | null;
    is_active: boolean;
  };
}
```

#### 2. Login Request/Response
```typescript
// POST /api/v1/auth/login
interface LoginRequest {
  username: string;       // Email hoặc username
  password: string;
}

// Response: Same as RegisterResponse (AuthResponse)
```

#### 3. Refresh Token
```typescript
// POST /api/v1/auth/refresh
interface RefreshRequest {
  refresh_token: string;
}

interface RefreshResponse {
  access_token: string;
  token_type: "bearer";
}
```

#### 4. Get Current User
```typescript
// GET /api/v1/users/me
// Requires: Authorization: Bearer <access_token>
interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  preferences: {
    theme?: string;
    language?: string;
  };
}
```

### Error Responses

```typescript
interface ErrorResponse {
  detail: string;
}

// Common errors:
// 400 - Validation error (invalid email, password too short)
// 401 - Invalid credentials
// 409 - Username/email already exists
// 422 - Validation error (Pydantic)
```

---

## 📁 File Structure

```
frontend/src/
├── pages/
│   ├── Login.tsx           ← CREATE NEW
│   └── Register.tsx        ← CREATE NEW
├── components/
│   ├── auth/
│   │   ├── ProtectedRoute.tsx  ← CREATE NEW
│   │   └── PublicRoute.tsx     ← CREATE NEW (guard public routes)
│   └── layout/
│       └── Sidebar.tsx     ← UPDATE (add Logout button)
├── lib/
│   ├── api/
│   │   ├── client.ts       ← CREATE NEW (axios instance)
│   │   └── auth.ts         ← CREATE NEW (auth API calls)
│   └── store.ts            ← UPDATE (add auth state)
└── App.tsx                 ← UPDATE (add routes)
```

**Important Note**: Implement theo `App.tsx` hiện tại. Project có file `app/router.tsx` nhưng KHÔNG DÙNG (nó trỏ tới `features/*` không tồn tại). Chỉ follow routing structure trong `App.tsx`.

---

## 🎨 UI/UX Requirements

### Design System
- ✅ Use existing shadcn/ui components
- ✅ Match existing page styles (refer to `Bots.tsx`, `Connections.tsx`)
- ✅ Dark mode compatible
- ✅ Responsive design (mobile-first)

### Login Page Layout
```
┌─────────────────────────────────────┐
│                                     │
│           🤖 Logo/Title             │
│        Trading Bot Platform         │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Email/Username               │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │  Password            [👁️]     │ │
│  └───────────────────────────────┘ │
│                                     │
│  [ ] Remember me    Forgot Password?│
│                                     │
│  ┌───────────────────────────────┐ │
│  │      Login / Sign In          │ │
│  └───────────────────────────────┘ │
│                                     │
│  Don't have an account? Register   │
│                                     │
└─────────────────────────────────────┘
```

### Register Page Layout
```
┌─────────────────────────────────────┐
│                                     │
│           🤖 Logo/Title             │
│        Create Your Account          │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Username                     │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │  Email                        │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │  Full Name (Optional)         │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │  Password            [👁️]     │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │  Confirm Password    [👁️]     │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │      Create Account           │ │
│  └───────────────────────────────┘ │
│                                     │
│  Already have an account? Login    │
│                                     │
└─────────────────────────────────────┘
```

### Component Requirements
- ✅ Use `Card` component for form container
- ✅ Use `Input` component for text fields
- ✅ Use `Button` component with loading state
- ✅ Use `Label` component for form labels
- ✅ Show validation errors inline (red text below input)
- ✅ Password toggle visibility (eye icon)
- ✅ Toast notifications for success/error

---

## 🛠️ Implementation Details

### 1. API Client Setup

**File**: `frontend/src/lib/api/client.ts`

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor - Add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle 401 and token refresh
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If 401 and not already retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Prevent refresh loop - if refresh endpoint itself fails, logout immediately
      if (originalRequest.url?.includes('/api/v1/auth/refresh')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(error);
      }
      
      // Handle concurrent refresh requests with queue
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        }).catch(err => Promise.reject(err));
      }
      
      originalRequest._retry = true;
      isRefreshing = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          // Attempt token refresh
          const { data } = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          // Save new access token
          localStorage.setItem('access_token', data.access_token);
          
          // Process queued requests
          processQueue(null, data.access_token);
          
          // Retry original request
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // Refresh failed - logout user
          processQueue(refreshError, null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        // No refresh token - redirect to login
        isRefreshing = false;
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

---

### 2. Auth API Service

**File**: `frontend/src/lib/api/auth.ts`

```typescript
import apiClient from './client';

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
    full_name: string | null;
    is_active: boolean;
  };
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  preferences: Record<string, any>;
}

export const authApi = {
  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/register', data);
    return response.data;
  },

  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/login', data);
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<RefreshResponse> => {
    const response = await apiClient.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await apiClient.get('/api/v1/users/me');
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};
```

---

### 3. Update Zustand Store

**File**: `frontend/src/lib/store.ts` (ADD to existing store)

```typescript
// Add to interface AppState:
interface AppState {
  // ... existing state ...
  
  // Auth state
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authInitialized: boolean;  // NEW - tracks if checkAuth completed
  
  // Auth actions
  login: (credentials: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

// Add to store implementation:
export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // ... existing state ...
      
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
        } catch (error) {
          set({ isAuthenticated: false, user: null, authInitialized: true });
          authApi.logout();
        }
      },
    }),
    {
      name: 'app-storage',
      // Don't persist tokens (stored in localStorage separately)
      partialize: (state) => ({
        isSetup: state.isSetup,
        // Don't persist user/auth state
      }),
    }
  )
);
```

---

### 4. Protected Route Component

**File**: `frontend/src/components/auth/ProtectedRoute.tsx`

```typescript
import { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAppStore } from '@/lib/store';

export function ProtectedRoute() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const authInitialized = useAppStore((state) => state.authInitialized);
  const checkAuth = useAppStore((state) => state.checkAuth);
  const location = useLocation();

  useEffect(() => {
    if (!authInitialized) {
      checkAuth();
    }
  }, [authInitialized, checkAuth]);

  // Show loading spinner while checking auth
  if (!authInitialized) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Redirect to login if not authenticated, save current location
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
```

---

### 5. Public Route Guard

**File**: `frontend/src/components/auth/PublicRoute.tsx`

```typescript
import { useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAppStore } from '@/lib/store';

export function PublicRoute() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const authInitialized = useAppStore((state) => state.authInitialized);
  const checkAuth = useAppStore((state) => state.checkAuth);

  useEffect(() => {
    if (!authInitialized) {
      checkAuth();
    }
  }, [authInitialized, checkAuth]);

  // Show loading spinner while checking auth
  if (!authInitialized) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Redirect to dashboard if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
```

**Purpose**: Prevents authenticated users from accessing login/register pages.

---

### 6. Login Page

**File**: `frontend/src/pages/Login.tsx`

**Key Requirements**:
- ✅ Form với username (or email) và password
- ✅ React Hook Form + Zod validation
- ✅ Show validation errors inline
- ✅ Loading state khi submit
- ✅ Toast notification on success/error
- ✅ Link to Register page
- ✅ Remember me checkbox - save username to `localStorage.getItem('remembered_username')`
- ✅ Forgot password link - show toast "Feature coming soon" (backend chưa có API)
- ✅ Redirect logic:
  - If `location.state?.from` exists → redirect to that path
  - Else if `isSetup === false` → redirect to `/connections` (onboarding)
  - Else → redirect to `/` (dashboard)

**Validation Rules**:
```typescript
const loginSchema = z.object({
  username: z.string().min(1, "Username/Email is required"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean().optional(),
});
```

**Remember Me Implementation**:
```typescript
// On form submit:
if (formData.rememberMe) {
  localStorage.setItem('remembered_username', formData.username);
} else {
  localStorage.removeItem('remembered_username');
}

// On component mount:
const [rememberMe, setRememberMe] = useState(false);
const rememberedUsername = localStorage.getItem('remembered_username');
if (rememberedUsername) {
  form.setValue('username', rememberedUsername);
  setRememberMe(true);
}
```

**Redirect Logic**:
```typescript
// After successful login:
const navigate = useNavigate();
const location = useLocation();
const isSetup = useAppStore((state) => state.isSetup);

const from = location.state?.from?.pathname || (isSetup ? '/' : '/connections');
navigate(from, { replace: true });
```

**Error Handling**:
```typescript
// 401 - Invalid credentials
toast({
  title: "Login Failed",
  description: "Invalid username or password",
  variant: "destructive",
});

// 400 - Validation error
toast({
  title: "Invalid Input",
  description: error.response.data.detail,
  variant: "destructive",
});

// Network error
toast({
  title: "Connection Error",
  description: "Could not connect to server",
  variant: "destructive",
});
```

---

### 7. Register Page

**File**: `frontend/src/pages/Register.tsx`

**Key Requirements**:
- ✅ Form với username, email, password, confirm password, full_name (optional)
- ✅ React Hook Form + Zod validation
- ✅ Password strength indicator (optional)
- ✅ Password visibility toggle
- ✅ Confirm password match validation
- ✅ Loading state khi submit
- ✅ Toast notification on success/error
- ✅ Link to Login page
- ✅ Redirect logic sau register:
  - If `isSetup === false` → redirect to `/connections` (first-time setup)
  - Else → redirect to `/` (dashboard)

**Validation Rules**:
```typescript
const registerSchema = z.object({
  username: z.string()
    .min(3, "Username must be at least 3 characters")
    .max(50, "Username must be less than 50 characters")
    .regex(/^[a-zA-Z0-9_]+$/, "Username can only contain letters, numbers, and underscores"),
  email: z.string()
    .email("Invalid email address"),
  full_name: z.string().optional(),
  password: z.string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one number"),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});
```

**Error Handling**:
```typescript
// 409 - Username/email already exists
toast({
  title: "Registration Failed",
  description: "Username or email already exists",
  variant: "destructive",
});

// 422 - Validation error from backend
toast({
  title: "Invalid Input",
  description: error.response.data.detail,
  variant: "destructive",
});
```

**Redirect Logic**:
```typescript
// After successful registration:
const navigate = useNavigate();
const isSetup = useAppStore((state) => state.isSetup);

// First-time users go to connections setup
const destination = isSetup ? '/' : '/connections';
navigate(destination, { replace: true });
```

---

### 8. Logout UI in Sidebar

**File**: `frontend/src/components/layout/Sidebar.tsx` (UPDATE existing file)

**Add after navigation section, before System Status**:

```typescript
import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';

// Inside Sidebar component:
export function Sidebar() {
  const navigate = useNavigate();
  const logout = useAppStore((state) => state.logout);
  const { toast } = useToast();

  const handleLogout = () => {
    logout();
    toast({
      title: "Logged out",
      description: "You have been successfully logged out",
    });
    navigate('/login');
  };

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-sidebar">
      <div className="flex h-full flex-col">
        {/* Logo */}
        {/* ... existing logo code ... */}

        {/* Navigation */}
        {/* ... existing nav items ... */}

        {/* Logout Button - NEW */}
        <div className="border-t border-border px-3 py-2">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-destructive transition-all"
          >
            <LogOut className="h-5 w-5" />
            Logout
          </button>
        </div>

        {/* System Status */}
        {/* ... existing system status ... */}
      </div>
    </aside>
  );
}
```

**Key Points**:
- Logout button placed above System Status (bottom of sidebar)
- Uses destructive color on hover for warning
- Shows toast notification
- Navigates to `/login` after logout

---

### 9. Update App Routes

**File**: `frontend/src/App.tsx`

```typescript
import { useEffect } from 'react';
import Login from "./pages/Login";
import Register from "./pages/Register";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { PublicRoute } from "./components/auth/PublicRoute";
import { useAppStore } from '@/lib/store';

const App = () => {
  const checkAuth = useAppStore((state) => state.checkAuth);

  // Initialize auth on app mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
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
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
```

**Key Changes**:
- ✅ Added `<PublicRoute />` wrapper for login/register
- ✅ Added `checkAuth()` on app mount (backup for auth initialization)
- ✅ Public routes now redirect authenticated users away
- ✅ Protected routes save `location.state.from` for post-login redirect

---

## ✅ Validation Checklist

### API Client
- [ ] Axios instance configured với base URL
- [ ] Request interceptor thêm Authorization header
- [ ] Response interceptor xử lý 401 và auto-refresh token
- [ ] Error handling cho network errors
- [ ] Timeout configuration (10s)

### Auth Service
- [ ] `register()` function gọi `/api/v1/auth/register`
- [ ] `login()` function gọi `/api/v1/auth/login`
- [ ] `refresh()` function gọi `/api/v1/auth/refresh`
- [ ] `getCurrentUser()` function gọi `/api/v1/users/me`
- [ ] `logout()` function clear tokens
- [ ] TypeScript interfaces cho tất cả request/response

### Store Updates
- [ ] Thêm `user` state (UserResponse | null)
- [ ] Thêm `isAuthenticated` state (boolean)
- [ ] Thêm `isLoading` state (boolean)
- [ ] Thêm `login()` action
- [ ] Thêm `register()` action
- [ ] Thêm `logout()` action
- [ ] Thêm `checkAuth()` action
- [ ] Save tokens vào localStorage sau login/register
- [ ] Clear tokens khi logout

### Login Page
- [ ] Card container với centered layout
- [ ] Username/Email input field
- [ ] Password input field với visibility toggle
- [ ] Remember me checkbox
- [ ] Submit button với loading state
- [ ] Link to Register page
- [ ] Form validation với Zod schema
- [ ] Error messages hiển thị inline
- [ ] Toast notifications
- [ ] Redirect to `/` sau khi thành công

### Register Page
- [ ] Card container với centered layout
- [ ] Username input field
- [ ] Email input field
- [ ] Full name input field (optional)
- [ ] Password input field với visibility toggle
- [ ] Confirm password input field với visibility toggle
- [ ] Submit button với loading state
- [ ] Link to Login page
- [ ] Form validation với Zod schema (password strength, email format)
- [ ] Password match validation
- [ ] Error messages hiển thị inline
- [ ] Toast notifications
- [ ] Redirect to `/` sau khi thành công

### Protected Route
- [ ] Component check `isAuthenticated` state
- [ ] Check `authInitialized` và show loading spinner khi false
- [ ] Redirect to `/login` với `state: { from: location }` nếu không authenticated
- [ ] Call `checkAuth()` on mount if not initialized
- [ ] Render `<Outlet />` cho nested routes

### Public Route
- [ ] Component check `isAuthenticated` state
- [ ] Check `authInitialized` và show loading spinner khi false
- [ ] Redirect to `/` nếu đã authenticated
- [ ] Call `checkAuth()` on mount if not initialized
- [ ] Render `<Outlet />` cho public pages

### Routing
- [ ] `/login` route wrapped trong `<PublicRoute />`
- [ ] `/register` route wrapped trong `<PublicRoute />`
- [ ] Tất cả routes khác wrapped trong `<ProtectedRoute />`
- [ ] `checkAuth()` called trong App.tsx useEffect (app-level init)
- [ ] Redirect logic đúng với from/isSetup handling

### Logout UI
- [ ] Logout button ở Sidebar (dưới nav, trên System Status)
- [ ] Click logout → gọi `logout()` action
- [ ] Toast notification "Logged out"
- [ ] Navigate to `/login`
- [ ] Tokens cleared from localStorage

---

## 🧪 Testing Requirements

### Manual Testing Checklist

#### Happy Path
- [ ] Register với valid data → Success toast → Redirect to `/connections` (if isSetup=false) or `/` (if isSetup=true)
- [ ] Login với valid credentials → Success toast → Redirect to previous page or `/`
- [ ] Login với "Remember me" checked → Username saved → Auto-filled next time
- [ ] Access protected route khi authenticated → Render page
- [ ] Logout từ Sidebar → Toast "Logged out" → Redirect to `/login` → Tokens cleared
- [ ] Access protected route khi not authenticated → Redirect to `/login` with from state
- [ ] Try access `/login` khi đã authenticated → Redirect to `/`
- [ ] Try access `/register` khi đã authenticated → Redirect to `/`
- [ ] Refresh page khi authenticated → Stay logged in (checkAuth works)
- [ ] Open app in new tab → checkAuth runs → auth state restored

#### Error Cases
- [ ] Register với username đã tồn tại → Error toast với message
- [ ] Register với email đã tồn tại → Error toast với message
- [ ] Register với invalid email format → Inline validation error
- [ ] Register với password quá ngắn → Inline validation error
- [ ] Register với passwords không match → Inline validation error
- [ ] Login với invalid credentials → Error toast
- [ ] Login với empty fields → Inline validation errors
- [ ] Network error → Toast notification với retry option

#### Token Management
- [ ] Access token saved vào localStorage sau login
- [ ] Refresh token saved vào localStorage sau login
- [ ] Tokens attached vào Authorization header
- [ ] Token auto-refresh khi expired (401 response)
- [ ] Multiple concurrent 401s → only 1 refresh call (queuing works)
- [ ] Refresh endpoint 401 → immediate logout (no infinite loop)
- [ ] Redirect to login khi refresh token expired
- [ ] Tokens cleared khi logout
- [ ] authInitialized flag prevents flicker on initial load

#### UI/UX
- [ ] Loading spinner hiển thị khi submit form
- [ ] Button disabled khi loading
- [ ] Password visibility toggle hoạt động
- [ ] Form fields có proper labels và placeholders
- [ ] Validation errors hiển thị màu đỏ
- [ ] Success messages hiển thị màu xanh
- [ ] Links to login/register pages hoạt động
- [ ] Responsive trên mobile

---

## 📝 Code Style Guidelines

### Follow Existing Patterns
- ✅ Use same import structure như `Bots.tsx`
- ✅ Use same component naming conventions
- ✅ Use existing shadcn/ui components
- ✅ Use same error handling patterns
- ✅ Use same toast notification patterns

### TypeScript
- ✅ Define proper interfaces cho tất cả data types
- ✅ Avoid `any` types
- ✅ Use type inference khi có thể
- ✅ Export types từ API service files

### React Hooks
- ✅ Use `useState` cho local form state
- ✅ Use `useNavigate` cho redirects
- ✅ Use `useToast` cho notifications
- ✅ Use `useAppStore` cho global auth state
- ✅ Use `useForm` từ react-hook-form

### Error Handling
- ✅ Wrap API calls trong try-catch
- ✅ Show user-friendly error messages
- ✅ Log errors to console trong development
- ✅ Use axios error response structure

---

## 🚀 Getting Started

### Prerequisites
```bash
# Install dependencies (nếu chưa có)
cd frontend
npm install axios react-hook-form zod
```

### Environment Setup
```bash
# Create .env.local file
VITE_API_URL=http://localhost:8000
```

### Development Workflow
1. ✅ Tạo API client (`client.ts`) trước
2. ✅ Tạo auth service (`auth.ts`)
3. ✅ Update Zustand store với auth state
4. ✅ Tạo ProtectedRoute component
5. ✅ Tạo Login page
6. ✅ Tạo Register page
7. ✅ Update App.tsx với routes
8. ✅ Test manually với backend running
9. ✅ Fix bugs và polish UI

---

## 🔗 Reference Files

### Existing Code to Reference
- `frontend/src/pages/Bots.tsx` - Form handling pattern
- `frontend/src/lib/store.ts` - Zustand store structure
- `frontend/src/App.tsx` - Routing setup
- `backend/docs/API_REFERENCE.md` - API documentation
- `frontend/src/components/ui/*` - shadcn/ui components

### External Documentation
- [React Hook Form](https://react-hook-form.com/)
- [Zod Validation](https://zod.dev/)
- [Axios](https://axios-http.com/)
- [React Router](https://reactrouter.com/)
- [shadcn/ui](https://ui.shadcn.com/)

---

## 📊 Success Criteria

### Definition of Done
- [ ] ✅ Tất cả 7 files đã tạo/update
- [ ] ✅ Login page hoạt động đầy đủ
- [ ] ✅ Register page hoạt động đầy đủ
- [ ] ✅ Protected routes redirect đúng
- [ ] ✅ Token management hoạt động
- [ ] ✅ Error handling comprehensive
- [ ] ✅ UI/UX polish và responsive
- [ ] ✅ Manual testing checklist passed
- [ ] ✅ Code review guidelines followed
- [ ] ✅ No console errors/warnings

### Post-Implementation
- [ ] Test with real backend API
- [ ] Update documentation nếu cần
- [ ] Create PR với clear description
- [ ] Demo cho team

---

## 💡 Implementation Tips

### Best Practices
1. **Start Simple**: Tạo basic login form trước, rồi mới thêm features
2. **Test Incrementally**: Test mỗi component riêng biệt trước khi integrate
3. **Handle Edge Cases**: Empty states, loading states, error states
4. **User Feedback**: Always show feedback cho mọi actions
5. **Security**: Never log passwords hoặc tokens trong production

### Common Pitfalls to Avoid
- ❌ Forget to clear tokens khi logout
- ❌ Not handling 401 errors properly (refresh loop)
- ❌ Storing tokens in state instead of localStorage
- ❌ Not showing loading states during auth check (causes flicker)
- ❌ Poor error messages ("Error occurred")
- ❌ Not validating email format
- ❌ Weak password requirements
- ❌ Not handling network errors
- ❌ Forget to guard public routes (allow authenticated users on /login)
- ❌ Not implementing Remember Me feature
- ❌ Hardcode redirect to `/` instead of using from/isSetup logic
- ❌ Follow `app/router.tsx` instead of `App.tsx` (router.tsx không dùng!)

---

**Deadline**: Complete within 1 sprint (4-6 hours)  
**Priority**: 🔴 **BLOCKER** - Cannot proceed with other features without auth  
**Owner**: AI Code Generator  
**Reviewer**: Team Lead

---

**Next Steps After Completion**:
1. Test auth flow thoroughly (follow testing checklist)
2. Verify logout button works in Sidebar
3. Test Remember Me feature
4. Test redirect logic (from route, isSetup handling)
5. Test concurrent 401 handling (no duplicate refresh calls)
6. Add user profile display in Sidebar (optional - show username/avatar)
7. Proceed with Phase 2: Exchange Connections integration
8. Consider forgot password flow (needs backend API first)

**Questions? Contact**: [Your contact info]
