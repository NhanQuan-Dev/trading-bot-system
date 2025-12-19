import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { 
  Settings as SettingsIcon, Lock, FolderOpen, Download, Upload, 
  Key, Trash2, RefreshCw, Database, Shield
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useState } from 'react';
import { useAppStore } from '@/lib/store';

export default function Settings() {
  const [dataPath] = useState('~/.trading_dashboard');
  const [autoStart, setAutoStart] = useState(true);
  const [debugMode, setDebugMode] = useState(false);
  const setIsSetup = useAppStore((state) => state.setIsSetup);
  const { toast } = useToast();

  const handleBackup = () => {
    toast({ title: 'Backup Created', description: 'Your data has been backed up successfully' });
  };

  const handleRestore = () => {
    toast({ title: 'Restore', description: 'Please select a backup file to restore' });
  };

  const handleReset = () => {
    setIsSetup(false);
    toast({ title: 'Reset Complete', description: 'Dashboard has been reset to initial state', variant: 'destructive' });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
            <SettingsIcon className="h-6 w-6 text-foreground" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-foreground">Settings</h1>
            <p className="text-muted-foreground">Configure your dashboard preferences</p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Security Settings */}
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                Security
              </CardTitle>
              <CardDescription>Manage your master passphrase and encryption settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border p-4">
                <div className="flex items-center gap-3">
                  <Lock className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium text-foreground">Master Passphrase</p>
                    <p className="text-sm text-muted-foreground">Last changed: 30 days ago</p>
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  <Key className="mr-2 h-4 w-4" />
                  Change
                </Button>
              </div>

              <div className="rounded-lg bg-primary/5 p-4">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-primary">AES-256 Encryption</strong> is used to protect all your API keys and sensitive data locally.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Storage Settings */}
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                Data Storage
              </CardTitle>
              <CardDescription>Configure where your data is stored</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Data Directory</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <FolderOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input value={dataPath} readOnly className="pl-10" />
                  </div>
                  <Button variant="outline">Browse</Button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-muted/50 p-4 text-center">
                  <p className="text-2xl font-bold text-foreground">12.4 MB</p>
                  <p className="text-sm text-muted-foreground">Database Size</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-4 text-center">
                  <p className="text-2xl font-bold text-foreground">1,245</p>
                  <p className="text-sm text-muted-foreground">Total Records</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Application Settings */}
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle>Application</CardTitle>
              <CardDescription>General application settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">Auto-start Bots</p>
                  <p className="text-sm text-muted-foreground">Resume bot states on startup</p>
                </div>
                <Switch checked={autoStart} onCheckedChange={setAutoStart} />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">Debug Mode</p>
                  <p className="text-sm text-muted-foreground">Enable verbose logging</p>
                </div>
                <Switch checked={debugMode} onCheckedChange={setDebugMode} />
              </div>

              <div className="pt-4">
                <p className="text-sm font-medium text-muted-foreground">Version</p>
                <p className="text-foreground">TradingBot Dashboard v0.1.0 (Local)</p>
              </div>
            </CardContent>
          </Card>

          {/* Backup & Restore */}
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle>Backup & Restore</CardTitle>
              <CardDescription>Manage your data backups</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Button variant="outline" className="h-auto flex-col gap-2 p-4" onClick={handleBackup}>
                  <Download className="h-6 w-6" />
                  <span>Create Backup</span>
                </Button>
                <Button variant="outline" className="h-auto flex-col gap-2 p-4" onClick={handleRestore}>
                  <Upload className="h-6 w-6" />
                  <span>Restore Backup</span>
                </Button>
              </div>

              <div className="rounded-lg bg-muted/50 p-4">
                <p className="text-sm text-muted-foreground">
                  Backups include all configurations, bot settings, and trade history. 
                  <strong className="text-foreground"> Your Master Passphrase is required to restore.</strong>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-destructive/30 bg-card lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>Irreversible actions - proceed with caution</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between rounded-lg border border-destructive/30 p-4">
                <div>
                  <p className="font-medium text-foreground">Reset Dashboard</p>
                  <p className="text-sm text-muted-foreground">
                    Clear all data and return to initial setup. This cannot be undone.
                  </p>
                </div>
                <Button variant="destructive" onClick={handleReset}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Reset All Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
