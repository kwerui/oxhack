import { describe, expect, it } from 'vitest';
import { applyLocationSelection, compareEvaluatedExperiments, CUSTOM_FEATURES, differsFromEvaluatedExperiment, evaluatedPeriods, PRESET_FEATURES, formatReverseGeocodedLabel, toggleFeature } from '../lib/experimentBuilder';
import type { ModelResult } from '../lib/aurora';

const evaluated: ModelResult = {
  horizonHours: 24, location: 'Reykjavík, Iceland', coordinates: { latitude: 64.15, longitude: -21.94 },
  features: PRESET_FEATURES.space, label: 'label', model: 'Logistic Regression', modelSelection: 'compare',
  trainCount: 1, validationCount: 1, testCount: 1, trainFrom: '2024-01-01', trainUntil: '2024-12-31', validationFrom: '2025-01-01', validationUntil: '2025-12-31', testFrom: '2026-01-01', testUntil: '2026-12-31',
  metrics: {} as ModelResult['metrics'], hours: [], modelRuns: [], comparisonExplanation: '', warnings: [], limitations: '',
};

describe('experiment builder state', () => {
  it('keeps a location selection independent from the Murmansk search draft', () => {
    const selected = { name: 'Reykjavík, Iceland', latitude: 64.15, longitude: -21.94 };
    const state = applyLocationSelection(selected);

    expect(state.location).toEqual(selected);
    expect(state.searchText).toBe('');
  });

  it('uses the exact documented features for each preset', () => {
    expect(PRESET_FEATURES.weather).toEqual(['temperature', 'cloud', 'wind', 'pressure']);
    expect(PRESET_FEATURES.space).toEqual(['temperature', 'cloud', 'wind', 'pressure', 'kp', 'solar_speed', 'bz']);
    expect(CUSTOM_FEATURES).toContain('moon_altitude');
    expect(CUSTOM_FEATURES).not.toContain('light_pollution');
    expect(CUSTOM_FEATURES).not.toContain('latitude');
  });

  it('turns a custom feature on and off without hidden additions', () => {
    const selected = toggleFeature(['cloud'], 'bz');
    expect(selected).toEqual(['cloud', 'bz']);
    expect(toggleFeature(selected, 'cloud')).toEqual(['bz']);
  });

  it('formats a reverse-geocoded city rather than a street address', () => {
    expect(formatReverseGeocodedLabel({ city: 'Oxford', county: 'Oxfordshire', country: 'United Kingdom' }, 'Penrose Paving, Oxford')).toBe('Oxford, Oxfordshire, United Kingdom');
  });

  it('marks results as outdated after the model or variable draft changes, while retaining the evaluated result', () => {
    const location = { name: 'Reykjavík, Iceland', latitude: 64.15, longitude: -21.94 };
    expect(differsFromEvaluatedExperiment(location, 'compare', PRESET_FEATURES.space, evaluated)).toBe(false);
    expect(differsFromEvaluatedExperiment(location, 'random_forest', PRESET_FEATURES.space, evaluated)).toBe(true);
    expect(differsFromEvaluatedExperiment(location, 'compare', ['cloud'], evaluated)).toBe(true);
    expect(evaluated.features).toEqual(PRESET_FEATURES.space);
  });

  it('keeps an evaluated fork configuration separate from an unsaved draft', () => {
    const draft = ['cloud'];
    expect(evaluated.features).toEqual(PRESET_FEATURES.space);
    expect(draft).not.toEqual(evaluated.features);
  });

  it('supplies populated 2024, 2025, and 2026 rows to advanced metrics', () => {
    expect(evaluatedPeriods(evaluated)).toEqual([
      ['Training', '2024-01-01–2024-12-31'],
      ['Validation', '2025-01-01–2025-12-31'],
      ['Test', '2026-01-01–2026-12-31'],
    ]);
  });

  it('reports feature, model, location, and test-period changes between saved forks', () => {
    const changed = {
      ...evaluated,
      features: ['cloud', 'kp'] as ModelResult['features'],
      modelSelection: 'random_forest' as const,
      coordinates: { latitude: 51.76, longitude: -1.26 },
      testUntil: '2026-11-30',
    };

    expect(compareEvaluatedExperiments(evaluated, changed)).toEqual({
      addedFeatures: [],
      removedFeatures: ['temperature', 'wind', 'pressure', 'solar_speed', 'bz'],
      modelChanged: true,
      locationChanged: true,
      testPeriodChanged: true,
    });
  });
});
