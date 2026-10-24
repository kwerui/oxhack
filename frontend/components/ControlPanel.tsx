import type { Inputs } from '../lib/types';
const fields: {key: keyof Inputs; label: string; step: number; suffix?: string}[] = [
  {key:'horizonYears', label:'Horizon', step:1, suffix:'years'}, {key:'initialValue', label:'Starting value', step:1000, suffix:'£'}, {key:'annualContribution', label:'Annual contribution', step:500, suffix:'£'}, {key:'expectedAnnualReturn', label:'Expected annual return', step:0.01, suffix:'%'}, {key:'annualVolatility', label:'Annual volatility', step:0.01, suffix:'%'}, {key:'inflationRate', label:'Inflation', step:0.005, suffix:'%'}, {key:'targetValue', label:'Target value', step:1000, suffix:'£'}
];
export function ControlPanel({ inputs, setInputs, onRun, running }: {inputs: Inputs; setInputs: (next: Inputs) => void; onRun: () => void; running: boolean}) {
  return <aside className="controls panel"><div className="panel-heading"><div><p className="eyebrow">FORK CONTROLS</p><h2>Change one reality</h2></div></div>
    <label className="branch-label">Scenario label<input value={inputs.branchName} onChange={e => setInputs({...inputs, branchName:e.target.value})} /></label>
    <div className="input-grid">{fields.map(field => { const numericValue = inputs[field.key] as number; const display = field.suffix === '%' ? numericValue * 100 : numericValue; return <label key={field.key}>{field.label}<span className="number-input"><input type="number" step={field.step} value={display} onChange={e => {const value = Number(e.target.value); setInputs({...inputs, [field.key]: field.suffix === '%' ? value / 100 : value})}}/><em>{field.suffix}</em></span></label>})}</div>
    <button className="primary" onClick={onRun} disabled={running}>{running ? 'Simulating timelines…' : 'Run this timeline'} <span>↗</span></button>
    <p className="seed-note">Seed {inputs.seed} makes this run reproducible. Change it to explore a new sample.</p>
  </aside>;
}
