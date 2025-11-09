import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Briefcase, TrendingUp, Activity, Plus } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../lib/api';
import StatsCard from '@/components/StatsCard';
import { Button } from '@/components/Button';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Input } from '../components/Input';
import toast from 'react-hot-toast';

// Mock data for 24h activity chart
const generateChartData = () => {
  const data = [];
  const now = new Date();
  for (let i = 23; i >= 0; i--) {
    const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
    data.push({
      time: hour.getHours() + ':00',
      accounts: Math.floor(Math.random() * 20) + 5,
    });
  }
  return data;
};

export default function Dashboard() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [accountCount, setAccountCount] = useState('10');
  const queryClient = useQueryClient();

  // Fetch data
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: api.accounts.stats,
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: api.jobs.list,
  });

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.accounts.list,
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: (count: number) => api.jobs.generate(count, false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job created successfully');
      setIsCreateModalOpen(false);
      setAccountCount('10');
    },
    onError: () => {
      toast.error('Failed to create job');
    },
  });

  const handleCreateJob = () => {
    const count = parseInt(accountCount);
    if (isNaN(count) || count < 1 || count > 100) {
      toast.error('Please enter a number between 1 and 100');
      return;
    }
    createJobMutation.mutate(count);
  };

  const recentJobs = jobs?.slice(0, 5) || [];
  const chartData = generateChartData();
  const runningJobs = jobs?.filter((j) => j.status === 'running').length || 0;
  const totalAccounts = accounts?.length || 0;
  const activeAccounts = accounts?.filter((a) => a.status === 'active').length || 0;
  const successRate = totalAccounts > 0 ? Math.round((activeAccounts / totalAccounts) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-2">Welcome back! Here's your overview</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="w-4 h-4" />
          Create Accounts
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Accounts"
          value={totalAccounts.toString()}
          icon={Users}
          trend={`${activeAccounts} active`}
        />
        <StatsCard
          title="Active Jobs"
          value={runningJobs.toString()}
          icon={Briefcase}
          trend={`${jobs?.length || 0} total`}
        />
        <StatsCard
          title="Success Rate"
          value={`${successRate}%`}
          icon={TrendingUp}
          trend={successRate > 80 ? '🎉 Excellent' : successRate > 60 ? '✅ Good' : '⚠️ Needs attention'}
        />
        <StatsCard
          title="24h Activity"
          value={chartData.reduce((sum, d) => sum + d.accounts, 0).toString()}
          icon={Activity}
          trend="accounts created"
        />
      </div>

      {/* Activity Chart */}
      <div className="glass-panel rounded-lg p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">24-Hour Activity</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="time"
                className="stroke-muted-foreground"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis className="stroke-muted-foreground" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))',
                }}
              />
              <Line
                type="monotone"
                dataKey="accounts"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ fill: 'hsl(var(--primary))', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Jobs & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Jobs */}
        <div className="glass-panel rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Recent Jobs</h2>
          {recentJobs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No jobs yet</p>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-3 bg-card rounded-lg hover:bg-card-hover transition-colors"
                >
                  <div>
                    <p className="font-medium text-foreground">
                      Job #{job.id.slice(0, 8)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {job.created_count || 0} / {job.count} accounts
                    </p>
                  </div>
                  <Badge
                    variant={
                      job.status === 'completed'
                        ? 'success'
                        : job.status === 'running'
                        ? 'info'
                        : job.status === 'failed'
                        ? 'danger'
                        : 'warning'
                    }
                  >
                    {job.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="glass-panel rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="w-full p-4 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all text-left"
            >
              <div className="flex items-center gap-3">
                <Plus className="w-5 h-5 text-white" />
                <div>
                  <p className="font-medium text-white">Create Accounts</p>
                  <p className="text-sm text-blue-100">Start a new job</p>
                </div>
              </div>
            </button>

            <a
              href="/accounts"
              className="block w-full p-4 bg-card rounded-lg hover:bg-card-hover transition-colors"
            >
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-muted-foreground" />
                <div>
                  <p className="font-medium text-foreground">View Accounts</p>
                  <p className="text-sm text-muted-foreground">Manage your accounts</p>
                </div>
              </div>
            </a>

            <a
              href="/jobs"
              className="block w-full p-4 bg-card rounded-lg hover:bg-card-hover transition-colors"
            >
              <div className="flex items-center gap-3">
                <Briefcase className="w-5 h-5 text-muted-foreground" />
                <div>
                  <p className="font-medium text-foreground">Monitor Jobs</p>
                  <p className="text-sm text-muted-foreground">Check job status</p>
                </div>
              </div>
            </a>
          </div>
        </div>
      </div>

      {/* Create Job Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Accounts"
        size="sm"
      >
        <div className="space-y-4">
          <Input
            type="number"
            label="Number of Accounts"
            placeholder="Enter number (1-100)"
            value={accountCount}
            onChange={(e) => setAccountCount(e.target.value)}
            min="1"
            max="100"
          />

          <div className="p-3 bg-primary/10 border border-primary/30 rounded-lg">
            <p className="text-sm text-primary">
              This will create {accountCount} TikTok accounts using the email pool.
            </p>
          </div>

          <div className="flex gap-3 justify-end pt-4">
            <Button
              variant="secondary"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateJob}
              disabled={createJobMutation.isPending}
            >
              {createJobMutation.isPending ? 'Creating...' : 'Create Job'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
