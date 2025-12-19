import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Activity, Loader2, Check, X } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useAppStore } from '@/lib/store';
import axios from 'axios';

const registerSchema = z.object({
  email: z.string()
    .email('Invalid email address'),
  full_name: z.string().optional(),
  password: z.string()
    .min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  timezone: z.string().optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

// Password strength checker
const checkPasswordStrength = (password: string) => {
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
  };
  
  const passed = Object.values(checks).filter(Boolean).length;
  return { checks, strength: passed };
};

export default function Register() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordValue, setPasswordValue] = useState('');
  
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const registerUser = useAppStore((state) => state.register);
  const isSetup = useAppStore((state) => state.isSetup);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const passwordStrength = checkPasswordStrength(passwordValue);

  const onSubmit = async (data: RegisterFormData) => {
    setIsSubmitting(true);
    
    try {
      await registerUser({
        email: data.email,
        password: data.password,
        full_name: data.full_name || undefined,
        timezone: data.timezone || 'UTC',
      });
      
      toast({
        title: 'Account created',
        description: 'Welcome to Trading Bot Platform!',
      });
      
      // Redirect logic - first-time users go to connections setup
      const destination = isSetup ? '/' : '/connections';
      navigate(destination, { replace: true });
      
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        const detail = error.response?.data?.detail;
        
        if (status === 409) {
          toast({
            title: 'Registration Failed',
            description: 'Username or email already exists',
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
            <CardTitle className="text-2xl font-bold">Create Your Account</CardTitle>
            <CardDescription className="mt-2">
              Start your automated trading journey
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
                placeholder="Enter your email"
                {...register('email')}
                disabled={isSubmitting}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            
            {/* Full Name Field (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="full_name">
                Full Name <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="full_name"
                type="text"
                placeholder="Enter your full name"
                {...register('full_name')}
                disabled={isSubmitting}
              />
            </div>
            
            {/* Password Field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Create a password"
                  {...register('password', {
                    onChange: (e) => setPasswordValue(e.target.value),
                  })}
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
              
              {/* Password Strength Indicator */}
              {passwordValue && (
                <div className="space-y-2 pt-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          passwordStrength.strength >= level
                            ? passwordStrength.strength <= 2
                              ? 'bg-destructive'
                              : passwordStrength.strength === 3
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                            : 'bg-muted'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.length ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <X className="h-3 w-3 text-muted-foreground" />
                      )}
                      <span className={passwordStrength.checks.length ? 'text-green-500' : 'text-muted-foreground'}>
                        8+ characters
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.uppercase ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <X className="h-3 w-3 text-muted-foreground" />
                      )}
                      <span className={passwordStrength.checks.uppercase ? 'text-green-500' : 'text-muted-foreground'}>
                        Uppercase
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.lowercase ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <X className="h-3 w-3 text-muted-foreground" />
                      )}
                      <span className={passwordStrength.checks.lowercase ? 'text-green-500' : 'text-muted-foreground'}>
                        Lowercase
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.number ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <X className="h-3 w-3 text-muted-foreground" />
                      )}
                      <span className={passwordStrength.checks.number ? 'text-green-500' : 'text-muted-foreground'}>
                        Number
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* Confirm Password Field */}
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm your password"
                  {...register('confirmPassword')}
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
              )}
            </div>
            
            {/* Submit Button */}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </Button>
          </form>
          
          {/* Login Link */}
          <div className="mt-6 text-center text-sm">
            <span className="text-muted-foreground">Already have an account? </span>
            <Link to="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
