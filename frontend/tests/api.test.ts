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

    await runModel(['cloud'], 'Tromsø');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/aurora/evaluate', expect.objectContaining({ method: 'POST' }));
  });

  it('sends legacy simulations through the relative Next.js API path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(successfulResponse({}));
    vi.stubGlobal('fetch', fetchMock);

    await runSimulation(initialInputs);

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/simulations', expect.objectContaining({ method: 'POST' }));
  });
});
