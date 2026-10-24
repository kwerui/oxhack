export function formatMetric(value: number, type: 'percent' | 'currency'): string {
  if (type === 'percent') return `${(value * 100).toFixed(0)}%`;
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(value);
}
