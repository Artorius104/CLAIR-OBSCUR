'use client';

import { useEffect, useState } from 'react';
import { Loader2, AlertTriangle, Wifi } from 'lucide-react';
import { fetchSuspiciousIPs, fetchTopPorts, type SuspiciousIP, type TopPort } from '@/lib/api';

export default function NetworkPage() {
  const [ips, setIps] = useState<SuspiciousIP[]>([]);
  const [ports, setPorts] = useState<TopPort[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [i, p] = await Promise.all([fetchSuspiciousIPs(), fetchTopPorts()]);
        setIps(i);
        setPorts(p);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <Loader2 size={32} className="animate-spin mr-3" /> Loading network data...
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Network Map</h1>
        <p className="text-gray-400">Suspicious IPs and active port analysis.</p>
      </header>

      {/* Suspicious IPs */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex items-center gap-2">
          <AlertTriangle size={20} className="text-red-400" />
          <h2 className="text-lg font-semibold text-white">Suspicious IPs</h2>
        </div>
        {ips.length === 0 ? (
          <p className="p-8 text-gray-500 text-center">No suspicious IPs detected yet.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-gray-400 text-xs uppercase tracking-wider bg-black/20">
                <th className="p-4 font-medium">IP Address</th>
                <th className="p-4 font-medium">Type</th>
                <th className="p-4 font-medium">Blocked Count</th>
                <th className="p-4 font-medium">Risk Level</th>
                <th className="p-4 font-medium">Last Blocked</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {ips.map((ip, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="p-4 font-mono text-indigo-400">{ip.ip_address}</td>
                  <td className="p-4 text-gray-300">{ip.ip_type}</td>
                  <td className="p-4 text-white font-semibold">{ip.blocked_count}</td>
                  <td className="p-4">
                    <RiskBadge level={ip.risk_level} />
                  </td>
                  <td className="p-4 text-gray-500 text-xs">
                    {ip.last_blocked ? new Date(ip.last_blocked).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Top Ports */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex items-center gap-2">
          <Wifi size={20} className="text-cyan-400" />
          <h2 className="text-lg font-semibold text-white">Top Ports</h2>
        </div>
        {ports.length === 0 ? (
          <p className="p-8 text-gray-500 text-center">No port data available yet.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-gray-400 text-xs uppercase tracking-wider bg-black/20">
                <th className="p-4 font-medium">Port</th>
                <th className="p-4 font-medium">Type</th>
                <th className="p-4 font-medium">Protocol</th>
                <th className="p-4 font-medium">Connections</th>
                <th className="p-4 font-medium">Last Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {ports.map((p, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="p-4 font-mono text-cyan-400 font-semibold">{p.port}</td>
                  <td className="p-4 text-gray-300">{p.port_type}</td>
                  <td className="p-4 text-gray-300">{p.protocol}</td>
                  <td className="p-4 text-white font-semibold">{p.total_connections.toLocaleString()}</td>
                  <td className="p-4 text-gray-500 text-xs">
                    {p.last_seen ? new Date(p.last_seen).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function RiskBadge({ level }: { level: string | null }) {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-500/20 text-red-500 border-red-500/30',
    HIGH: 'bg-orange-500/20 text-orange-500 border-orange-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30',
    LOW: 'bg-blue-500/20 text-blue-500 border-blue-500/30',
  };
  const cls = colors[(level || '').toUpperCase()] || colors.LOW;
  return (
    <span className={`px-2 py-1 rounded-md text-xs font-medium border ${cls}`}>
      {level || 'Unknown'}
    </span>
  );
}
