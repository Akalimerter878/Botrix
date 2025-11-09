import { Activity, Users, Briefcase, TrendingUp } from 'lucide-react'
import StatsCard from '@/components/StatsCard'
import { Button } from '@/components/Button'

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
            <Button className="w-full">
              Create Accounts
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
