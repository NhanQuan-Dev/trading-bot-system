import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAppStore } from '@/lib/store';
import { Activity, Shield, Eye, EyeOff, Check, Lock, FolderOpen, Zap } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export function WelcomeSetup() {
  const [step, setStep] = useState(1);
  const [passphrase, setPassphrase] = useState('');
  const [confirmPassphrase, setConfirmPassphrase] = useState('');
  const [showPassphrase, setShowPassphrase] = useState(false);
  const [dataPath, setDataPath] = useState('~/.trading_dashboard');
  const setIsSetup = useAppStore((state) => state.setIsSetup);
  const { toast } = useToast();

  const handleComplete = () => {
    if (passphrase.length < 8) {
      toast({
        title: "Passphrase too short",
        description: "Please use at least 8 characters",
        variant: "destructive"
      });
      return;
    }
    if (passphrase !== confirmPassphrase) {
      toast({
        title: "Passphrases don't match",
        description: "Please ensure both passphrases are identical",
        variant: "destructive"
      });
      return;
    }
    
    setIsSetup(true);
    toast({
      title: "Setup Complete!",
      description: "Your trading dashboard is ready to use",
    });
  };

  const features = [
    { icon: Shield, title: 'Local-First Security', desc: 'All data encrypted and stored locally' },
    { icon: Zap, title: 'Real-time Monitoring', desc: 'Live updates on all your bots' },
    { icon: Lock, title: 'AES-256 Encryption', desc: 'Bank-grade encryption for your API keys' },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-2xl">
        {step === 1 && (
          <div className="text-center">
            <div className="mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/20">
              <Activity className="h-10 w-10 text-primary-foreground" />
            </div>
            <h1 className="mb-4 text-4xl font-bold text-foreground">
              Welcome to TradingBot Dashboard
            </h1>
            <p className="mb-8 text-lg text-muted-foreground">
              Your local-first, privacy-focused trading bot management system
            </p>

            <div className="mb-8 grid gap-4 md:grid-cols-3">
              {features.map((feature) => (
                <Card key={feature.title} className="border-border bg-card">
                  <CardContent className="p-6 text-center">
                    <feature.icon className="mx-auto mb-3 h-8 w-8 text-primary" />
                    <h3 className="mb-1 font-semibold text-foreground">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.desc}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Button size="lg" onClick={() => setStep(2)} className="px-8">
              Get Started
            </Button>
          </div>
        )}

        {step === 2 && (
          <Card className="border-border bg-card">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-primary/10">
                <Lock className="h-8 w-8 text-primary" />
              </div>
              <CardTitle className="text-2xl">Create Master Passphrase</CardTitle>
              <CardDescription>
                This passphrase will be used to encrypt all your API keys and sensitive data.
                <br />
                <strong className="text-accent">Never share it and store it safely!</strong>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="passphrase">Master Passphrase</Label>
                <div className="relative">
                  <Input
                    id="passphrase"
                    type={showPassphrase ? 'text' : 'password'}
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    placeholder="Enter a strong passphrase"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassphrase(!showPassphrase)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassphrase ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {passphrase.length > 0 && passphrase.length < 8 && (
                  <p className="text-xs text-destructive">Minimum 8 characters required</p>
                )}
                {passphrase.length >= 8 && (
                  <p className="flex items-center gap-1 text-xs text-primary">
                    <Check className="h-3 w-3" /> Strong passphrase
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm">Confirm Passphrase</Label>
                <Input
                  id="confirm"
                  type="password"
                  value={confirmPassphrase}
                  onChange={(e) => setConfirmPassphrase(e.target.value)}
                  placeholder="Confirm your passphrase"
                />
                {confirmPassphrase.length > 0 && passphrase !== confirmPassphrase && (
                  <p className="text-xs text-destructive">Passphrases don't match</p>
                )}
                {confirmPassphrase.length > 0 && passphrase === confirmPassphrase && (
                  <p className="flex items-center gap-1 text-xs text-primary">
                    <Check className="h-3 w-3" /> Passphrases match
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="path">Data Storage Path</Label>
                <div className="relative">
                  <FolderOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="path"
                    value={dataPath}
                    onChange={(e) => setDataPath(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  All configurations and trade history will be stored here
                </p>
              </div>

              <div className="flex gap-3 pt-4">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  Back
                </Button>
                <Button 
                  onClick={handleComplete} 
                  className="flex-1"
                  disabled={passphrase.length < 8 || passphrase !== confirmPassphrase}
                >
                  Complete Setup
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
