import { useNavigate } from 'react-router-dom';
import { NavLink } from '@/components/NavLink';
import { 
  LayoutDashboard, 
  Bot, 
  Link2, 
  BarChart3, 
  LineChart, 
  Bell, 
  Shield, 
  Settings,
  Activity,
  Zap,
  LogOut
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { useToast } from '@/hooks/use-toast';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/bots', icon: Bot, label: 'Bot Management' },
  { to: '/strategies', icon: Zap, label: 'Strategies' },
  { to: '/connections', icon: Link2, label: 'Connections' },
  { to: '/performance', icon: BarChart3, label: 'Performance' },
  { to: '/backtest', icon: LineChart, label: 'Backtest' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/risk', icon: Shield, label: 'Risk Manager' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const navigate = useNavigate();
  const logout = useAppStore((state) => state.logout);
  const user = useAppStore((state) => state.user);
  const { toast } = useToast();

  const handleLogout = () => {
    logout();
    toast({
      title: 'Logged out',
      description: 'You have been successfully logged out',
    });
    navigate('/login');
  };

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-sidebar">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-border px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Activity className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">TradingBot</h1>
            <p className="text-xs text-muted-foreground">Dashboard V0</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
              )}
              activeClassName="bg-sidebar-accent text-primary"
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User Info & Logout */}
        <div className="border-t border-border px-3 py-2">
          {user && (
            <div className="mb-2 px-3 py-2">
              <p className="text-sm font-medium text-foreground truncate">
                {user.full_name || user.email}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {user.email}
              </p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-destructive transition-all"
          >
            <LogOut className="h-5 w-5" />
            Logout
          </button>
        </div>

        {/* System Status */}
        <div className="border-t border-border p-4">
          <div className="rounded-lg bg-card p-3">
            <div className="flex items-center gap-2 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
              </span>
              <span className="text-muted-foreground">System Online</span>
            </div>
            <div className="mt-2 flex justify-between text-xs text-muted-foreground">
              <span>CPU: 12%</span>
              <span>RAM: 256MB</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
