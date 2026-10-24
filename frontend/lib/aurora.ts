// The only frontend file that knows how to talk to the Python API.
type Variable = {
  key: string;
  name: string;
  unit: string;
};

type VariableGroup = {
  title: string;
  note: string;
  variables: Variable[];
};

export const VARIABLE_GROUPS: VariableGroup[] = [
  {
    title: 'Local weather',
    note: 'Historical hourly observations (Open-Meteo ERA5)',
    variables: [
      { key: 'temperature', name: 'Temperature', unit: '°C' },
      { key: 'cloud', name: 'Cloud cover', unit: '%' },
      { key: 'wind', name: 'Wind speed', unit: 'km/h' },
      { key: 'pressure', name: 'Atmospheric pressure', unit: 'hPa' },
    ],
  },
  {
    title: 'Space weather',
    note: 'NASA OMNI measurements; we use an earlier completed Kp interval',
    variables: [
      { key: 'kp', name: 'Geomagnetic Kp index', unit: '0–9' },
      { key: 'solar_speed', name: 'Solar wind speed', unit: 'km/s' },
      { key: 'bz', name: 'Interplanetary magnetic field (Bz)', unit: 'nT' },
    ],
  },
  {
    title: 'Sky and location',
    note: 'Known future Sun/Moon positions calculated from the selected coordinates',
    variables: [
      { key: 'sun_elevation', name: 'Darkness (sun elevation)', unit: 'degrees' },
      { key: 'moon_phase', name: 'Moon phase (illumination)', unit: '%' },
      { key: 'moon_altitude', name: 'Moon altitude', unit: 'degrees' },
    ],
  },
] ;

export const VARIABLES = VARIABLE_GROUPS.flatMap(group => group.variables);
export type Feature = Variable['key'];
export type ModelChoice = 'logistic_regression' | 'random_forest' | 'compare';
export type ExperimentLocation = { name: string; latitude?: number; longitude?: number };
export type PreparedLocation = { location: string; coordinates: { latitude: number; longitude: number } | null; historicalRowCount: number };

export type ModelMetrics = {
  brier: number;
  baselineBrier: number;
  precision: number;
  recall: number;
  f1: number;
  auc: number | null;
  positiveRate: number;
  positiveCount: number;
  negativeCount: number;
  truePositive: number;
  falsePositive: number;
  trueNegative: number;
  falseNegative: number;
};

export type ModelRun = {
  key: Exclude<ModelChoice, 'compare'>;
  name: string;
  metrics: ModelMetrics;
  hours: { hour: string; probability: number; observedProxy: number }[];
};

export type ModelResult = {
  horizonHours: 24;
  location: string;
  features: Feature[];
  label: string;
  model: string;
  modelSelection: ModelChoice;
  trainCount: number;
  validationCount: number;
  testCount: number;
  trainFrom: string;
  trainUntil: string;
  validationFrom: string;
  validationUntil: string;
  testFrom: string;
  testUntil: string;
  metrics: ModelMetrics;
  hours: { hour: string; probability: number; observedProxy: number }[];
  modelRuns: ModelRun[];
  comparisonExplanation: string;
  coordinates: { latitude: number; longitude: number } | null;
  warnings: string[];
  limitations: string;
};

type RequestOptions = { signal?: AbortSignal };

async function auroraRequest(path: string, body: object, options?: RequestOptions): Promise<Response> {
  try {
    return await fetch(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: options?.signal,
    });
  } catch (error) {
    if ((error as { name?: string }).name === 'AbortError') throw error;
    throw new Error('Cannot contact Python. Start the backend on port 8000.');
  }
}

export async function prepareLocation(location: ExperimentLocation, options?: RequestOptions): Promise<PreparedLocation> {
  const response = await auroraRequest('/api/v1/aurora/prepare', {
    location: location.name, latitude: location.latitude, longitude: location.longitude,
  }, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Python API error ${response.status}`);
  }
  return (await response.json()) as PreparedLocation;
}

export async function runModel(features: Feature[], location: ExperimentLocation | string, model: ModelChoice, options?: RequestOptions): Promise<ModelResult> {
  const selected = typeof location === 'string' ? { name: location } : location;
  const response = await auroraRequest('/api/v1/aurora/evaluate', { features, location: selected.name, latitude: selected.latitude, longitude: selected.longitude, model }, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail;
    throw new Error(typeof message === 'string' ? message : `Python API error ${response.status}`);
  }
  const result = (await response.json()) as ModelResult;
  if (result.horizonHours !== 24) {
    throw new Error('This result uses an older prediction horizon and cannot be shown as a 24-hour experiment. Run it again.');
  }
  return result;
}
