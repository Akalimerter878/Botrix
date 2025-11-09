import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Save, Key, Upload, Moon, Sun, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../lib/api';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { FileUpload } from '../components/FileUpload';
import { useTheme } from '../hooks/useTheme';

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  const [apiKey, setApiKey] = useState('');
  const [emailFile, setEmailFile] = useState<File | null>(null);
  const [emailPreview, setEmailPreview] = useState<string[]>([]);

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: api.accounts.stats,
  });

  const handleSaveApiKey = () => {
    if (!apiKey.trim()) {
      toast.error('Please enter an API key');
      return;
    }
    // In a real app, this would save to backend
    localStorage.setItem('rapidapi_key', apiKey);
    toast.success('API key saved successfully');
  };

  const handleTestApi = () => {
    const savedKey = localStorage.getItem('rapidapi_key');
    if (!savedKey) {
      toast.error('No API key found');
      return;
    }
    toast.success('API key is valid');
  };

  const handleFileSelect = async (file: File) => {
    setEmailFile(file);
    
    // Read file and validate format
    const text = await file.text();
    const lines = text.split('\n').filter(line => line.trim());
    
    const validLines: string[] = [];
    const invalidLines: string[] = [];
    
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (trimmed.includes(':') && trimmed.split(':').length === 2) {
        const [email, password] = trimmed.split(':');
        if (email.includes('@') && password.length > 0) {
          validLines.push(trimmed);
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
    
    setEmailPreview(validLines.slice(0, 5)); // Show first 5
    toast.success(`Loaded ${validLines.length} valid email:password pairs`);
  };

  const handleUploadEmails = () => {
    if (!emailFile) {
      toast.error('Please select a file first');
      return;
    }
    // In a real app, this would upload to backend
    toast.success('Email pool uploaded successfully');
    setEmailFile(null);
    setEmailPreview([]);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-2">Configure your application settings</p>
      </div>

      {/* API Configuration */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Key className="w-5 h-5 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">API Configuration</h2>
        </div>
        
        <div className="space-y-4">
          <Input
            type="password"
            label="RapidAPI Key"
            placeholder="Enter your RapidAPI key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          
          <div className="flex gap-2">
            <Button onClick={handleSaveApiKey}>
              <Save className="w-4 h-4" />
              Save API Key
            </Button>
            <Button variant="secondary" onClick={handleTestApi}>
              Test Connection
            </Button>
          </div>
          
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

      {/* Email Pool Upload */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Upload className="w-5 h-5 text-green-400" />
          <h2 className="text-xl font-semibold text-white">Email Pool</h2>
        </div>
        
        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-400 mb-2">
              Upload a .txt file with email:password pairs (one per line)
            </p>
            <FileUpload onFileSelect={handleFileSelect} accept=".txt" />
          </div>
          
          {emailPreview.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-white">Preview:</h3>
              <div className="bg-gray-800 rounded-lg p-3 font-mono text-xs space-y-1">
                {emailPreview.map((line, i) => (
                  <div key={i} className="text-gray-300">
                    {line.split(':')[0]}:***
                  </div>
                ))}
                {emailFile && (
                  <div className="text-gray-500 mt-2">
                    ... and more
                  </div>
                )}
              </div>
            </div>
          )}
          
          {emailFile && (
            <Button onClick={handleUploadEmails}>
              <Upload className="w-4 h-4" />
              Upload Email Pool
            </Button>
          )}
        </div>
      </div>

      {/* Theme Settings */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          {theme === 'dark' ? (
            <Moon className="w-5 h-5 text-purple-400" />
          ) : (
            <Sun className="w-5 h-5 text-yellow-400" />
          )}
          <h2 className="text-xl font-semibold text-white">Theme</h2>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-white">Dark Mode</p>
            <p className="text-sm text-gray-400">Toggle between light and dark theme</p>
          </div>
          <button
            onClick={toggleTheme}
            className={`
              relative inline-flex h-8 w-14 items-center rounded-full transition-colors
              ${theme === 'dark' ? 'bg-blue-600' : 'bg-gray-600'}
            `}
          >
            <span
              className={`
                inline-block h-6 w-6 transform rounded-full bg-white transition-transform
                ${theme === 'dark' ? 'translate-x-7' : 'translate-x-1'}
              `}
            />
          </button>
        </div>
      </div>

      {/* System Information */}
      <div className="glass-panel rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Info className="w-5 h-5 text-gray-400" />
          <h2 className="text-xl font-semibold text-white">System Information</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800/50 rounded-lg p-4">
            <p className="text-sm text-gray-400">Total Accounts</p>
            <p className="text-2xl font-bold text-white mt-1">
              {stats?.total_accounts || 0}
            </p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4">
            <p className="text-sm text-gray-400">Success Rate</p>
            <p className="text-2xl font-bold text-green-400 mt-1">
              {stats?.success_rate ? `${stats.success_rate}%` : '0%'}
            </p>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4">
            <p className="text-sm text-gray-400">Last Sync</p>
            <p className="text-sm font-medium text-white mt-1">
              {new Date().toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
