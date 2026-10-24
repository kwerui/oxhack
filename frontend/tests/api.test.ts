import { afterEach, describe, expect, it, vi } from 'vitest';
import { runSimulation } from '../lib/api';
import { runModel } from '../lib/aurora';
import { initialInputs } from '../lib/types';

afterEach(() => vi.unstubAllGlobals());

function successfulResponse(body: unknown): Response {
  return { ok: true, json: async () => body } as Response;
}

describe('frontend API client', () => {
  it('sends aurora experiments through the relative Next.js API path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({}));
    vi.stubGlobal('fetch', fetchMock);

    await runModel(['cloud'], 'Tromsø', 'compare');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/aurora/evaluate', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({
      body: JSON.stringify({ features: ['cloud'], location: 'Tromsø', model: 'compare' }),
    }));
  });

  it('sends legacy simulations through the relative Next.js API path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({}));
    vi.stubGlobal('fetch', fetchMock);

    await runSimulation(initialInputs);

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/simulations', expect.objectContaining({ method: 'POST' }));
  });
});
