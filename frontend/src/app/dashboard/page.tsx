import { 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  Filter, 
  MoreVertical,
  ArrowUpRight
} from 'lucide-react';

// Mock Data
const tickets = [
  { id: 'TKT-2026-001', severity: 'Critical', type: 'Data Exfiltration', source: '192.168.1.45', target: '10.0.0.5', status: 'Open', timestamp: '2 mins ago' },
  { id: 'TKT-2026-002', severity: 'High', type: 'Brute Force SSH', source: '203.0.113.12', target: '192.168.1.10', status: 'Investigating', timestamp: '15 mins ago' },
  { id: 'TKT-2026-003', severity: 'Medium', type: 'Suspicious Port Scan', source: '10.0.0.8', target: '10.0.0.0/24', status: 'Resolved', timestamp: '1 hour ago' },
  { id: 'TKT-2026-004', severity: 'Low', type: 'Policy Violation', source: '192.168.1.105', target: 'External DNS', status: 'Closed', timestamp: '3 hours ago' },
  { id: 'TKT-2026-005', severity: 'Critical', type: 'C2 Communication', source: '192.168.1.50', target: '185.x.x.x', status: 'Open', timestamp: '5 hours ago' },
];

export default function DashboardPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Anomaly Tickets</h1>
          <p className="text-gray-400">Real-time alerts and incident response management.</p>
        </div>
        <div className="flex gap-4">
             <div className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col items-center w-32">
                <span className="text-2xl font-bold text-red-500">2</span>
                <span className="text-xs text-gray-500 uppercase">Critical</span>
             </div>
             <div className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col items-center w-32">
                <span className="text-2xl font-bold text-orange-400">1</span>
                <span className="text-xs text-gray-500 uppercase">Investigating</span>
             </div>
             <div className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col items-center w-32">
                <span className="text-2xl font-bold text-green-500">14</span>
                <span className="text-xs text-gray-500 uppercase">Resolved</span>
             </div>
        </div>
      </header>

      {/* Toolbar */}
      <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl border border-white/10">
        <div className="flex gap-4">
           {/* Search & Filter Placeholders */}
           <input 
             type="text" 
             placeholder="Search tickets..." 
             className="bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 w-64"
           />
           <button className="flex items-center gap-2 px-4 py-2 bg-black/20 border border-white/10 rounded-lg text-sm text-gray-400 hover:text-white transition-colors">
              <Filter size={16} />
              Filter
           </button>
        </div>
        <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-colors">
           Export Report
        </button>
      </div>

      {/* Ticket List */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden glass-panel">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-gray-400 text-xs uppercase tracking-wider bg-black/20">
              <th className="p-6 font-medium">Ticket ID</th>
              <th className="p-6 font-medium">Severity</th>
              <th className="p-6 font-medium">Type</th>
              <th className="p-6 font-medium">Source / Target</th>
              <th className="p-6 font-medium">Status</th>
              <th className="p-6 font-medium">Time</th>
              <th className="p-6 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {tickets.map((ticket) => (
              <tr key={ticket.id} className="hover:bg-white/5 transition-colors group cursor-pointer">
                <td className="p-6 font-mono text-indigo-400 group-hover:text-indigo-300">
                   {ticket.id}
                </td>
                <td className="p-6">
                  <Badge severity={ticket.severity} />
                </td>
                <td className="p-6 font-medium text-white">
                  {ticket.type}
                </td>
                <td className="p-6 text-sm text-gray-300">
                  <div className="flex flex-col">
                    <span className="font-mono text-xs text-gray-400">SRC: {ticket.source}</span>
                    <span className="font-mono text-xs text-gray-400">DST: {ticket.target}</span>
                  </div>
                </td>
                <td className="p-6">
                   <StatusPill status={ticket.status} />
                </td>
                <td className="p-6 text-sm text-gray-500">
                  {ticket.timestamp}
                </td>
                <td className="p-6 text-right">
                  <button className="p-2 hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-white">
                     <ArrowUpRight size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Badge({ severity }: { severity: string }) {
  const colors = {
    'Critical': 'bg-red-500/20 text-red-500 border-red-500/30',
    'High': 'bg-orange-500/20 text-orange-500 border-orange-500/30',
    'Medium': 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30',
    'Low': 'bg-blue-500/20 text-blue-500 border-blue-500/30',
  };
  const colorClass = colors[severity as keyof typeof colors] || colors['Low'];
  
  return (
    <span className={`px-2 py-1 rounded-md text-xs font-medium border ${colorClass} flex items-center gap-1 w-fit`}>
      {severity === 'Critical' && <AlertCircle size={12} />}
      {severity}
    </span>
  );
}

function StatusPill({ status }: { status: string }) {
   const styles = {
      'Open': 'text-red-400 bg-red-400/10',
      'Investigating': 'text-orange-400 bg-orange-400/10',
      'Resolved': 'text-green-400 bg-green-400/10',
      'Closed': 'text-gray-400 bg-gray-400/10',
   };
   const style = styles[status as keyof typeof styles] || styles['Closed'];

   return (
      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${style}`}>
         {status}
      </span>
   )
}
