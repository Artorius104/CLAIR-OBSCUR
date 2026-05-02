'use client';

import { useEffect, useState } from 'react';
import { Search, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchLogs, type Log } from '@/lib/api';

const PAGE_SIZE = 50;

export default function LogSearchPage() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('');
  const [action, setAction] = useState('');
  const [page, setPage] = useState(0);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await fetchLogs({
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        severity: severity || undefined,
        action: action || undefined,
        search: search || undefined,
      });
      setLogs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, severity, action]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    loadData();
  };

  return (
    <div className="p-8 space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Log Search</h1>
        <p className="text-gray-400">Search and filter firewall logs.</p>
      </header>

      {/* Filters */}
      <form onSubmit={handleSearch} className="flex gap-4 flex-wrap bg-white/5 p-4 rounded-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <Search size={16} className="text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by IP, reason, firewall..."
            className="bg-transparent border-none focus:outline-none text-white text-sm w-full"
          />
        </div>
        <select
          value={severity}
          onChange={(e) => { setSeverity(e.target.value); setPage(0); }}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Severity</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <select
          value={action}
          onChange={(e) => { setAction(e.target.value); setPage(0); }}
          className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Actions</option>
          <option value="ALLOW">ALLOW</option>
          <option value="DENY">DENY</option>
          <option value="DROP">DROP</option>
        </select>
        <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-colors">
          Search
        </button>
      </form>

      {/* Table */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden glass-panel">
        {loading ? (
          <div className="flex items-center justify-center py-20 text-gray-500">
            <Loader2 size={24} className="animate-spin mr-3" /> Loading...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/10 text-gray-400 text-xs uppercase tracking-wider bg-black/20">
                  <th className="p-4 font-medium">Timestamp</th>
                  <th className="p-4 font-medium">Firewall</th>
                  <th className="p-4 font-medium">Source</th>
                  <th className="p-4 font-medium">Destination</th>
                  <th className="p-4 font-medium">Protocol</th>
                  <th className="p-4 font-medium">Action</th>
                  <th className="p-4 font-medium">Severity</th>
                  <th className="p-4 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4 text-gray-400 font-mono text-xs whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </td>
                    <td className="p-4 text-gray-300">{log.firewall_id || '—'}</td>
                    <td className="p-4 font-mono text-xs text-gray-300">{log.src_ip}:{log.src_port}</td>
                    <td className="p-4 font-mono text-xs text-gray-300">{log.dst_ip}:{log.dst_port}</td>
                    <td className="p-4 text-cyan-400">{log.protocol || '—'}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        ['DENY','DROP','REJECT'].includes((log.action||'').toUpperCase()) ? 'text-red-400 bg-red-400/10' : 'text-green-400 bg-green-400/10'
                      }`}>{log.action || '—'}</span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-md text-xs font-medium border ${
                        log.severity === 'High' ? 'bg-red-500/20 text-red-500 border-red-500/30'
                        : log.severity === 'Medium' ? 'bg-orange-500/20 text-orange-500 border-orange-500/30'
                        : 'bg-blue-500/20 text-blue-500 border-blue-500/30'
                      }`}>{log.severity || '—'}</span>
                    </td>
                    <td className="p-4 text-gray-400 max-w-[200px] truncate">{log.reason || '—'}</td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr><td colSpan={8} className="p-12 text-center text-gray-500">No logs matching your criteria.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => setPage(Math.max(0, page - 1))}
          disabled={page === 0}
          className="flex items-center gap-1 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
        >
          <ChevronLeft size={16} /> Previous
        </button>
        <span className="text-gray-500 text-sm">Page {page + 1}</span>
        <button
          onClick={() => setPage(page + 1)}
          disabled={logs.length < PAGE_SIZE}
          className="flex items-center gap-1 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
