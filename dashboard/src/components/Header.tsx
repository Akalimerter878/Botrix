import { Moon, Sun } from 'lucide-react'
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
}
