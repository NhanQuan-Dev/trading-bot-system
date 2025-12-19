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
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to dashboard if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
