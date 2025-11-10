import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, Key, Mail, Server, Info, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../lib/api';
import { Button } from '../components/Button';
import { Input } from '../components/Input';

interface SettingsData {
  rapidapi_key: string;
  imap_server: string;
  imap_port: number;
  imap_username: string;
  imap_password: string;
  smtp_server: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  proxy_url: string;
  worker_count: number;
  retry_count: number;
  timeout: number;
}

export default function Settings() {
  const queryClient = useQueryClient();
  
  const [showPasswords, setShowPasswords] = useState({
    rapidapi: false,
    imap: false,
    smtp: false,
  });

  // Fetch settings from backend
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: api.settings.get,
    retry: 2,
  });

  // Local state for form
  const [formData, setFormData] = useState<Partial<SettingsData>>({
    rapidapi_key: '',
    imap_server: 'imap.gmail.com',
    imap_port: 993,
    imap_username: '',
    imap_password: '',
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    proxy_url: '',
    worker_count: 1,
    retry_count: 3,
    timeout: 30,
  });

  // Update form when settings are loaded
  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  // Mutation for saving settings
  const saveMutation = useMutation({
    mutationFn: api.settings.save,
    onSuccess: () => {
      toast.success('Settings saved successfully');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to save settings');
    },
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: api.stats.get,
  });

  const updateField = (field: keyof SettingsData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    if (!formData.rapidapi_key?.trim()) {
      toast.error('RapidAPI key is required');
      return;
    }
    saveMutation.mutate(formData);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-2">Configure your application settings</p>
      </div>

      {/* API Configuration */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Key className="w-5 h-5 text-blue-400" />
          <h2 className="text-xl font-semibold text-foreground">API Configuration</h2>
        </div>
        
        <div className="space-y-4">
          {/* RapidAPI Key - Required */}
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">
              RapidAPI Key <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Input
                type={showPasswords.rapidapi ? 'text' : 'password'}
                placeholder="Enter your RapidAPI key"
                value={formData.rapidapi_key || ''}
                onChange={(e) => updateField('rapidapi_key', e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPasswords(prev => ({ ...prev, rapidapi: !prev.rapidapi }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPasswords.rapidapi ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Required for Kasada solving. Get your key from{' '}
              <a
                href="https://rapidapi.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:underline"
              >
                RapidAPI
              </a>
            </p>
          </div>

          {/* Proxy URL */}
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">
              Proxy URL <span className="text-xs text-muted-foreground">(optional)</span>
            </label>
            <Input
              placeholder="http://username:password@proxy-host:port"
              value={formData.proxy_url || ''}
              onChange={(e) => updateField('proxy_url', e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Email Configuration (IMAP) */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-green-400" />
          <h2 className="text-xl font-semibold text-foreground">IMAP Configuration</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="IMAP Server"
            placeholder="imap.gmail.com"
            value={formData.imap_server || ''}
            onChange={(e) => updateField('imap_server', e.target.value)}
          />
          <Input
            label="IMAP Port"
            type="number"
            placeholder="993"
            value={formData.imap_port || 993}
            onChange={(e) => updateField('imap_port', parseInt(e.target.value) || 993)}
          />
          <Input
            label="IMAP Username"
            placeholder="your-email@gmail.com"
            value={formData.imap_username || ''}
            onChange={(e) => updateField('imap_username', e.target.value)}
          />
          <div className="relative">
            <Input
              label="IMAP Password"
              type={showPasswords.imap ? 'text' : 'password'}
              placeholder="••••••••"
              value={formData.imap_password || ''}
              onChange={(e) => updateField('imap_password', e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPasswords(prev => ({ ...prev, imap: !prev.imap }))}
              className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
            >
              {showPasswords.imap ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Email Configuration (SMTP) */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-purple-400" />
          <h2 className="text-xl font-semibold text-foreground">SMTP Configuration</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="SMTP Server"
            placeholder="smtp.gmail.com"
            value={formData.smtp_server || ''}
            onChange={(e) => updateField('smtp_server', e.target.value)}
          />
          <Input
            label="SMTP Port"
            type="number"
            placeholder="587"
            value={formData.smtp_port || 587}
            onChange={(e) => updateField('smtp_port', parseInt(e.target.value) || 587)}
          />
          <Input
            label="SMTP Username"
            placeholder="your-email@gmail.com"
            value={formData.smtp_username || ''}
            onChange={(e) => updateField('smtp_username', e.target.value)}
          />
          <div className="relative">
            <Input
              label="SMTP Password"
              type={showPasswords.smtp ? 'text' : 'password'}
              placeholder="••••••••"
              value={formData.smtp_password || ''}
              onChange={(e) => updateField('smtp_password', e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPasswords(prev => ({ ...prev, smtp: !prev.smtp }))}
              className="absolute right-3 top-[38px] text-muted-foreground hover:text-foreground"
            >
              {showPasswords.smtp ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Worker Configuration */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Info className="w-5 h-5 text-orange-400" />
          <h2 className="text-xl font-semibold text-foreground">Worker Configuration</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Input
            label="Worker Count"
            type="number"
            min="1"
            max="10"
            placeholder="1"
            value={formData.worker_count || 1}
            onChange={(e) => updateField('worker_count', parseInt(e.target.value) || 1)}
          />
          <Input
            label="Retry Count"
            type="number"
            min="1"
            max="10"
            placeholder="3"
            value={formData.retry_count || 3}
            onChange={(e) => updateField('retry_count', parseInt(e.target.value) || 3)}
          />
          <Input
            label="Timeout (seconds)"
            type="number"
            min="10"
            max="120"
            placeholder="30"
            value={formData.timeout || 30}
            onChange={(e) => updateField('timeout', parseInt(e.target.value) || 30)}
          />
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button 
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="min-w-[200px]"
        >
          <Save className="w-4 h-4" />
          {saveMutation.isPending ? 'Saving...' : 'Save All Settings'}
        </Button>
      </div>

      {/* System Information */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Info className="w-5 h-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold text-foreground">System Information</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-secondary/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Total Accounts</p>
            <p className="text-2xl font-bold text-foreground mt-1">
              {stats?.total_accounts || 0}
            </p>
          </div>
          <div className="bg-secondary/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Success Rate</p>
            <p className="text-2xl font-bold text-green-400 mt-1">
              {stats?.success_rate ? `${stats.success_rate}%` : '0%'}
            </p>
          </div>
          <div className="bg-secondary/50 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Last Updated</p>
            <p className="text-sm font-medium text-foreground mt-1">
              {new Date().toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
