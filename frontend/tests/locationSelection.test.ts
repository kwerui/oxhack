import { describe, expect, it } from 'vitest';
import { backendCoordinatesMatch, coordinateFallback, isCurrentResponse, isSelectedLocation } from '../lib/locationSelection';

describe('location selection integrity', () => {
  it('keeps valid browser coordinates selected when no readable place name is available', () => {
    const fallback = coordinateFallback(51.5074, -0.1278);
    expect(fallback).toEqual({ name: '51.5074°, -0.1278°', latitude: 51.5074, longitude: -0.1278 });
    expect(isSelectedLocation(fallback)).toBe(true);
  });

  it('does not regard an empty selection as runnable', () => {
    expect(isSelectedLocation(null)).toBe(false);
    expect(isSelectedLocation({ name: 'Missing coordinates' })).toBe(false);
  });

  it('requires backend-confirmed coordinates to match the requested location', () => {
    const requested = { name: 'London', latitude: 51.5074, longitude: -0.1278 };
    expect(backendCoordinatesMatch(requested, { latitude: 51.5074, longitude: -0.1278 })).toBe(true);
    expect(backendCoordinatesMatch(requested, { latitude: 69.65, longitude: 18.96 })).toBe(false);
  });

  it('rejects a response made stale by a location switch or newer request', () => {
    expect(isCurrentResponse(3, 9, 3, 9)).toBe(true);
    expect(isCurrentResponse(3, 9, 4, 10)).toBe(false);
    expect(isCurrentResponse(3, 9, 3, 10)).toBe(false);
  });
});
