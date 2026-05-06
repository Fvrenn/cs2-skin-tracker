'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart2, Crosshair, List, Settings, TrendingUp } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: BarChart2 },
  { href: '/skins', label: 'Mes Skins', icon: List },
  { href: '/market', label: 'Marché', icon: Crosshair },
  { href: '/settings', label: 'Paramètres', icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 h-full flex flex-col bg-zinc-900 border-r border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-indigo-400" />
          <span className="text-sm font-semibold text-zinc-100">CS2 Tracker</span>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href || (href !== '/dashboard' && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                active
                  ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                  : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 border border-transparent'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
