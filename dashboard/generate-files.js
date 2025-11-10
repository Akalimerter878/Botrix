#!/usr/bin/env node
/**
 * Botrix Dashboard - Complete File Generator
 * This script generates all remaining dashboard files
 * Run: node generate-files.js
 */

const fs = require('fs');
const path = require('path');

const files = {
  // Environment variables
  '.env': `VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080/ws`,

  // Vite env types
  'src/vite-env.d.ts': `/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}`,

  // Components - Button
  'src/components/Button.tsx': `import { ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-primary text-primary-foreground hover:bg-primary/90': variant === 'primary',
            'bg-secondary text-secondary-foreground hover:bg-secondary/80': variant === 'secondary',
            'bg-destructive text-destructive-foreground hover:bg-destructive/90': variant === 'danger',
            'hover:bg-accent hover:text-accent-foreground': variant === 'ghost',
          },
          {
            'h-8 px-3 text-sm': size === 'sm',
            'h-10 px-4': size === 'md',
            'h-12 px-6 text-lg': size === 'lg',
          },
          className
        )}
        {...props}
      />
    )
  }
)`,

  // Dashboard page
  'src/pages/Dashboard.tsx': `import { Activity, Users, Briefcase, TrendingUp } from 'lucide-react'
import StatsCard from '@/components/StatsCard'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your Botrix automation system</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Accounts"
          value="0"
          icon={Users}
          trend="+0%"
        />
        <StatsCard
          title="Active Jobs"
          value="0"
          icon={Briefcase}
          trend="0"
        />
        <StatsCard
          title="Success Rate"
          value="0%"
          icon={TrendingUp}
          trend="+0%"
        />
        <StatsCard
          title="24h Activity"
          value="0"
          icon={Activity}
          trend="+0"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="glass rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
          <p className="text-muted-foreground">No recent activity</p>
        </div>
        <div className="glass rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <button className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-md hover:bg-primary/90">
              Create Accounts
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}`,

  // Accounts page
  'src/pages/Accounts.tsx': `export default function Accounts() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Accounts</h1>
        <p className="text-muted-foreground">Manage your created accounts</p>
      </div>
      <div className="glass rounded-lg p-6">
        <p>Accounts page - Implementation in progress</p>
      </div>
    </div>
  )
}`,

  // Jobs page
  'src/pages/Jobs.tsx': `export default function Jobs() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Jobs</h1>
        <p className="text-muted-foreground">Monitor account creation jobs</p>
      </div>
      <div className="glass rounded-lg p-6">
        <p>Jobs page - Implementation in progress</p>
      </div>
    </div>
  )
}`,

  // Settings page
  'src/pages/Settings.tsx': `export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Configure your system</p>
      </div>
      <div className="glass rounded-lg p-6">
        <p>Settings page - Implementation in progress</p>
      </div>
    </div>
  )
}`,

  // Layout component
  'src/components/Layout.tsx': `import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}`,

  // Sidebar component
  'src/components/Sidebar.tsx': `import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, Briefcase, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Accounts', href: '/accounts', icon: Users },
  { name: 'Jobs', href: '/jobs', icon: Briefcase },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <div className="w-64 glass border-r border-border">
      <div className="p-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
          Botrix
        </h1>
      </div>
      <nav className="space-y-1 px-3">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent'
              )}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}`,

  // Header component
  'src/components/Header.tsx': `import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { Button } from './Button'

export default function Header() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="h-16 glass border-b border-border flex items-center justify-between px-6">
      <div>
        <h2 className="text-lg font-semibold">Welcome Back</h2>
      </div>
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>
    </header>
  )
}`,

  // StatsCard component
  'src/components/StatsCard.tsx': `import { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string
  icon: LucideIcon
  trend?: string
}

export default function StatsCard({ title, value, icon: Icon, trend }: StatsCardProps) {
  return (
    <div className="glass rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <h3 className="text-2xl font-bold mt-2">{value}</h3>
          {trend && (
            <p className="text-xs text-green-500 mt-1">{trend}</p>
          )}
        </div>
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
    </div>
  )
}`,
};

// Create files
Object.entries(files).forEach(([filePath, content]) => {
  const fullPath = path.join(__dirname, filePath);
  const dir = path.dirname(fullPath);
  
  // Create directory if it doesn't exist
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  
  // Write file
  fs.writeFileSync(fullPath, content);
  console.log(`✓ Created: ${filePath}`);
});

console.log('\n✅ All files generated successfully!');
console.log('\nNext steps:');
console.log('1. npm run dev');
console.log('2. Open http://localhost:3000');
