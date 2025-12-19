import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Activity, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast';
import { useAppStore } from '@/lib/store';
import { LoginData } from '@/lib/api/auth';
import axios from 'axios';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  
  const login = useAppStore((state) => state.login);
  const isSetup = useAppStore((state) => state.isSetup);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // Load remembered email on mount
  useEffect(() => {
    const rememberedEmail = localStorage.getItem('remembered_email');
    if (rememberedEmail) {
      setValue('email', rememberedEmail);
      setRememberMe(true);
    }
  }, [setValue]);

  const onSubmit = async (data: LoginFormData) => {
    setIsSubmitting(true);
    
    try {
      await login(data as LoginData);
      
      // Handle remember me
      if (rememberMe) {
        localStorage.setItem('remembered_email', data.email);
      } else {
        localStorage.removeItem('remembered_email');
      }
      
      toast({
        title: 'Login successful',
        description: 'Welcome back!',
      });
      
      // Redirect logic
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname;
      const destination = from || (isSetup ? '/' : '/connections');
      navigate(destination, { replace: true });
      
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const detail = error.response?.data?.detail;
        
        if (status === 401) {
          toast({
            title: 'Login Failed',
            description: 'Invalid username or password',
            variant: 'destructive',
          });
        } else if (status === 400 || status === 422) {
          toast({
            title: 'Invalid Input',
            description: detail || 'Please check your input',
            variant: 'destructive',
          });
        } else {
          toast({
            title: 'Connection Error',
            description: 'Could not connect to server. Please try again.',
            variant: 'destructive',
          });
        }
      } else {
        toast({
          title: 'Error',
          description: 'An unexpected error occurred',
          variant: 'destructive',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotPassword = () => {
    toast({
      title: 'Feature Coming Soon',
      description: 'Password reset functionality will be available soon.',
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-4">
          {/* Logo */}
          <div className="flex justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary">
              <Activity className="h-6 w-6 text-primary-foreground" />
            </div>
          </div>
          <div>
            <CardTitle className="text-2xl font-bold">Trading Bot Platform</CardTitle>
            <CardDescription className="mt-2">
              Sign in to your account to continue
            </CardDescription>
          </div>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="Enter your email address"
                {...register('email')}
                disabled={isSubmitting}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            
            {/* Password Field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  {...register('password')}
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            
            {/* Remember Me & Forgot Password */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remember"
                  checked={rememberMe}
                  onCheckedChange={(checked) => setRememberMe(checked as boolean)}
                  disabled={isSubmitting}
                />
                <Label htmlFor="remember" className="text-sm font-normal cursor-pointer">
                  Remember me
                </Label>
              </div>
              <button
                type="button"
                onClick={handleForgotPassword}
                className="text-sm text-primary hover:underline"
              >
                Forgot password?
              </button>
            </div>
            
            {/* Submit Button */}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>
          
          {/* Register Link */}
          <div className="mt-6 text-center text-sm">
            <span className="text-muted-foreground">Don't have an account? </span>
            <Link to="/register" className="text-primary hover:underline font-medium">
              Create account
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
