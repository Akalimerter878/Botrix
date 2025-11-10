import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Save, Key, Upload, Moon, Sun, Info, Eye, EyeOff, Plus, Trash2, Download, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../lib/api';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { FileUpload } from '../components/FileUpload';
import { useTheme } from '../hooks/useTheme';

interface EmailEntry {
  id: string;
  email: string;
  password: string;
}

interface SettingsData {
  rapidApiKey: string;
  kickApiKey: string;
  kasadaApiKey: string;
  hotmailApiKey: string;
  proxyEnabled: boolean;
  proxyUrl: string;
  emailPool: EmailEntry[];
}

const SETTINGS_KEY = 'botrix_settings';

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  
  // Load settings from localStorage
  const loadSettings = (): SettingsData => {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse settings:', e);
      }
    }
    return {
      rapidApiKey: '',
      kickApiKey: '',
      kasadaApiKey: '',
      hotmailApiKey: '',
      proxyEnabled: false,
      proxyUrl: '',
      emailPool: [],
    };
  };

  const [settings, setSettings] = useState<SettingsData>(loadSettings());
  const [showApiKeys, setShowApiKeys] = useState({
    rapid: false,
    kick: false,
    kasada: false,
    hotmail: false,
  });
  
  // Single email add form
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  
  // File import
  const [emailFile, setEmailFile] = useState<File | null>(null);
  const [emailPreview, setEmailPreview] = useState<EmailEntry[]>([]);

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: api.stats.get,
  });

  // Save to localStorage whenever settings change
  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSetting = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveAllSettings = () => {
    if (!settings.rapidApiKey.trim()) {
      toast.error('RapidAPI key is required');
      return;
    }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    toast.success('All settings saved successfully');
  };

  // Email Pool Management
  const handleAddEmail = () => {
    if (!newEmail.trim() || !newPassword.trim()) {
      toast.error('Please enter both email and password');
      return;
    }
    
    if (!newEmail.includes('@')) {
      toast.error('Invalid email format');
      return;
    }

    const newEntry: EmailEntry = {
      id: Date.now().toString(),
      email: newEmail.trim(),
      password: newPassword.trim(),
    };

    setSettings(prev => ({
      ...prev,
      emailPool: [...prev.emailPool, newEntry],
    }));
    
    setNewEmail('');
    setNewPassword('');
    toast.success('Email added to pool');
  };

  const handleRemoveEmail = (id: string) => {
    setSettings(prev => ({
      ...prev,
      emailPool: prev.emailPool.filter(e => e.id !== id),
    }));
    toast.success('Email removed from pool');
  };

  const handleClearAllEmails = () => {
    if (settings.emailPool.length === 0) {
      toast.error('Email pool is already empty');
      return;
    }
    
    if (confirm('Are you sure you want to clear all emails?')) {
      setSettings(prev => ({ ...prev, emailPool: [] }));
      toast.success('Email pool cleared');
    }
  };

  const handleFileSelect = async (file: File) => {
    setEmailFile(file);
    
    const text = await file.text();
    const lines = text.split('\n').filter(line => line.trim());
    
    const validEntries: EmailEntry[] = [];
    const invalidLines: string[] = [];
    
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (trimmed.includes(':') && trimmed.split(':').length === 2) {
        const [email, password] = trimmed.split(':');
        if (email.includes('@') && password.length > 0) {
          validEntries.push({
            id: `${Date.now()}-${index}`,
            email: email.trim(),
            password: password.trim(),
          });
        } else {
          invalidLines.push(`Line ${index + 1}: Invalid format`);
        }
      } else {
        invalidLines.push(`Line ${index + 1}: Invalid format`);
      }
    });
    
    if (invalidLines.length > 0) {
      toast.error(`Found ${invalidLines.length} invalid lines`);
    }
    
    setEmailPreview(validEntries.slice(0, 5));
    toast.success(`Loaded ${validEntries.length} valid email:password pairs`);
  };

  const handleImportEmails = async () => {
    if (!emailFile) {
      toast.error('Please select a file first');
      return;
    }

    const text = await emailFile.text();
    const lines = text.split('\n').filter(line => line.trim());
    
    const newEntries: EmailEntry[] = [];
    
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (trimmed.includes(':') && trimmed.split(':').length === 2) {
        const [email, password] = trimmed.split(':');
        if (email.includes('@') && password.length > 0) {
          newEntries.push({
            id: `${Date.now()}-${index}`,
            email: email.trim(),
            password: password.trim(),
          });
        }
      }
    });

    setSettings(prev => ({
      ...prev,
      emailPool: [...prev.emailPool, ...newEntries],
    }));
    
    toast.success(`Imported ${newEntries.length} emails`);
    setEmailFile(null);
    setEmailPreview([]);
  };

  const handleExportEmails = () => {
    if (settings.emailPool.length === 0) {
      toast.error('No emails to export');
      return;
    }

    const content = settings.emailPool
      .map(entry => `${entry.email}:${entry.password}`)
      .join('\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `email_pool_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('Email pool exported');
  };

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
          <h2 className="text-xl font-semibold text-foreground">API Keys</h2>
        </div>
        
        <div className="space-y-4">
          {/* RapidAPI Key - Required */}
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">
              RapidAPI Key <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Input
                type={showApiKeys.rapid ? 'text' : 'password'}
                placeholder="Enter your RapidAPI key"
                value={settings.rapidApiKey}
                onChange={(e) => updateSetting('rapidApiKey', e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowApiKeys(prev => ({ ...prev, rapid: !prev.rapid }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKeys.rapid ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Kick API Key - Optional */}
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">
              Kick API Key <span className="text-xs text-muted-foreground">(optional)</span>
            </label>
            <div className="relative">
              <Input
                type={showApiKeys.kick ? 'text' : 'password'}
                placeholder="Enter your Kick API key"
                value={settings.kickApiKey}
                onChange={(e) => updateSetting('kickApiKey', e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowApiKeys(prev => ({ ...prev, kick: !prev.kick }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKeys.kick ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Kasada API Key - Optional */}
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">
              Kasada API Key <span className="text-xs text-muted-foreground">(optional)</span>
            </label>
            <div className="relative">
              <Input
                type={showApiKeys.kasada ? 'text' : 'password'}
                placeholder="Enter your Kasada API key"
                value={settings.kasadaApiKey}
                onChange={(e) => updateSetting('kasadaApiKey', e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowApiKeys(prev => ({ ...prev, kasada: !prev.kasada }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKeys.kasada ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Hotmail API Key - Optional */}
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">
              Hotmail API Key <span className="text-xs text-muted-foreground">(optional)</span>
            </label>
            <div className="relative">
              <Input
                type={showApiKeys.hotmail ? 'text' : 'password'}
                placeholder="Enter your Hotmail API key"
                value={settings.hotmailApiKey}
                onChange={(e) => updateSetting('hotmailApiKey', e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowApiKeys(prev => ({ ...prev, hotmail: !prev.hotmail }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiKeys.hotmail ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <Button onClick={handleSaveAllSettings} className="w-full">
            <Save className="w-4 h-4" />
            Save All Settings
          </Button>
          
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-400">
              Get your API key from{' '}
              <a
                href="https://rapidapi.com"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-blue-300"
              >
                RapidAPI
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* Proxy Settings */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Info className="w-5 h-5 text-purple-400" />
          <h2 className="text-xl font-semibold text-foreground">Proxy Settings</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-foreground">Enable Proxy</p>
              <p className="text-sm text-muted-foreground">Use proxy for all requests</p>
            </div>
            <button
              onClick={() => updateSetting('proxyEnabled', !settings.proxyEnabled)}
              className={`
                relative inline-flex h-8 w-14 items-center rounded-full transition-colors
                ${settings.proxyEnabled ? 'bg-primary' : 'bg-secondary'}
              `}
            >
              <span
                className={`
                  inline-block h-6 w-6 transform rounded-full bg-foreground transition-transform
                  ${settings.proxyEnabled ? 'translate-x-7' : 'translate-x-1'}
                `}
                style={{ boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)' }}
              />
            </button>
          </div>

          {settings.proxyEnabled && (
            <Input
              label="Proxy URL"
              placeholder="http://username:password@proxy-host:port"
              value={settings.proxyUrl}
              onChange={(e) => updateSetting('proxyUrl', e.target.value)}
            />
          )}
        </div>
      </div>

      {/* Email Pool Management */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-green-400" />
            <h2 className="text-xl font-semibold text-foreground">Email Pool</h2>
            <span className="text-sm text-muted-foreground">
              ({settings.emailPool.length} emails)
            </span>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleExportEmails} disabled={settings.emailPool.length === 0}>
              <Download className="w-4 h-4" />
              Export
            </Button>
            <Button variant="danger" onClick={handleClearAllEmails} disabled={settings.emailPool.length === 0}>
              <Trash2 className="w-4 h-4" />
              Clear All
            </Button>
          </div>
        </div>
        
        {/* Add Single Email */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-foreground">Add Single Email</h3>
          <div className="flex gap-2">
            <Input
              placeholder="email@example.com"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="flex-1"
            />
            <Input
              type="password"
              placeholder="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="flex-1"
            />
            <Button onClick={handleAddEmail}>
              <Plus className="w-4 h-4" />
              Add
            </Button>
          </div>
        </div>

        {/* Import from File */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-foreground">Import from File</h3>
          <p className="text-sm text-muted-foreground">
            Upload a .txt file with email:password pairs (one per line)
          </p>
          <FileUpload onFileSelect={handleFileSelect} accept=".txt" />
          
          {emailPreview.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-foreground">Preview:</h3>
                <button
                  onClick={() => {
                    setEmailFile(null);
                    setEmailPreview([]);
                  }}
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="bg-secondary rounded-lg p-3 font-mono text-xs space-y-1 max-h-40 overflow-y-auto">
                {emailPreview.map((entry, i) => (
                  <div key={i} className="text-foreground">
                    {entry.email}:***
                  </div>
                ))}
                {emailFile && (
                  <div className="text-muted-foreground mt-2">
                    ... and more
                  </div>
                )}
              </div>
              <Button onClick={handleImportEmails} className="w-full">
                <Upload className="w-4 h-4" />
                Import Emails
              </Button>
            </div>
          )}
        </div>

        {/* Email List */}
        {settings.emailPool.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-foreground">Current Pool:</h3>
            <div className="bg-secondary rounded-lg p-3 space-y-2 max-h-60 overflow-y-auto">
              {settings.emailPool.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between p-2 bg-background/50 rounded hover:bg-background"
                >
                  <span className="text-sm font-mono text-foreground">
                    {entry.email}
                  </span>
                  <button
                    onClick={() => handleRemoveEmail(entry.id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Theme Settings */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          {theme === 'dark' ? (
            <Moon className="w-5 h-5 text-purple-400" />
          ) : (
            <Sun className="w-5 h-5 text-yellow-400" />
          )}
          <h2 className="text-xl font-semibold text-foreground">Theme</h2>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-foreground">Dark Mode</p>
            <p className="text-sm text-muted-foreground">Toggle between light and dark theme</p>
          </div>
          <button
            onClick={toggleTheme}
            className={`
              relative inline-flex h-8 w-14 items-center rounded-full transition-colors
              ${theme === 'dark' ? 'bg-primary' : 'bg-secondary'}
            `}
          >
            <span
              className={`
                inline-block h-6 w-6 transform rounded-full bg-foreground transition-transform
                ${theme === 'dark' ? 'translate-x-7' : 'translate-x-1'}
              `}
              style={{ boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)' }}
            />
          </button>
        </div>
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
            <p className="text-sm text-muted-foreground">Last Sync</p>
            <p className="text-sm font-medium text-foreground mt-1">
              {new Date().toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
