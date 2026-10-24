import type { ExperimentLocation } from './aurora';

export function isSelectedLocation(location: ExperimentLocation | null): location is Required<ExperimentLocation> {
  return Boolean(location && Number.isFinite(location.latitude) && Number.isFinite(location.longitude));
}

export function coordinateFallback(latitude: number, longitude: number): Required<ExperimentLocation> {
  return { name: `${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°`, latitude, longitude };
}

export function backendCoordinatesMatch(location: ExperimentLocation, coordinates: { latitude: number; longitude: number } | null) {
  return Boolean(coordinates && location.latitude === coordinates.latitude && location.longitude === coordinates.longitude);
}

export function isCurrentResponse(selectionAtStart: number, requestAtStart: number, currentSelection: number, currentRequest: number) {
  return selectionAtStart === currentSelection && requestAtStart === currentRequest;
}
