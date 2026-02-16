import Link from 'next/link';
import { 
  LayoutDashboard, 
  ShieldAlert, 
  Activity, 
  Settings, 
  LogOut,
  Search
} from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/10 flex flex-col glass-effect">
        <div className="p-6 border-b border-white/10">
          <Link href="/" className="text-2xl font-bold tracking-tighter hover:text-gray-300 transition-colors">
            CLAIR OBSCUR
          </Link>
          <p className="text-xs text-gray-500 mt-1">NDR Platform</p>
        </div>
        
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          <StatusBadge />
          
          <div className="pt-4">
            <p className="px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Monitoring
            </p>
            <NavLink href="/dashboard" icon={<ShieldAlert size={20} />} label="Anomaly Tickets" active />
            <NavLink href="/dashboard/analytics" icon={<LayoutDashboard size={20} />} label="Analytics" />
            <NavLink href="/dashboard/logs" icon={<Search size={20} />} label="Log Search" />
            <NavLink href="/dashboard/network" icon={<Activity size={20} />} label="Network Map" />
          </div>

          <div className="pt-8">
             <p className="px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              System
            </p>
            <NavLink href="/dashboard/settings" icon={<Settings size={20} />} label="Settings" />
          </div>
        </nav>

        <div className="p-4 border-t border-white/10">
           <button className="flex items-center gap-3 px-4 py-2 w-full text-left text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
            <LogOut size={20} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-gradient-to-br from-black to-gray-900 relative">
         <div className="absolute inset-0 pointer-events-none bg-[url('/grid.svg')] opacity-10"></div>
        {children}
      </main>
    </div>
  );
}

function NavLink({ href, icon, label, active = false }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <Link 
      href={href} 
      className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
        active 
          ? 'bg-white/10 text-white border-l-2 border-indigo-500' 
          : 'text-gray-400 hover:text-white hover:bg-white/5'
      }`}
    >
      {icon}
      <span>{label}</span>
    </Link>
  );
}

function StatusBadge() {
  return (
     <div className="mx-4 mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center gap-3">
        <div className="relative">
           <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
           <div className="absolute inset-0 w-2 h-2 rounded-full bg-green-500 animate-ping opacity-50"></div>
        </div>
        <div className="flex flex-col">
           <span className="text-xs font-medium text-green-400">System Healthy</span>
           <span className="text-[10px] text-green-500/60">99.9% Uptime</span>
        </div>
     </div>
  )
}
