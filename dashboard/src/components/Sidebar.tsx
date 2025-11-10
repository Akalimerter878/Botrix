import { Link, useLocation } from 'react-router-dom'
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
    <div className="w-64 glass-panel border-r border-border/50 backdrop-blur-xl">
      <div className="p-6">
        <h1 className="text-2xl font-bold bg-gradient-to-br from-primary via-blue-500 to-purple-600 bg-clip-text text-transparent animate-fade-in">
          Botrix
        </h1>
        <p className="text-xs text-muted-foreground mt-1">Kick.com Automation</p>
      </div>
      <nav className="space-y-1 px-3">
        {navigation.map((item, index) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200',
                'hover:translate-x-1',
                'animate-slide-in',
                isActive
                  ? 'bg-gradient-to-r from-primary to-blue-600 text-white shadow-lg shadow-primary/20'
                  : 'hover:bg-accent/50 text-foreground'
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <item.icon className={cn(
                "h-5 w-5 transition-transform duration-200",
                isActive && "scale-110"
              )} />
              <span className="font-medium">{item.name}</span>
              {isActive && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
              )}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
