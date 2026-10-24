import type { Inputs, Simulation } from './types';

export async function runSimulation(inputs: Inputs): Promise<Simulation> {
  const response = await fetch('/api/v1/simulations', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(inputs) });
  if (!response.ok) throw new Error(`Simulation unavailable (${response.status})`);
  return response.json() as Promise<Simulation>;
}
