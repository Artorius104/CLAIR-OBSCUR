'use client';

import { useEffect, useState } from 'react';
import { Loader2, Shield, ShieldAlert, ShieldCheck, Activity, Wifi, Server } from 'lucide-react';
import { fetchOverview, fetchActions, fetchProtocols, fetchTimeline, type OverviewStats, type ActionBreakdown, type ProtocolBreakdown, type TimelinePoint } from '@/lib/api';

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [actions, setActions] = useState<ActionBreakdown[]>([]);
  const [protocols, setProtocols] = useState<ProtocolBreakdown[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [o, a, p, t] = await Promise.all([
          fetchOverview(), fetchActions(), fetchProtocols(), fetchTimeline(),
        ]);
        setOverview(o);
        setActions(a);
        setProtocols(p);
        setTimeline(t);
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
        <Loader2 size={32} className="animate-spin mr-3" /> Loading analytics...
      </div>
    );
  }

  const maxTimeline = Math.max(...timeline.map(t => t.total), 1);

  return (
    <div className="p-8 space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
        <p className="text-gray-400">Overview of firewall activity and threat metrics.</p>
      </header>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Activity size={20} />} label="Total Events" value={overview?.total_logs ?? 0} color="text-indigo-400" />
        <StatCard icon={<ShieldAlert size={20} />} label="Blocked" value={overview?.total_blocked ?? 0} color="text-red-400" />
        <StatCard icon={<ShieldCheck size={20} />} label="Allowed" value={overview?.total_allowed ?? 0} color="text-green-400" />
        <StatCard icon={<Server size={20} />} label="Unique Sources" value={overview?.unique_src_ips ?? 0} color="text-cyan-400" />
      </div>

      {/* Severity row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
          <p className="text-3xl font-bold text-red-500">{overview?.severity_high ?? 0}</p>
          <p className="text-xs text-red-400/70 uppercase mt-1">High Severity</p>
        </div>
        <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-6 text-center">
          <p className="text-3xl font-bold text-orange-400">{overview?.severity_medium ?? 0}</p>
          <p className="text-xs text-orange-400/70 uppercase mt-1">Medium Severity</p>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6 text-center">
          <p className="text-3xl font-bold text-blue-400">{overview?.severity_low ?? 0}</p>
          <p className="text-xs text-blue-400/70 uppercase mt-1">Low Severity</p>
        </div>
      </div>

      {/* Timeline Chart */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Event Timeline</h2>
        {timeline.length === 0 ? (
          <p className="text-gray-500 text-sm">No timeline data available yet.</p>
        ) : (
          <div className="flex items-end gap-1 h-40">
            {timeline.slice(-48).map((t, i) => (
              <div
                key={i}
                className="flex-1 bg-indigo-500/60 hover:bg-indigo-400/80 rounded-t transition-colors min-w-[4px]"
                style={{ height: `${(t.total / maxTimeline) * 100}%` }}
                title={`${t.hour}: ${t.total} events`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Actions */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>
          <div className="space-y-3">
            {actions.map((a) => {
              const total = actions.reduce((s, x) => s + x.count, 0) || 1;
              const pct = ((a.count / total) * 100).toFixed(1);
              const isDeny = ['DENY', 'DROP', 'REJECT'].includes((a.action || '').toUpperCase());
              return (
                <div key={a.action}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-300">{a.action}</span>
                    <span className="text-gray-500">{a.count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-white/5 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${isDeny ? 'bg-red-500' : 'bg-green-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {actions.length === 0 && <p className="text-gray-500 text-sm">No data.</p>}
          </div>
        </div>

        {/* Protocols */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Protocols</h2>
          <div className="space-y-3">
            {protocols.map((p) => {
              const total = protocols.reduce((s, x) => s + x.count, 0) || 1;
              const pct = ((p.count / total) * 100).toFixed(1);
              return (
                <div key={p.protocol}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-300">{p.protocol}</span>
                    <span className="text-gray-500">{p.count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-white/5 rounded-full h-2">
                    <div className="h-2 rounded-full bg-cyan-500" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
            {protocols.length === 0 && <p className="text-gray-500 text-sm">No data.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-6">
      <div className={`${color} mb-2`}>{icon}</div>
      <p className="text-2xl font-bold text-white">{value.toLocaleString()}</p>
      <p className="text-xs text-gray-500 uppercase mt-1">{label}</p>
    </div>
  );
}
