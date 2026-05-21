export function toNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatValue(value: number): string {
  if (!Number.isFinite(value)) return "-";
  const abs = Math.abs(value);
  if (abs !== 0 && abs < 0.001) return value.toExponential(3);
  if (abs >= 10000) {
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);
  }
  if (Number.isInteger(value)) return String(value);
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 4 }).format(value);
}

export function formatScore(value: number): string {
  return Number.isFinite(value) ? value.toFixed(4) : "-";
}

export function formatMathValue(value: number): string {
  if (!Number.isFinite(value)) return String.raw`\text{不可用}`;
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 0.001 || abs >= 1_000_000)) {
    const [mantissa, exponent] = value.toExponential(3).split("e");
    return String.raw`${mantissa} \times 10^{${Number(exponent)}}`;
  }
  if (Number.isInteger(value)) return String(value);
  return String(Number(value.toFixed(4)));
}