'use client';

import { useState } from 'react';
import { runModel, VARIABLES, VARIABLE_GROUPS, type Feature, type ModelResult } from '../lib/aurora';

// A simple starting model. Add/remove features to create a new fork.
const DEFAULT_FEATURES: Feature[] = [
  'temperature', 'cloud', 'wind', 'pressure',
  'kp', 'solar_speed', 'latitude', 'sun_elevation',
];

type Branch = { name: string; result: ModelResult };

function percentage(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function Home() {
  const [location, setLocation] = useState('Tromsø');
  const [features, setFeatures] = useState<Feature[]>(DEFAULT_FEATURES);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function toggleFeature(key: Feature) {
    setFeatures(previous =>
      previous.includes(key) ? previous.filter(feature => feature !== key) : [...previous, key],
    );
  }

  async function evaluate() {
    setLoading(true);
    setError('');
    try {
      const result = await runModel(features, location);
      const branch = { name: `Fork ${branches.length + 1}`, result };
      setBranches(previous => [...previous, branch]);
      setSelected(branches.length);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  }

  function openBranch(index: number) {
    const branch = branches[index];
    if (!branch) return;
    setSelected(index);
    setLocation(branch.result.location);
    setFeatures([...branch.result.features]);
  }

  const active = branches[selected]?.result;

  return (
    <main className="site">
      <header className="site-header">
        <div className="brand"><span className="symbol">⟡</span> AURORATIME</div>
        <span className="top-tag">OXHACK 2026 / TIME</span>
        <span className="subtitle">Explore the past. Predict the night.</span>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">TEST THE DATA · EXPLORE THE FUTURE</p>
          <h1>What makes a <em>good night</em> for the aurora?</h1>
          <p className="intro">
            Choose which weather and space-weather variables to test. Compare
            predictions for the next three hours using real historical observations.
          </p>
        </div>
        <div className="orbit" aria-hidden="true"><span>NOW</span><strong>+3 HOURS</strong></div>
      </section>

      <section className="how-it-works" aria-label="Three simple steps">
        <p><b>01</b> Pick your variables</p>
        <p><b>02</b> Train + test the model</p>
        <p><b>03</b> Rewind and compare</p>
      </section>

      <section className="panel model-panel" id="model-builder">
        <div className="section-heading">
          <div>
            <p className="eyebrow">STEP 1 / YOUR EXPERIMENT</p>
            <h2>Choose your inputs</h2>
            <p>Choose any combination of 12 inputs. Run the model, then add or remove variables to compare the results.</p>
          </div>
          <span className="pill">{features.length} selected</span>
        </div>

        <div className="form-group">
          <label htmlFor="location" className="field-title">Location</label>
          <select id="location" value={location} onChange={event => setLocation(event.target.value)}>
            <option value="Tromsø">Tromsø, Norway (69.65° N)</option>
            <option value="Reykjavík">Reykjavík, Iceland (64.15° N)</option>
          </select>
          <p className="field-tip">Both locations are included in the training dataset. All times are UTC.</p>
        </div>

        <div className="feature-groups">
          <div className="variable-heading">
            <p className="field-title">Variables used to train the model</p>
            <div className="variable-actions">
              <button className="secondary" type="button" onClick={() => setFeatures([...DEFAULT_FEATURES])}>Starting set</button>
              <button className="secondary" type="button" onClick={() => setFeatures(VARIABLES.map(v => v.key))}>Select all 12</button>
            </div>
          </div>
          {VARIABLE_GROUPS.map(group => (
            <fieldset className="variables" key={group.title}>
              <legend className="group-title">{group.title}</legend>
              <p className="field-tip">{group.note}</p>
              <div className="variable-grid">
                {group.variables.map(variable => (
                  <label className={`variable ${features.includes(variable.key) ? 'chosen' : ''}`} key={variable.key}>
                    <input
                      type="checkbox"
                      checked={features.includes(variable.key)}
                      onChange={() => toggleFeature(variable.key)}
                    />
                    <span>{variable.name}</span>
                    <small>{variable.unit}</small>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </div>

        <div className="run-row">
          <div>
            <strong>Prediction target</strong>
            <p>Will Kp ≥ 4, clouds ≤ 40%, and the sun be ≤ −6° in 3 hours?</p>
            <p className="fine-print">We measure this rule on held-out 2024 history, NOT actual aurora sightings or live conditions. Sun/Moon positions can be calculated for future hours; light pollution is only an assumption.</p>
          </div>
          <button className="primary" type="button" disabled={loading || features.length === 0} onClick={evaluate}>
            {loading ? 'Training model…' : 'Run experiment →'}
          </button>
        </div>
        {features.length === 0 && <p className="error">Select at least one variable.</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {branches.length === 0 ? (
        <section className="panel empty-state">
          <p className="eyebrow">READY WHEN YOU ARE</p>
          <h2>Test your first timeline.</h2>
          <p>The Python model learns from earlier 2024 hours and is evaluated on later hours it has never seen. Download the dataset first.</p>
        </section>
      ) : (
        <>
          <section className="result-heading">
            <div>
              <p className="eyebrow">STEP 2 / HISTORICAL BACKTEST</p>
              <h2>Compare your forks</h2>
            </div>
            <p>Each fork remembers a location and feature combination. Reopen one to rewind and adjust its inputs.</p>
          </section>

          <div className="branch-list" aria-label="Previous experiments">
            {branches.map((branch, index) => (
              <button
                className={`branch ${index === selected ? 'active' : ''}`}
                type="button"
                key={index}
                onClick={() => openBranch(index)}
              >
                <b>{branch.name}</b>
                <small>{branch.result.features.length} variables · {branch.result.location}</small>
              </button>
            ))}
          </div>

          {active && (
            <>
              <section className="stats" aria-label="Measured results on unseen historical hours">
                <article className="panel stat">
                  <span>Model Brier score <i>(lower is better)</i></span>
                  <strong>{active.metrics.brier.toFixed(3)}</strong>
                  <small>Baseline: {active.metrics.baselineBrier.toFixed(3)}</small>
                </article>
                <article className="panel stat">
                  <span>Precision <i>(positive predictions)</i></span>
                  <strong>{percentage(active.metrics.precision)}</strong>
                  <small>Fraction that matched the proxy</small>
                </article>
                <article className="panel stat">
                  <span>Recall <i>(detected positives)</i></span>
                  <strong>{percentage(active.metrics.recall)}</strong>
                  <small>Fraction of proxy-positive hours detected</small>
                </article>
                <article className="panel stat">
                  <span>Test observations</span>
                  <strong>{active.testCount.toLocaleString()}</strong>
                  <small>Later observations held out from training</small>
                </article>
              </section>

              <section className="panel hourly-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">HOURLY OUTLOOK / RETROSPECTIVE</p>
                    <h2>Last 24 test hours · {active.location}</h2>
                    <p>Blue bars estimate whether our sky-condition rule will be met. GO means the model passed a 50% decision threshold; dots indicate actual historical conditions, not verified sightings.</p>
                  </div>
                </div>
                <div className="chart-key"><span className="key-bar" /> Model probability <span className="key-dot" /> Conditions met (observed proxy)</div>
                <div className="hour-chart">
                  {active.hours.map(hour => (
                    <div className="hour-row" key={hour.hour}>
                      <time>{hour.hour.replace('T', ' ').slice(5, 16)}</time>
                      <div className="track"><div className="fill" style={{ width: `${hour.probability}%` }} /></div>
                      <b>{hour.probability.toFixed(0)}%</b>
                      <span className={hour.probability >= 50 ? 'decision-go' : 'decision-wait'}>
                        {hour.probability >= 50 ? 'GO' : 'WAIT'}
                      </span>
                      <span className={hour.observedProxy ? 'actual-yes' : 'actual-no'} title={hour.observedProxy ? 'Proxy conditions met' : 'Proxy conditions not met'}>
                        {hour.observedProxy ? '●' : '○'}
                      </span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel comparison-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">STEP 3 / FORK THE MODEL</p>
                    <h2>What changed when you changed the data?</h2>
                    <p>Change one variable and rerun. Compare held-out accuracy against your previous fork and the simple baseline.</p>
                  </div>
                  <button type="button" className="secondary" onClick={() => document.getElementById('model-builder')?.scrollIntoView({ behavior: 'smooth' })}>↶ Edit variables</button>
                </div>
                <div className="comparison-table-wrap">
                  <table>
                    <thead><tr><th>Fork</th><th>Variables</th><th>Brier ↓</th><th>Baseline ↓</th><th>Precision</th><th>Recall</th></tr></thead>
                    <tbody>
                      {branches.map((branch, index) => (
                        <tr key={index} className={selected === index ? 'highlight-row' : ''}>
                          <td>{branch.name}</td>
                          <td>{branch.result.features.length}</td>
                          <td>{branch.result.metrics.brier.toFixed(3)}</td>
                          <td>{branch.result.metrics.baselineBrier.toFixed(3)}</td>
                          <td>{percentage(branch.result.metrics.precision)}</td>
                          <td>{percentage(branch.result.metrics.recall)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="notes">
                <div className="panel">
                  <p className="eyebrow">HOW WE TRAIN</p>
                  <p>We train logistic regression using {active.trainCount.toLocaleString()} earlier observations and test on {active.testCount.toLocaleString()} unseen hours in {active.location}. A three-hour gap prevents future-label leakage.</p>
                  <p>Selected inputs: {active.features.map(key => VARIABLES.find(variable => variable.key === key)?.name).join(', ')}.</p>
                </div>
                <div className="panel caution">
                  <p className="eyebrow">HONEST LIMITATIONS</p>
                  <p>{active.limitations}</p>
                </div>
              </section>
            </>
          )}
        </>
      )}

      <footer>
        <span>AURORATIME · OXHACK 2026</span>
        <span>NASA OMNI2 + Open-Meteo ERA5 · Astronomy calculations by Astral · Not live forecasting</span>
      </footer>
    </main>
  );
}
