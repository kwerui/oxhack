import type { Inputs, Simulation } from './types';
const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export async function runSimulation(inputs: Inputs): Promise<Simulation> {
  const response = await fetch(`${API}/api/v1/simulations`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(inputs) });
  if (!response.ok) throw new Error(`Simulation unavailable (${response.status})`);
  return response.json() as Promise<Simulation>;
}
