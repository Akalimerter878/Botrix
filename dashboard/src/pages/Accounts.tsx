import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Download, Trash2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../lib/api';
import { downloadCSV } from '../lib/utils';
import { Table } from '../components/Table';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import type { Account } from '../types';

export default function Accounts() {
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; account?: Account }>({
    isOpen: false,
  });
  const queryClient = useQueryClient();

  // Fetch accounts
  const { data: accounts, isLoading, refetch } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.accounts.list,
  });

  // Delete account mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.accounts.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      toast.success('Account deleted successfully');
      setDeleteModal({ isOpen: false });
    },
    onError: () => {
      toast.error('Failed to delete account');
    },
  });

  // Filter accounts based on search
  const filteredAccounts = accounts?.filter(
    (account) =>
      account.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      account.username.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Export to CSV
  const handleExport = () => {
    if (!filteredAccounts.length) {
      toast.error('No accounts to export');
      return;
    }

    const csvData = filteredAccounts.map((account) => ({
      Email: account.email,
      Username: account.username,
      Status: account.status,
      'Created At': new Date(account.created_at).toLocaleString(),
    }));

    downloadCSV(csvData, 'accounts.csv');
    toast.success('Accounts exported successfully');
  };

  const handleDelete = () => {
    if (deleteModal.account) {
      deleteMutation.mutate(deleteModal.account.id);
    }
  };

  const columns = [
    {
      key: 'email',
      header: 'Email',
      render: (account: Account) => (
        <div className="font-medium">{account.email}</div>
      ),
    },
    {
      key: 'username',
      header: 'Username',
      render: (account: Account) => (
        <div className="text-gray-400">@{account.username}</div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (account: Account) => (
        <Badge
          variant={
            account.status === 'active'
              ? 'success'
              : account.status === 'banned'
              ? 'danger'
              : 'warning'
          }
        >
          {account.status}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created At',
      render: (account: Account) => (
        <div className="text-gray-400">
          {new Date(account.created_at).toLocaleDateString()}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (account: Account) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setDeleteModal({ isOpen: true, account });
          }}
          className="p-2 hover:bg-red-500/20 rounded-lg transition-colors group"
        >
          <Trash2 className="w-4 h-4 text-gray-400 group-hover:text-red-400" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Accounts</h1>
        <p className="text-gray-400 mt-2">Manage your TikTok accounts</p>
      </div>

      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <Input
              placeholder="Search by email or username..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <Button variant="secondary" onClick={handleExport}>
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-gray-400">Total Accounts</p>
          <p className="text-2xl font-bold text-white mt-1">
            {accounts?.length || 0}
          </p>
        </div>
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-gray-400">Active</p>
          <p className="text-2xl font-bold text-green-400 mt-1">
            {accounts?.filter((a) => a.status === 'active').length || 0}
          </p>
        </div>
        <div className="glass-panel rounded-lg p-4">
          <p className="text-sm text-gray-400">Filtered Results</p>
          <p className="text-2xl font-bold text-blue-400 mt-1">
            {filteredAccounts.length}
          </p>
        </div>
      </div>

      {/* Table */}
      <Table
        columns={columns}
        data={filteredAccounts}
        isLoading={isLoading}
        emptyMessage="No accounts found. Create your first account from the Dashboard."
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ isOpen: false })}
        title="Delete Account"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-gray-300">
            Are you sure you want to delete the account{' '}
            <span className="font-semibold text-white">
              {deleteModal.account?.email}
            </span>
            ? This action cannot be undone.
          </p>
          <div className="flex gap-3 justify-end">
            <Button
              variant="secondary"
              onClick={() => setDeleteModal({ isOpen: false })}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
