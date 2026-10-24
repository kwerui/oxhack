'use client';
import { useState } from 'react';
import { runSimulation } from '../lib/api';
import { initialInputs, type Inputs, type Simulation } from '../lib/types';
import { formatMetric } from '../lib/format';
import { ControlPanel } from '../components/ControlPanel';
import { Timeline } from '../components/Timeline';
import { DistributionChart } from '../components/DistributionChart';

export default function Home() {
  const [inputs, setInputs] = useState<Inputs>(initialInputs); const [results, setResults] = useState<Simulation[]>([]); const [selected, setSelected] = useState(''); const [running, setRunning] = useState(false); const [error, setError] = useState('');
  async function run() { setRunning(true); setError(''); try { const result = await runSimulation(inputs); setResults(previous => [...previous.slice(-2), result]); setSelected(result.id); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to simulate'); } finally { setRunning(false); } }
  const active = results.find(result => result.id === selected) ?? results.at(-1);
  return <main><header><div className="brand"><span>⟡</span> TIMEFORK</div><div className="tag">DECISION EXPLORER <i /></div><p>Simulate branches. Inspect uncertainty. Decide with your eyes open.</p></header>
    <section className="hero"><div><p className="eyebrow">SCENARIO LAB / 01</p><h1>Explore the <em>shape</em><br />of tomorrow.</h1><p className="lede">A transparent Monte Carlo sandbox for comparing possibilities—not predicting the future.</p></div><div className="hero-orbit"><span>NOW</span><i /><b>FUTURE<br/>FIELD</b></div></section>
    <ControlPanel inputs={inputs} setInputs={setInputs} onRun={run} running={running} />
    {error && <p className="error" role="alert">{error}. Start the API at port 8000, then try again.</p>}
    {results.length === 0 ? <section className="empty panel"><p className="eyebrow">READY WHEN YOU ARE</p><h2>Run your first timeline</h2><p>Adjust the variables, then generate thousands of reproducible paths. Add another branch to compare choices side by side.</p></section> : <><section className="results-head"><div><p className="eyebrow">TIMELINE MAP</p><h2>Forks from the same present</h2></div><p>{results.length}/3 visible branches</p></section><Timeline results={results} selected={selected} onSelect={setSelected} /><DistributionChart results={results} />
      {active && <section className="metrics"><div className="panel metric-intro"><p className="eyebrow">RISK SIGNALS</p><h2>{active.branchName}</h2><p>{active.runs.toLocaleString()} paths · {active.horizonYears} years · seed {active.seed}</p></div>{active.metrics.map(metric => <article className="panel metric" key={metric.label}><p>{metric.label}</p><strong>{formatMetric(metric.value, metric.format)}</strong><small>{metric.detail}</small></article>)}</section>}
      {active && <section className="notes"><article><p className="eyebrow">MODEL ASSUMPTIONS</p>{active.assumptions.map(item => <p key={item}>• {item}</p>)}</article><article className="caution"><p className="eyebrow">READ BEFORE USING</p>{active.caveats.map(item => <p key={item}>• {item}</p>)}</article></section>}</>}
    <footer><span>TIMEFORK / HACKATHON MVP</span><span>Illustrative simulations only. Not financial, medical, or engineering advice.</span></footer>
  </main>;
}
