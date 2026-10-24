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
    note: 'Known future Sun/Moon positions; geographic latitude (not magnetic latitude)',
    variables: [
      { key: 'latitude', name: 'Location / latitude', unit: 'degrees' },
      { key: 'sun_elevation', name: 'Darkness (sun elevation)', unit: 'degrees' },
      { key: 'moon_phase', name: 'Moon phase (illumination)', unit: '%' },
      { key: 'moon_altitude', name: 'Moon altitude', unit: 'degrees' },
    ],
  },
  {
    title: 'Site assumption',
    note: 'Fixed example Bortle class per city; this is NOT measured light pollution',
    variables: [{ key: 'light_pollution', name: 'Light pollution', unit: 'Bortle 1–9' }],
  },
] ;

export const VARIABLES = VARIABLE_GROUPS.flatMap(group => group.variables);
export type Feature = Variable['key'];

export type ModelResult = {
  location: string;
  features: Feature[];
  label: string;
  model: string;
  trainCount: number;
  testCount: number;
  trainUntil: string;
  testFrom: string;
  metrics: {
    brier: number;
    baselineBrier: number;
    precision: number;
    recall: number;
    auc: number | null;
    positiveRate: number;
  };
  hours: { hour: string; probability: number; observedProxy: number }[];
  limitations: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function runModel(features: Feature[], location: string): Promise<ModelResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/aurora/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ features, location }),
    });
  } catch {
    throw new Error('Cannot contact Python. Start the backend on port 8000.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail;
    throw new Error(typeof message === 'string' ? message : `Python API error ${response.status}`);
  }
  return (await response.json()) as ModelResult;
}
