'use client';

import { useMemo } from 'react';
import { Minus, TrendingDown, TrendingUp } from 'lucide-react';
import { detectSignal } from '@/lib/analysis';
import type { Signal, SignalType } from '@/lib/analysis';

interface Props {
  prices: number[];
  purchasePrice?: number;
}

// ─── Signal presentation config ───────────────────────────────────────────────

interface SignalCfg {
  label: string;
  bg: string;
  text: string;
  border: string;
}

const SIGNAL_CFG: Record<SignalType, SignalCfg> = {
  strong_buy:  { label: 'Achat fort',  bg: 'bg-emerald-950/50', text: 'text-emerald-400', border: 'border-emerald-700/40' },
  buy:         { label: 'Achat',       bg: 'bg-green-950/50',   text: 'text-green-400',   border: 'border-green-700/40'   },
  hold:        { label: 'Conserver',   bg: 'bg-amber-950/40',   text: 'text-amber-400',   border: 'border-amber-700/40'   },
  sell:        { label: 'Vendre',      bg: 'bg-orange-950/40',  text: 'text-orange-400',  border: 'border-orange-700/40'  },
  strong_sell: { label: 'Vente forte', bg: 'bg-red-950/50',     text: 'text-red-400',     border: 'border-red-700/40'     },
};

function SignalIcon({ type, className }: { type: SignalType; className: string }) {
  if (type === 'strong_buy' || type === 'buy') return <TrendingUp className={className} />;
  if (type === 'strong_sell' || type === 'sell') return <TrendingDown className={className} />;
  return <Minus className={className} />;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function RSIGauge({ rsi }: { rsi: number }) {
  const clamped = Math.min(100, Math.max(0, rsi));
  const dotColor = rsi < 30 ? '#22c55e' : rsi > 70 ? '#ef4444' : '#f59e0b';

  return (
    <div className="space-y-1.5">
      <div className="relative h-1.5 rounded-full bg-zinc-800">
        <div className="absolute inset-y-0 left-0 w-[30%] bg-green-900/50 rounded-l-full" />
        <div className="absolute inset-y-0 right-0 w-[30%] bg-red-900/50 rounded-r-full" />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-zinc-900"
          style={{
            left: `calc(${clamped}% - 6px)`,
            backgroundColor: dotColor,
            boxShadow: `0 0 6px ${dotColor}88`,
          }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-zinc-600">
        <span>Survendu (30)</span>
        <span>Neutre</span>
        <span>Suracheté (70)</span>
      </div>
    </div>
  );
}

function pctClass(value: number): string {
  if (value > 0.02) return 'text-green-400';
  if (value < -0.02) return 'text-red-400';
  return 'text-amber-400';
}

function fmtPct(value: number): string {
  return (value >= 0 ? '+' : '') + (value * 100).toFixed(1) + '%';
}

interface MetricTileProps {
  label: string;
  value: string;
  valueClass?: string;
}

function MetricTile({ label, value, valueClass = 'text-zinc-200' }: MetricTileProps) {
  return (
    <div className="bg-zinc-950 border border-zinc-800/60 rounded-md p-3">
      <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-sm font-semibold tabular-nums ${valueClass}`}>{value}</p>
    </div>
  );
}

function RSILabel({ signal }: { signal: Signal }) {
  const zone =
    signal.rsi < 30 ? 'Survendu' :
    signal.rsi > 70 ? 'Suracheté' :
    'Neutre';
  const cls =
    signal.rsi < 30 ? 'text-green-400' :
    signal.rsi > 70 ? 'text-red-400' :
    'text-amber-400';

  return (
    <div className="flex items-center justify-between mb-2">
      <p className="text-xs text-zinc-500">
        RSI <span className="text-zinc-300 font-medium">{signal.rsi.toFixed(1)}</span>
      </p>
      <span className={`text-xs font-medium ${cls}`}>{zone}</span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TechnicalAnalysis({ prices, purchasePrice }: Props) {
  const signal = useMemo(
    () => detectSignal(prices, purchasePrice),
    [prices, purchasePrice],
  );

  const cfg = SIGNAL_CFG[signal.type];
  const hasEnoughData = prices.length >= 2;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
      <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
        Analyse technique
      </h2>

      {!hasEnoughData ? (
        <p className="text-xs text-zinc-600">Données insuffisantes pour l&apos;analyse.</p>
      ) : (
        <>
          {/* Signal banner */}
          <div
            className={`flex items-start gap-3 px-4 py-3 rounded-lg border ${cfg.bg} ${cfg.border}`}
          >
            <SignalIcon type={signal.type} className={`w-5 h-5 mt-0.5 shrink-0 ${cfg.text}`} />
            <div>
              <p className={`text-sm font-bold leading-none mb-1 ${cfg.text}`}>{cfg.label}</p>
              <p className="text-xs text-zinc-400 leading-relaxed">{signal.message}</p>
            </div>
          </div>

          {/* RSI gauge */}
          <div>
            <RSILabel signal={signal} />
            <RSIGauge rsi={signal.rsi} />
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-2">
            <MetricTile
              label="Momentum 7j"
              value={fmtPct(signal.momentum7d)}
              valueClass={pctClass(signal.momentum7d)}
            />
            <MetricTile
              label="Momentum 30j"
              value={fmtPct(signal.momentum30d)}
              valueClass={pctClass(signal.momentum30d)}
            />
            <MetricTile
              label="Depuis le pic 30j"
              value={fmtPct(signal.fromPeak)}
              valueClass={pctClass(signal.fromPeak)}
            />
            <MetricTile
              label="Tendance MA7 / MA30"
              value={signal.ma7AboveMA30 ? 'Haussière' : 'Baissière'}
              valueClass={signal.ma7AboveMA30 ? 'text-green-400' : 'text-red-400'}
            />
          </div>
        </>
      )}
    </div>
  );
}
