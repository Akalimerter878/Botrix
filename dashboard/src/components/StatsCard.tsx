import { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string
  icon: LucideIcon
  trend?: string
}

export default function StatsCard({ title, value, icon: Icon, trend }: StatsCardProps) {
  return (
    <div className="glass-panel rounded-2xl p-6 hover-lift animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">{title}</p>
          <h3 className="text-3xl font-bold mt-2 bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
            {value}
          </h3>
          {trend && (
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              {trend}
            </p>
          )}
        </div>
        <div className="ml-4 p-3 bg-primary/10 rounded-xl transition-transform duration-300 hover:scale-110">
          <Icon className="h-6 w-6 text-primary" />
        </div>
      </div>
    </div>
  )
}
