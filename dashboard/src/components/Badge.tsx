import { cn } from '../lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  const variants = {
    default: 'bg-secondary text-secondary-foreground',
    success: 'bg-green-500/10 text-green-400 border-green-500/20 shadow-sm shadow-green-500/10',
    warning: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20 shadow-sm shadow-yellow-500/10',
    danger: 'bg-red-500/10 text-red-400 border-red-500/20 shadow-sm shadow-red-500/10',
    info: 'bg-blue-500/10 text-blue-400 border-blue-500/20 shadow-sm shadow-blue-500/10',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border backdrop-blur-sm',
        'transition-all duration-200 hover:scale-105',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
