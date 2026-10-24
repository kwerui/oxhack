import { afterEach, describe, expect, it, vi } from 'vitest';
import { runSimulation } from '../lib/api';
import { prepareLocation, runModel } from '../lib/aurora';
import { initialInputs } from '../lib/types';

afterEach(() => vi.unstubAllGlobals());

function successfulResponse(body: unknown): Response {
  return { ok: true, json: async () => body } as Response;
}

describe('frontend API client', () => {
  it('sends aurora experiments through the relative Next.js API path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({ horizonHours: 24 }));
    vi.stubGlobal('fetch', fetchMock);

    await runModel(['cloud'], 'Tromsø', 'compare');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/aurora/evaluate', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({
      body: JSON.stringify({ features: ['cloud'], location: 'Tromsø', model: 'compare' }),
    }));
  });

  it('includes selected coordinates when evaluating a worldwide location', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({ horizonHours: 24 }));
    vi.stubGlobal('fetch', fetchMock);

    await runModel(['cloud'], { name: 'London, England, United Kingdom', latitude: 51.5074, longitude: -0.1278 }, 'compare');

    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({
      body: JSON.stringify({ features: ['cloud'], location: 'London, England, United Kingdom', latitude: 51.5074, longitude: -0.1278, model: 'compare' }),
    }));
  });

  it('sends only the custom variable IDs selected by the user', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({ horizonHours: 24 }));
    vi.stubGlobal('fetch', fetchMock);

    await runModel(['cloud', 'bz', 'moon_altitude'], { name: 'Reykjavík, Iceland', latitude: 64.15, longitude: -21.94 }, 'random_forest');

    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({
      body: JSON.stringify({ features: ['cloud', 'bz', 'moon_altitude'], location: 'Reykjavík, Iceland', latitude: 64.15, longitude: -21.94, model: 'random_forest' }),
    }));
  });

  it('prepares the exact selected coordinates before evaluation', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({ coordinates: { latitude: 51.5074, longitude: -0.1278 }, historicalRowCount: 1 }));
    vi.stubGlobal('fetch', fetchMock);

    await prepareLocation({ name: 'London', latitude: 51.5074, longitude: -0.1278 });

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/aurora/prepare', expect.objectContaining({
      body: JSON.stringify({ location: 'London', latitude: 51.5074, longitude: -0.1278 }),
    }));
  });

  it('rejects a saved result from the retired three-hour protocol', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(successfulResponse({ horizonHours: 3 })));
    await expect(runModel(['cloud'], 'Tromsø', 'compare')).rejects.toThrow('older prediction horizon');
  });

  it('sends legacy simulations through the relative Next.js API path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({}));
    vi.stubGlobal('fetch', fetchMock);

    await runSimulation(initialInputs);

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/simulations', expect.objectContaining({ method: 'POST' }));
  });
});
