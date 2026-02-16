'use client';

import { useEffect, useState } from 'react';
import { 
  AlertCircle, 
  Filter, 
  ArrowUpRight,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { fetchLogs, fetchOverview, type Log, type OverviewStats } from '@/lib/api';

export default function DashboardPage() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [logsData, statsData] = await Promise.all([
        fetchLogs({ limit: 50 }),
        fetchOverview(),
      ]);
      setLogs(logsData);
      setStats(statsData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (ts: string | null) => {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return d.toLocaleDateString();
    } catch {
      return ts;
    }
  };

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Anomaly Tickets</h1>
          <p className="text-gray-400">Real-time alerts and incident response management.</p>
        </div>
        <div className="flex gap-4 items-end">
          <button 
            onClick={loadData}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
            title="Refresh"
          >
            <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
          </button>
          <div className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col items-center w-32">
            <span className="text-2xl font-bold text-red-500">{stats?.severity_high ?? '—'}</span>
            <span className="text-xs text-gray-500 uppercase">Critical</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col items-center w-32">
            <span className="text-2xl font-bold text-orange-400">{stats?.severity_medium ?? '—'}</span>
            <span className="text-xs text-gray-500 uppercase">Medium</span>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col items-center w-32">
            <span className="text-2xl font-bold text-green-500">{stats?.total_logs ?? '—'}</span>
            <span className="text-xs text-gray-500 uppercase">Total Logs</span>
          </div>
        </div>
      </header>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">
          ⚠️ {error} — Retrying automatically...
        </div>
      )}

      {/* Ticket List */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden glass-panel">
        {loading && logs.length === 0 ? (
          <div className="flex items-center justify-center py-20 text-gray-500">
            <Loader2 size={24} className="animate-spin mr-3" />
            Loading data...
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-gray-400 text-xs uppercase tracking-wider bg-black/20">
                <th className="p-6 font-medium">ID</th>
                <th className="p-6 font-medium">Severity</th>
                <th className="p-6 font-medium">Action</th>
                <th className="p-6 font-medium">Source / Target</th>
                <th className="p-6 font-medium">Reason</th>
                <th className="p-6 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-white/5 transition-colors group cursor-pointer">
                  <td className="p-6 font-mono text-indigo-400 group-hover:text-indigo-300 text-sm">
                    #{log.id}
                  </td>
                  <td className="p-6">
                    <Badge severity={log.severity} />
                  </td>
                  <td className="p-6">
                    <ActionBadge action={log.action} />
                  </td>
                  <td className="p-6 text-sm text-gray-300">
                    <div className="flex flex-col">
                      <span className="font-mono text-xs text-gray-400">SRC: {log.src_ip || '—'}:{log.src_port ?? ''}</span>
                      <span className="font-mono text-xs text-gray-400">DST: {log.dst_ip || '—'}:{log.dst_port ?? ''}</span>
                    </div>
                  </td>
                  <td className="p-6 text-sm text-gray-300 max-w-xs truncate">
                    {log.reason || '—'}
                  </td>
                  <td className="p-6 text-sm text-gray-500">
                    {formatTime(log.timestamp)}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-gray-500">
                    No logs found. Data will appear once the pipeline processes events.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Badge({ severity }: { severity: string | null }) {
  const colors: Record<string, string> = {
    'High': 'bg-red-500/20 text-red-500 border-red-500/30',
    'Medium': 'bg-orange-500/20 text-orange-500 border-orange-500/30',
    'Low': 'bg-blue-500/20 text-blue-500 border-blue-500/30',
  };
  const colorClass = colors[severity || ''] || colors['Low'];

  return (
    <span className={`px-2 py-1 rounded-md text-xs font-medium border ${colorClass} flex items-center gap-1 w-fit`}>
      {severity === 'High' && <AlertCircle size={12} />}
      {severity || 'Unknown'}
    </span>
  );
}

function ActionBadge({ action }: { action: string | null }) {
  const a = (action || '').toUpperCase();
  const isDeny = ['DENY', 'DROP', 'REJECT'].includes(a);
  const cls = isDeny
    ? 'text-red-400 bg-red-400/10'
    : 'text-green-400 bg-green-400/10';

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${cls}`}>
      {action || '—'}
    </span>
  );
}
