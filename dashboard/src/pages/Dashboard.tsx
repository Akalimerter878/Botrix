import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Briefcase, TrendingUp, Activity, Plus } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../lib/api';
import { useWebSocket } from '../hooks/useWebSocket';
import StatsCard from '@/components/StatsCard';
import { Button } from '@/components/Button';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Input } from '../components/Input';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [accountCount, setAccountCount] = useState('10');
  const queryClient = useQueryClient();

  // Fetch statistics from backend
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: api.stats.get,
    refetchInterval: 5000, // Refetch every 5 seconds
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: api.jobs.list,
    refetchInterval: 5000,
  });

  // WebSocket for real-time updates
  useWebSocket((message) => {
    if (message.type === 'job_update') {
      // Refresh stats and jobs when job updates occur
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
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

  // Calculate real statistics from backend data
  const recentJobs = jobs?.slice(0, 5) || [];
  const totalAccounts = stats?.total_accounts || 0;
  const activeJobs = stats?.job_stats?.running || 0;
  const successRate = Math.round(stats?.success_rate || 0);
  const todayAccounts = stats?.account_stats?.created_today || 0;
  const activeAccounts = stats?.account_stats?.active || 0;
  const completedJobs = stats?.job_stats?.completed || 0;

  // Generate real chart data from recent jobs
  const generateChartData = () => {
    if (!jobs || jobs.length === 0) {
      // Return empty data if no jobs
      const data = [];
      const now = new Date();
      for (let i = 23; i >= 0; i--) {
        const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
        data.push({
          time: hour.getHours() + ':00',
          accounts: 0,
        });
      }
      return data;
    }

    // Group jobs by hour for the last 24 hours
    const now = new Date();
    const hourlyData = new Map<number, number>();
    
    // Initialize all hours with 0
    for (let i = 23; i >= 0; i--) {
      const hour = new Date(now.getTime() - i * 60 * 60 * 1000).getHours();
      hourlyData.set(hour, 0);
    }

    // Count successful accounts per hour
    jobs.forEach(job => {
      const jobDate = new Date(job.created_at);
      const hoursDiff = Math.floor((now.getTime() - jobDate.getTime()) / (1000 * 60 * 60));
      
      if (hoursDiff < 24) {
        const hour = jobDate.getHours();
        const current = hourlyData.get(hour) || 0;
        hourlyData.set(hour, current + (job.successful || 0));
      }
    });

    // Convert to chart format
    const data = [];
    for (let i = 23; i >= 0; i--) {
      const hour = new Date(now.getTime() - i * 60 * 60 * 1000).getHours();
      data.push({
        time: hour + ':00',
        accounts: hourlyData.get(hour) || 0,
      });
    }
    
    return data;
  };

  const chartData = generateChartData();

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
        {statsLoading ? (
          // Loading skeletons
          <>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="glass-panel rounded-lg p-6 animate-pulse">
                <div className="h-4 bg-muted rounded w-24 mb-3"></div>
                <div className="h-8 bg-muted rounded w-16 mb-2"></div>
                <div className="h-3 bg-muted rounded w-20"></div>
              </div>
            ))}
          </>
        ) : (
          <>
            <StatsCard
              title="Total Accounts"
              value={totalAccounts.toString()}
              icon={Users}
              trend={`${activeAccounts} active`}
            />
            <StatsCard
              title="Active Jobs"
              value={activeJobs.toString()}
              icon={Briefcase}
              trend={`${completedJobs} completed`}
            />
            <StatsCard
              title="Success Rate"
              value={`${successRate}%`}
              icon={TrendingUp}
              trend={successRate > 80 ? '🎉 Excellent' : successRate > 60 ? '✅ Good' : successRate > 0 ? '⚠️ Needs attention' : 'No data yet'}
            />
            <StatsCard
              title="Today's Activity"
              value={todayAccounts.toString()}
              icon={Activity}
              trend="accounts created today"
            />
          </>
        )}
      </div>

      {/* Activity Chart */}
      <div className="glass-panel rounded-lg p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">24-Hour Activity</h2>
        {jobsLoading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        ) : chartData.every(d => d.accounts === 0) ? (
          <div className="h-64 flex items-center justify-center">
            <p className="text-muted-foreground">No activity in the last 24 hours</p>
          </div>
        ) : (
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
        )}
      </div>

      {/* Recent Jobs & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Jobs */}
        <div className="glass-panel rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Recent Jobs</h2>
          {jobsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-3 bg-card rounded-lg animate-pulse">
                  <div className="h-4 bg-muted rounded w-24 mb-2"></div>
                  <div className="h-3 bg-muted rounded w-32"></div>
                </div>
              ))}
            </div>
          ) : recentJobs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No jobs yet. Create your first job to get started!</p>
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
                      {job.successful || 0} / {job.count} accounts
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
              This will create {accountCount} Kick.com accounts using the email pool.
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
