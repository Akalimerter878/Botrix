import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'

export default function Header() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="h-16 glass-panel border-b border-border/50 backdrop-blur-xl flex items-center justify-between px-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Welcome Back</h2>
        <p className="text-xs text-muted-foreground">Manage your Kick.com accounts</p>
      </div>
      <div className="flex items-center gap-4">
        <button
          onClick={toggleTheme}
          className="p-2 hover:bg-accent/50 rounded-xl transition-all duration-200 hover:scale-110 group"
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5 text-muted-foreground group-hover:text-yellow-400 transition-colors" />
          ) : (
            <Moon className="h-5 w-5 text-muted-foreground group-hover:text-blue-400 transition-colors" />
          )}
        </button>
      </div>
    </header>
  )
}
