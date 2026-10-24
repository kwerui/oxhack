'use client';

import { useRef, useState } from 'react';
import { prepareLocation, runModel, VARIABLE_GROUPS, VARIABLES, type ExperimentLocation, type Feature, type ModelChoice, type ModelResult } from '../lib/aurora';
import { applyLocationSelection, compareEvaluatedExperiments, differsFromEvaluatedExperiment, evaluatedPeriods, formatReverseGeocodedLabel, PRESET_FEATURES, toggleFeature } from '../lib/experimentBuilder';
import { backendCoordinatesMatch, coordinateFallback, isCurrentResponse, isSelectedLocation } from '../lib/locationSelection';

type Fork = { name: string; result: ModelResult };
type Place = ExperimentLocation & { region?: string; country?: string };
type Status = 'selecting-location' | 'ready' | 'loading-history' | 'evaluating-models' | 'completed' | 'error';
const pct = (value: number) => `${Math.round(value * 100)}%`;

export default function Home() {
  const [location, setLocation] = useState<ExperimentLocation | null>(null);
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<Place[]>([]);
  const [searchError, setSearchError] = useState('');
  const [geolocationError, setGeolocationError] = useState('');
  const [reverseGeocodingError, setReverseGeocodingError] = useState('');
  const [note, setNote] = useState('Choose a suggested place, search, use coordinates, or use browser location.');
  const [advanced, setAdvanced] = useState(false);
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [features, setFeatures] = useState<Feature[]>(PRESET_FEATURES.space);
  const [preset, setPreset] = useState<'weather' | 'space' | 'custom'>('space');
  const [model, setModel] = useState<ModelChoice>('compare');
  const [forks, setForks] = useState<Fork[]>([]);
  const [selected, setSelected] = useState(0);
  const [comparisonForkIndex, setComparisonForkIndex] = useState<number | null>(null);
  const [status, setStatus] = useState<Status>('selecting-location');
  const [error, setError] = useState('');
  const requestVersion = useRef(0);
  const selectionVersion = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const candidate = forks[selected]?.result;
  const active = candidate?.horizonHours === 24 ? candidate : undefined;
  const comparisonFork = comparisonForkIndex === null ? undefined : forks[comparisonForkIndex];
  const forkDifference = active && comparisonFork ? compareEvaluatedExperiments(comparisonFork.result, active) : undefined;
  const isRunning = status === 'loading-history' || status === 'evaluating-models';
  const resultIsOutdated = differsFromEvaluatedExperiment(location, model, features, active);
  const featureNames = (selectedFeatures: Feature[]) => selectedFeatures.map(key => VARIABLES.find(variable => variable.key === key)?.name ?? key).join(', ');

  function invalidateRequest() {
    requestVersion.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
  }

  function selectLocation(next: ExperimentLocation, message: string) {
    if (next.latitude === undefined || next.longitude === undefined) return;
    const selection = applyLocationSelection(next);
    invalidateRequest();
    selectionVersion.current += 1;
    setLocation(selection.location);
    setForks([]);
    setSelected(0);
    setComparisonForkIndex(null);
    setMatches([]);
    setQuery(selection.searchText);
    setError('');
    setSearchError('');
    setReverseGeocodingError('');
    setNote(message);
    setStatus('ready');
  }

  async function search() {
    const text = query.trim();
    if (!text) {
      setSearchError('Enter a city or place to search.');
      return;
    }
    setSearchError('');
    setMatches([]);
    try {
      const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(text)}&count=6&language=en&format=json`);
      const body = await response.json() as { results?: Place[] };
      const results = body.results ?? [];
      setMatches(results);
      if (!results.length) {
        setSearchError(location ? `No replacement was found for “${text}”. ${location.name} remains selected.` : `No places found for “${text}”. Try a more specific name or coordinates.`);
      }
    } catch {
      setSearchError(location ? `Place search is unavailable. ${location.name} remains selected.` : 'Place search is unavailable. Enter coordinates or try again.');
    }
  }

  async function reverseCoordinateName(latitude: number, longitude: number, version: number) {
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`);
      const body = await response.json() as { display_name?: string; address?: { city?: string; town?: string; village?: string; municipality?: string; county?: string; state?: string; country?: string } };
      if (selectionVersion.current === version && body.display_name) {
        const name = formatReverseGeocodedLabel(body.address, body.display_name);
        setLocation({ name, latitude, longitude });
        setQuery('');
        setNote(`Selected ${name}. Coordinates are verified below.`);
      } else if (selectionVersion.current === version) {
        setReverseGeocodingError('No readable place name was returned. The browser coordinates remain selected.');
      }
    } catch {
      if (selectionVersion.current === version) {
        setReverseGeocodingError('Could not look up a readable place name. The browser coordinates remain selected.');
      }
    }
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGeolocationError('Browser geolocation is not supported. Search or enter coordinates instead.');
      return;
    }
    setGeolocationError('');
    setReverseGeocodingError('');
    setStatus('selecting-location');
    setNote('Requesting browser coordinates…');
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const version = selectionVersion.current + 1;
        selectLocation(coordinateFallback(coords.latitude, coords.longitude), 'Browser coordinates selected. Looking up a readable name is optional.');
        void reverseCoordinateName(coords.latitude, coords.longitude, version);
      },
      () => {
        setGeolocationError('Browser location was unavailable or permission was not granted. Search or enter coordinates instead.');
        setStatus(location ? 'ready' : 'selecting-location');
      },
      { enableHighAccuracy: false, timeout: 10_000 },
    );
  }

  function useCoordinates() {
    const latitude = Number(lat);
    const longitude = Number(lon);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      setError('Latitude must be −90 to 90 and longitude −180 to 180.');
      setStatus(location ? 'ready' : 'error');
      return;
    }
    setReverseGeocodingError('');
    selectLocation(coordinateFallback(latitude, longitude), 'Coordinates selected. They will be sent to the backend exactly as shown.');
  }

  function setPresetChoice(next: 'weather' | 'space' | 'custom') {
    setPreset(next);
    if (next !== 'custom') setFeatures(PRESET_FEATURES[next]);
  }

  function toggle(feature: Feature) {
    setPreset('custom');
    setFeatures(current => toggleFeature(current, feature));
  }

  async function run() {
    if (!isSelectedLocation(location)) {
      setError('Select a valid location before running an experiment.');
      setStatus('error');
      return;
    }
    if (!features.length) {
      setError('Select at least one input variable before running an experiment.');
      return;
    }
    const requestedLocation = { ...location };
    const requestedFeatures = [...features];
    const selectionAtStart = selectionVersion.current;
    const requestAtStart = requestVersion.current + 1;
    requestVersion.current = requestAtStart;
    const controller = new AbortController();
    abortRef.current = controller;
    setError('');
    setStatus('loading-history');
    try {
      const prepared = await prepareLocation(requestedLocation, { signal: controller.signal });
      if (!isCurrentResponse(selectionAtStart, requestAtStart, selectionVersion.current, requestVersion.current)) return;
      if (!backendCoordinatesMatch(requestedLocation, prepared.coordinates)) throw new Error('Backend preparation returned different coordinates; the experiment was not run.');
      setStatus('evaluating-models');
      const result = await runModel(requestedFeatures, requestedLocation, model, { signal: controller.signal });
      if (!isCurrentResponse(selectionAtStart, requestAtStart, selectionVersion.current, requestVersion.current)) return;
      if (!backendCoordinatesMatch(requestedLocation, result.coordinates)) throw new Error('Backend evaluation returned different coordinates; the result was discarded.');
      setForks(current => {
        setSelected(current.length);
        setComparisonForkIndex(current.length ? 0 : null);
        return [...current, { name: `Fork ${String.fromCharCode(65 + current.length)}`, result }];
      });
      setStatus('completed');
    } catch (problem) {
      if ((problem as { name?: string }).name === 'AbortError') return;
      if (!isCurrentResponse(selectionAtStart, requestAtStart, selectionVersion.current, requestVersion.current)) return;
      setError(problem instanceof Error ? problem.message : 'Experiment failed.');
      setStatus('error');
    } finally {
      if (requestVersion.current === requestAtStart) abortRef.current = null;
    }
  }

  const statusText: Record<Status, string> = {
    'selecting-location': 'Select a location to enable experiments.',
    ready: 'Location selected. Ready to prepare its historical dataset.',
    'loading-history': 'Loading or verifying historical data for the selected coordinates…',
    'evaluating-models': 'Historical data confirmed. Evaluating the selected models…',
    completed: 'Experiment completed. The result below uses backend-confirmed coordinates.',
    error: 'Resolve the error before running an experiment.',
  };

  return <main className="site">
    <header className="site-header"><a className="brand" href="#top"><span>✦</span> AuroraTime</a><nav><a href="#experiment">Experiment</a><a href="#results">Results</a><a href="#forks">Compare</a></nav><span className="header-note">Historical exploration · UTC</span></header>
    <section className="masthead" id="top"><div><p className="eyebrow">A historical model lab</p><h1>Explore the conditions behind an aurora-ready sky.</h1><p>Choose a place, select the evidence you want to test, and compare models on unseen historical hours.</p></div><div className="aurora-mark" aria-hidden="true"><i/><i/><i/><span>24h</span><small>prediction horizon</small></div></section>
    <div className="experience">
    <aside className="experiment-builder" id="experiment" aria-label="Experiment builder">
      <div className="builder-heading"><p className="eyebrow">Experiment builder</p><h2>Set up your test</h2><p>All models use the same 24-hour horizon and held-out historical test period.</p></div>
    <section className="panel builder-panel" id="location"><div className="section-title"><div><p className="step-label">1 · Location</p><h3>Choose a place</h3></div><button className="secondary" onClick={useMyLocation}>Use my location</button></div>
      <label htmlFor="search">Search by city or place</label><div className="search-row"><input id="search" value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => event.key === 'Enter' && search()} placeholder="e.g. Yellowknife, Canada"/><button className="primary compact" onClick={search}>Search</button></div>
      <div className="suggestions"><button onClick={() => selectLocation({ name: 'Tromsø, Norway', latitude: 69.65, longitude: 18.96 }, 'Selected Tromsø, Norway. Coordinates are verified below.')}>Tromsø</button><button onClick={() => selectLocation({ name: 'Reykjavík, Iceland', latitude: 64.15, longitude: -21.94 }, 'Selected Reykjavík, Iceland. Coordinates are verified below.')}>Reykjavík</button><button onClick={() => setAdvanced(!advanced)}>Advanced coordinates</button></div>
      {matches.length > 0 && <ul className="matches">{matches.map(place => <li key={`${place.latitude}-${place.longitude}`}><button onClick={() => selectLocation({ name: [place.name, place.region, place.country].filter(Boolean).join(', '), latitude: place.latitude, longitude: place.longitude }, 'Selected search result. Coordinates are verified below.')}><b>{place.name}</b><span>{[place.region, place.country].filter(Boolean).join(', ')}</span></button></li>)}</ul>}
      {advanced && <div className="coordinates"><label>Latitude<input value={lat} onChange={event => setLat(event.target.value)} placeholder="51.5074"/></label><label>Longitude<input value={lon} onChange={event => setLon(event.target.value)} placeholder="−0.1278"/></label><button className="secondary" onClick={useCoordinates}>Use coordinates</button></div>}
      <p className="field-tip" role="status">{note}</p>{location && <p className="selected-location"><b>Selected</b><span>{location.name}</span><small>{location.latitude?.toFixed(4)}, {location.longitude?.toFixed(4)}</small></p>}{searchError && <p className="error">{searchError}</p>}{geolocationError && <p className="error">{geolocationError}</p>}{reverseGeocodingError && <p className="warning">{reverseGeocodingError}</p>}
    </section>
    <section className="panel builder-panel"><div className="section-title"><div><p className="step-label">2 · Inputs & model</p><h3>Choose what to compare</h3></div><span className="pill">{features.length} variables</span></div>
      <fieldset disabled={isRunning}><legend>Choose an input set</legend><div className="choice-grid">{([['weather', 'Weather only', 'Temperature, cloud, wind and pressure'], ['space', 'Weather + space weather', 'Weather plus Kp, solar wind and IMF Bz'], ['custom', 'Custom variables', 'Choose available inputs']] as const).map(([id, title, text]) => <label className={preset === id ? 'selected' : ''} key={id}><input type="radio" checked={preset === id} onChange={() => setPresetChoice(id)}/><b>{title}</b><small>{text}</small></label>)}</div></fieldset>
      {preset === 'custom' && <div className="custom-grid"><p className="field-tip custom-help">Choose exactly the inputs sent to the model. Coordinates still retrieve location-specific history and calculate Sun/Moon positions, but latitude is not an hourly predictor for one location. Light pollution is unavailable because no measured worldwide source is bundled; it is never replaced with an assumed value.</p>{VARIABLE_GROUPS.map(group => <fieldset disabled={isRunning} key={group.title}><legend>{group.title}</legend><p className="field-tip">{group.note}</p>{group.variables.map(variable => <label className="check" key={variable.key}><input type="checkbox" checked={features.includes(variable.key as Feature)} onChange={() => toggle(variable.key as Feature)}/>{variable.name}<em>{variable.unit}</em></label>)}</fieldset>)}</div>}
      <fieldset disabled={isRunning}><legend>Model</legend><div className="choice-grid">{([['logistic_regression', 'Logistic Regression', 'Simple probability baseline'], ['random_forest', 'Random Forest', 'Flexible pattern finder'], ['compare', 'Compare both', 'Same held-out hours']] as const).map(([id, title, text]) => <label className={model === id ? 'selected' : ''} key={id}><input type="radio" checked={model === id} onChange={() => setModel(id)}/><b>{title}</b><small>{text}</small></label>)}</div></fieldset>
      <div className="run-row"><div><b>24-hour horizon</b><p>Target: Kp ≥ 4, clouds ≤ 40%, and darkness at Sun ≤ −6°.</p><p className="field-tip" role="status">{statusText[status]}</p>{!features.length && <p className="warning" role="alert">Select at least one variable to run this experiment.</p>}{resultIsOutdated && <p className="warning" role="status">The builder has changed. Run again to evaluate these settings.</p>}</div><button className="primary" disabled={isRunning || !location || !features.length} onClick={run}>{status === 'loading-history' ? 'Loading history…' : status === 'evaluating-models' ? 'Evaluating models…' : 'Run experiment'}</button></div>{error && <p className="error">{error}</p>}
    </section>
    </aside>
    <section className="results-stage" id="results" aria-live="polite">
      {!active && <div className="pre-experiment"><p className="eyebrow">What this experiment tests</p><h2>A transparent 24-hour backtest.</h2><p>At a selected hour, AuroraTime asks whether the available weather, space-weather and sky inputs would help identify a suitable viewing period one day later.</p><div className="horizon-card"><span>Now</span><i aria-hidden="true"/><strong>+24 hours</strong><small>Evaluate against the historical proxy</small></div><dl><div><dt>Training</dt><dd>2024 historical hours</dd></div><div><dt>Validation</dt><dd>2025 threshold selection</dd></div><div><dt>Testing</dt><dd>2026 unseen hours</dd></div></dl><p className="quiet-note">This is not a live forecast and the outcome is a rule-defined viewing-conditions proxy, not a confirmed aurora sighting.</p></div>}
    {active && <section className="results-content"><div className="result-intro"><p className="eyebrow">Evaluated experiment</p><h2>What the models found</h2><p className="conclusion">{active.comparisonExplanation}</p>{resultIsOutdated && <p className="warning">This saved result belongs to the previous builder settings.</p>}<p className="field-tip"><b>{active.location}</b> · {active.coordinates?.latitude.toFixed(4)}, {active.coordinates?.longitude.toFixed(4)}<br/>{featureNames(active.features)} · {active.horizonHours}-hour horizon</p></div>{active.warnings.map(warning => <p className="warning" key={warning}>{warning}</p>)}<div className="summary-grid">{active.modelRuns.map(run => <article className="panel model-summary" key={run.key}><p className="eyebrow">{run.name}</p><div className="headline-metric"><strong>{run.metrics.truePositive}</strong><span>detected periods</span></div><dl><div><dt>Missed periods</dt><dd>{run.metrics.falseNegative}</dd></div><div><dt>False alarms</dt><dd>{run.metrics.falsePositive}</dd></div><div><dt>Precision <small>When it signalled, how often it was right</small></dt><dd>{pct(run.metrics.precision)}</dd></div><div><dt>Recall <small>Suitable periods it found</small></dt><dd>{pct(run.metrics.recall)}</dd></div></dl></article>)}</div><article className="panel insight"><h3>How to read this</h3><p><b>Precision</b> is how often a model’s positive signal matched the historical proxy. <b>Recall</b> is how many of those suitable periods it found. False alarms and missed periods show the trade-off more directly than one headline score.</p><details><summary>Advanced metrics, baseline and evaluation dates</summary><table><thead><tr><th>Evaluation period</th><th>Dates (UTC)</th></tr></thead><tbody>{evaluatedPeriods(active).map(([period, dates]) => <tr key={period}><th>{period}</th><td>{dates}</td></tr>)}{active.modelRuns.map(run => <tr key={run.key}><th>{run.name}</th><td>F1 {pct(run.metrics.f1)} · Brier {run.metrics.brier.toFixed(6)} / baseline {run.metrics.baselineBrier.toFixed(6)} · TP {run.metrics.truePositive} · FP {run.metrics.falsePositive} · FN {run.metrics.falseNegative}</td></tr>)}</tbody></table></details></article></section>}
    </section></div>
    {forks.length > 0 && <section id="forks"><div className="result-intro"><p className="eyebrow">4 / Compare experiments</p><h2>Compare saved forks</h2><p>Each fork retains backend-confirmed settings and coordinates. A new location clears prior results.</p></div><div className="fork-grid">{forks.map((fork, index) => <button className={`fork ${index === selected ? 'active' : ''}`} onClick={() => { if (index === comparisonForkIndex) setComparisonForkIndex(selected); setSelected(index); }} key={fork.name}><b>{fork.name}</b><span>{featureNames(fork.result.features)}</span>{fork.result.modelRuns.map(run => <small key={run.key}>{run.name}: {run.metrics.truePositive} detected · {run.metrics.falseNegative} missed · {run.metrics.falsePositive} false alarms</small>)}</button>)}</div>{active && forks.length > 1 && <article className="panel fork-comparison"><label htmlFor="compare-fork">Compare {forks[selected].name} with <select id="compare-fork" value={comparisonForkIndex ?? ''} onChange={event => setComparisonForkIndex(event.target.value === '' ? null : Number(event.target.value))}><option value="">Choose a fork</option>{forks.map((fork, index) => index !== selected && <option value={index} key={fork.name}>{fork.name}</option>)}</select></label>{comparisonFork && forkDifference && <><h3>{comparisonFork.name} → {forks[selected].name}</h3><p><b>Variables changed:</b> {forkDifference.addedFeatures.length ? `added ${featureNames(forkDifference.addedFeatures)}` : 'none added'}; {forkDifference.removedFeatures.length ? `removed ${featureNames(forkDifference.removedFeatures)}` : 'none removed'}.</p><p><b>Model changed:</b> {forkDifference.modelChanged ? `${comparisonFork.result.modelSelection} → ${active.modelSelection}` : 'no'}.</p>{forkDifference.locationChanged && <p className="warning">These forks use different locations; their metrics are not a like-for-like model comparison.</p>}{forkDifference.testPeriodChanged && <p className="warning">These forks use different held-out test periods; their metrics are not directly comparable.</p>}<div className="comparison-table-wrap"><table><thead><tr><th>Fork / model</th><th>Evaluated variables</th><th>Detected / missed / false alarms</th><th>Precision</th><th>Recall</th><th>F1</th><th>Brier / baseline</th></tr></thead><tbody>{[comparisonFork, forks[selected]].flatMap(fork => fork.result.modelRuns.map(run => <tr key={`${fork.name}-${run.key}`}><th>{fork.name} · {run.name}</th><td>{featureNames(fork.result.features)}</td><td>{run.metrics.truePositive} / {run.metrics.falseNegative} / {run.metrics.falsePositive}</td><td>{pct(run.metrics.precision)}</td><td>{pct(run.metrics.recall)}</td><td>{pct(run.metrics.f1)}</td><td>{run.metrics.brier.toFixed(6)} / {run.metrics.baselineBrier.toFixed(6)}</td></tr>))}</tbody></table></div></>}</article>}</section>}
    <footer>NASA OMNI2 + Open-Meteo ERA5 · Astronomy via Astral · Historical backtests only</footer>
  </main>;
}
