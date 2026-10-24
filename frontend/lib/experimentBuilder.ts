import type { ExperimentLocation, Feature, ModelChoice, ModelResult } from './aurora';

export const PRESET_FEATURES: Record<'weather' | 'space', Feature[]> = {
  weather: ['temperature', 'cloud', 'wind', 'pressure'],
  space: ['temperature', 'cloud', 'wind', 'pressure', 'kp', 'solar_speed', 'bz'],
};

export const CUSTOM_FEATURES: Feature[] = [
  'temperature', 'cloud', 'wind', 'pressure', 'kp', 'solar_speed', 'bz',
  'latitude', 'sun_elevation', 'moon_phase', 'moon_altitude', 'light_pollution',
];

type ReverseAddress = {
  city?: string;
  town?: string;
  village?: string;
  municipality?: string;
  county?: string;
  state?: string;
  country?: string;
};

export function toggleFeature(features: Feature[], feature: Feature): Feature[] {
  return features.includes(feature) ? features.filter(item => item !== feature) : [...features, feature];
}

export function formatReverseGeocodedLabel(address: ReverseAddress | undefined, fallback: string): string {
  const locality = address?.city ?? address?.town ?? address?.village ?? address?.municipality;
  const parts = [locality, address?.county ?? address?.state, address?.country].filter(Boolean);
  return parts.length ? parts.join(', ') : fallback.split(',').slice(0, 2).join(',').trim();
}

export function applyLocationSelection(location: ExperimentLocation) {
  return { location, searchText: '' };
}

export function differsFromEvaluatedExperiment(
  location: ExperimentLocation | null,
  model: ModelChoice,
  features: Feature[],
  result: ModelResult | undefined,
): boolean {
  if (!location || !result) return false;
  return location.latitude !== result.coordinates?.latitude
    || location.longitude !== result.coordinates?.longitude
    || model !== result.modelSelection
    || features.length !== result.features.length
    || features.some((feature, index) => feature !== result.features[index]);
}

export function evaluatedPeriods(result: Pick<ModelResult, 'trainFrom' | 'trainUntil' | 'validationFrom' | 'validationUntil' | 'testFrom' | 'testUntil'>) {
  const date = (value: string) => value.slice(0, 10);
  return [
    ['Training', `${date(result.trainFrom)}–${date(result.trainUntil)}`],
    ['Validation', `${date(result.validationFrom)}–${date(result.validationUntil)}`],
    ['Test', `${date(result.testFrom)}–${date(result.testUntil)}`],
  ] as const;
}
