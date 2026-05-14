export type SignalType = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';

export interface Signal {
  type: SignalType;
  rsi: number;
  momentum7d: number;
  momentum30d: number;
  fromPeak: number;
  ma7AboveMA30: boolean;
  message: string;
}

// ─── Core indicators ─────────────────────────────────────────────────────────

export function calculateRSI(prices: number[], period = 14): number {
  if (prices.length < period + 1) return NaN;

  const changes = prices.slice(1).map((p, i) => p - prices[i]);

  // Seed: simple average over first `period` changes
  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 0; i < period; i++) {
    const d = changes[i];
    if (d > 0) avgGain += d;
    else avgLoss += -d;
  }
  avgGain /= period;
  avgLoss /= period;

  // Wilder's smoothing for the rest
  for (let i = period; i < changes.length; i++) {
    const d = changes[i];
    avgGain = (avgGain * (period - 1) + Math.max(0, d)) / period;
    avgLoss = (avgLoss * (period - 1) + Math.max(0, -d)) / period;
  }

  if (avgLoss === 0) return 100;
  return 100 - 100 / (1 + avgGain / avgLoss);
}

export function calculateMA(prices: number[], period: number): number[] {
  if (prices.length < period) return [];

  let windowSum = 0;
  for (let i = 0; i < period; i++) windowSum += prices[i];

  const result: number[] = [windowSum / period];
  for (let i = period; i < prices.length; i++) {
    windowSum += prices[i] - prices[i - period];
    result.push(windowSum / period);
  }
  return result;
}

export function calculateBollingerBands(
  prices: number[],
  period = 20,
): { upper: number[]; middle: number[]; lower: number[] } {
  const middle = calculateMA(prices, period);
  const upper: number[] = [];
  const lower: number[] = [];

  for (let i = 0; i < middle.length; i++) {
    const slice = prices.slice(i, i + period);
    const mean = middle[i];
    const variance = slice.reduce((acc, p) => acc + (p - mean) ** 2, 0) / period;
    const stddev = Math.sqrt(variance);
    upper.push(mean + 2 * stddev);
    lower.push(mean - 2 * stddev);
  }

  return { upper, middle, lower };
}

// ─── Signal detection ─────────────────────────────────────────────────────────

// Prices are assumed to be hourly data points (as produced by the backend).
const HOURS_7D = 7 * 24;
const HOURS_30D = 30 * 24;

function momentum(prices: number[], lookback: number): number {
  const ref = prices.at(-lookback) ?? prices.at(0);
  const current = prices.at(-1);
  if (ref == null || current == null || ref === 0) return 0;
  return (current - ref) / ref;
}

function buildMessage(
  type: SignalType,
  rsi: number,
  momentum7d: number,
  fromPeak: number,
  purchasePrice: number | undefined,
  currentPrice: number | undefined,
): string {
  const rsiStr = isNaN(rsi) ? '—' : rsi.toFixed(0);
  const mom7Str = (momentum7d >= 0 ? '+' : '') + (momentum7d * 100).toFixed(1) + '%';
  const peakStr = (fromPeak * 100).toFixed(1) + '%';

  const pnlSuffix =
    purchasePrice != null && currentPrice != null && purchasePrice > 0
      ? ` P&L actuel : ${(((currentPrice - purchasePrice) / purchasePrice) * 100).toFixed(1)}%.`
      : '';

  switch (type) {
    case 'strong_buy':
      return `RSI à ${rsiStr} — zone de survente. Prix ${peakStr} sous le pic 30j. Signal d'achat fort.${pnlSuffix}`;
    case 'buy':
      return `RSI à ${rsiStr} et tendance positive (${mom7Str} sur 7j). Bon moment pour envisager l'achat.${pnlSuffix}`;
    case 'hold':
      return `RSI neutre à ${rsiStr}. Marché équilibré — conserver la position actuelle.${pnlSuffix}`;
    case 'sell':
      return `Momentum faible (${mom7Str} sur 7j) et RSI à ${rsiStr}. Envisager une sortie partielle.${pnlSuffix}`;
    case 'strong_sell':
      return `RSI à ${rsiStr} — zone de surachat. Prendre les bénéfices dès maintenant.${pnlSuffix}`;
  }
}

export function detectSignal(prices: number[], purchasePrice?: number): Signal {
  if (prices.length === 0) {
    return {
      type: 'hold',
      rsi: NaN,
      momentum7d: 0,
      momentum30d: 0,
      fromPeak: 0,
      ma7AboveMA30: false,
      message: 'Données insuffisantes pour l\'analyse.',
    };
  }

  const currentPrice = prices.at(-1)!;
  const rsi = calculateRSI(prices);

  const momentum7d = momentum(prices, HOURS_7D);
  const momentum30d = momentum(prices, HOURS_30D);

  const slice30d = prices.slice(-HOURS_30D);
  const peak30 = Math.max(...(slice30d.length > 0 ? slice30d : prices));
  const fromPeak = peak30 > 0 ? (currentPrice - peak30) / peak30 : 0;

  const ma7 = calculateMA(prices, 7);
  const ma30 = calculateMA(prices, 30);
  const ma7Last = ma7.at(-1) ?? 0;
  const ma30Last = ma30.at(-1) ?? 0;
  const ma7AboveMA30 = ma7Last > ma30Last;

  // Composite score → signal type
  let score = 0;

  if (!isNaN(rsi)) {
    if (rsi < 30) score += 2;
    else if (rsi < 45) score += 1;
    else if (rsi > 70) score -= 2;
    else if (rsi > 55) score -= 1;
  }

  score += ma7AboveMA30 ? 1 : -1;

  if (momentum7d > 0.05) score += 1;
  else if (momentum7d < -0.05) score -= 1;

  let type: SignalType;
  if (score >= 3) type = 'strong_buy';
  else if (score >= 1) type = 'buy';
  else if (score <= -3) type = 'strong_sell';
  else if (score <= -1) type = 'sell';
  else type = 'hold';

  const safeRsi = isNaN(rsi) ? 50 : rsi;

  return {
    type,
    rsi: safeRsi,
    momentum7d,
    momentum30d,
    fromPeak,
    ma7AboveMA30,
    message: buildMessage(type, safeRsi, momentum7d, fromPeak, purchasePrice, currentPrice),
  };
}
