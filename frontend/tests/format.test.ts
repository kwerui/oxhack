import { describe, expect, it } from 'vitest';
import { formatMetric } from '../lib/format';

describe('formatMetric', () => {
  it('formats a probability as a whole percentage', () => {
    expect(formatMetric(0.345, 'percent')).toBe('35%');
  });

  it('formats an outcome as British currency', () => {
    expect(formatMetric(40000, 'currency')).toContain('40,000');
  });
});
