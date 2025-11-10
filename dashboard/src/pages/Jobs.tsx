import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, RefreshCw, XCircle, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../lib/api';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { Input } from '../components/Input';
import { useWebSocket } from '../hooks/useWebSocket';

export default function Jobs() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [accountCount, setAccountCount] = useState('10');
  const [testMode, setTestMode] = useState(false);
  const queryClient = useQueryClient();

  // Fetch jobs
  const { data: jobs, isLoading, error, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: api.jobs.list,
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
  });

  // WebSocket for real-time updates
  const { connectionState, reconnectAttempts, reconnect } = useWebSocket((message) => {
    if (message.type === 'job_update') {
      // Refetch jobs when we get an update
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      
      const jobId = message.job_id?.slice(0, 8) || 'Unknown';
      
      if (message.status === 'completed') {
        toast.success(`Job #${jobId} completed!`);
      } else if (message.status === 'failed') {
        toast.error(`Job #${jobId} failed`);
      } else if (message.status === 'running') {
        // Optional: Show when job starts
        console.log(`Job #${jobId} is now running`);
      }
    }
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: ({ count, test }: { count: number; test: boolean }) =>
      api.jobs.generate(count, test),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job created successfully');
      setIsCreateModalOpen(false);
      setAccountCount('10');
      setTestMode(false);
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to create job';
      toast.error(errorMessage);
      console.error('Create job error:', error);
    },
  });

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: (id: string) => api.jobs.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job cancelled');
    },
    onError: (error: any) => {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to cancel job';
      toast.error(errorMessage);
      console.error('Cancel job error:', error);
    },
  });

  const handleCreateJob = () => {
    const count = parseInt(accountCount);
    if (isNaN(count) || count < 1 || count > 100) {
      toast.error('Please enter a number between 1 and 100');
      return;
    }
    createJobMutation.mutate({ count, test: testMode });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'running':
        return <Badge variant="info">Running</Badge>;
      case 'failed':
        return <Badge variant="danger">Failed</Badge>;
      case 'pending':
        return <Badge variant="warning">Pending</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'running':
        return <Clock className="w-5 h-5 text-blue-400 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-400" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-400" />;
      default:
        return null;
    }
  };

  const sortedJobs = jobs?.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  ) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Jobs</h1>
          <p className="text-muted-foreground mt-2">Monitor account creation jobs</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="w-4 h-4" />
            New Job
          </Button>
        </div>
      </div>

      {/* WebSocket Status */}
      <div className="glass-panel rounded-lg p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              connectionState === 'connected'
                ? 'bg-green-500 animate-pulse'
                : connectionState === 'reconnecting'
                ? 'bg-yellow-500 animate-pulse'
                : 'bg-red-500'
            }`}
          />
          <div>
            <p className="text-sm font-medium text-foreground">
              {connectionState === 'connected'
                ? 'Real-time updates active'
                : connectionState === 'reconnecting'
                ? `Reconnecting... (attempt ${reconnectAttempts}/10)`
                : 'Disconnected - reconnecting...'}
            </p>
            {connectionState !== 'connected' && (
              <p className="text-xs text-muted-foreground mt-0.5">
                Real-time updates will resume when connection is restored
              </p>
            )}
          </div>
        </div>
        {connectionState === 'disconnected' && (
          <Button
            variant="secondary"
            size="sm"
            onClick={reconnect}
          >
            <RefreshCw className="w-4 h-4" />
            Retry Now
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Total Jobs</p>
          <p className="text-2xl font-bold text-foreground mt-1">{jobs?.length || 0}</p>
        </div>
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Running</p>
          <p className="text-2xl font-bold text-blue-400 mt-1">
            {jobs?.filter((j) => j.status === 'running').length || 0}
          </p>
        </div>
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Completed</p>
          <p className="text-2xl font-bold text-green-400 mt-1">
            {jobs?.filter((j) => j.status === 'completed').length || 0}
          </p>
        </div>
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Failed</p>
          <p className="text-2xl font-bold text-red-400 mt-1">
            {jobs?.filter((j) => j.status === 'failed').length || 0}
          </p>
        </div>
      </div>

      {/* Jobs List */}
      {isLoading ? (
        <div className="glass-panel rounded-lg p-8 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      ) : error ? (
        <div className="glass-panel rounded-lg p-8">
          <div className="flex flex-col items-center gap-4">
            <AlertCircle className="w-12 h-12 text-red-400" />
            <p className="text-center text-foreground font-semibold">Failed to load jobs</p>
            <p className="text-center text-muted-foreground text-sm">
              {error instanceof Error ? error.message : 'Unable to connect to the backend API'}
            </p>
            <Button onClick={() => refetch()} variant="secondary">
              <RefreshCw className="w-4 h-4" />
              Try Again
            </Button>
          </div>
        </div>
      ) : sortedJobs.length === 0 ? (
        <div className="glass-panel rounded-lg p-8">
          <p className="text-center text-muted-foreground">
            No jobs yet. Create your first job to get started!
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedJobs.map((job) => (
            <div key={job.id} className="glass-panel rounded-lg p-6 space-y-4">
              {/* Job Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(job.status)}
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground">Job #{job.id.slice(0, 8)}</h3>
                      {getStatusBadge(job.status)}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      Created {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                {job.status === 'running' && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => cancelJobMutation.mutate(job.id)}
                    disabled={cancelJobMutation.isPending}
                  >
                    <XCircle className="w-4 h-4" />
                    Cancel
                  </Button>
                )}
              </div>

              {/* Progress Bar */}
              {job.status === 'running' && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="text-foreground font-medium">{job.progress}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Job Stats */}
              <div className="grid grid-cols-3 gap-4 pt-2 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground">Total</p>
                  <p className="text-lg font-semibold text-foreground">{job.count}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Created</p>
                  <p className="text-lg font-semibold text-green-400">
                    {job.successful || 0}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Failed</p>
                  <p className="text-lg font-semibold text-red-400">
                    {job.failed || 0}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Job Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Job"
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

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="testMode"
              checked={testMode}
              onChange={(e) => setTestMode(e.target.checked)}
              className="w-4 h-4 rounded border-border bg-secondary text-primary focus:ring-2 focus:ring-ring"
            />
            <label htmlFor="testMode" className="text-sm text-foreground">
              Test mode (don't create real accounts)
            </label>
          </div>

          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-400">
              This will create {accountCount} Kick.com accounts using the email pool.
              {testMode && ' Test mode: No real accounts will be created.'}
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
