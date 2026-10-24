import type { Simulation } from '../lib/types';
export function Timeline({ results, selected, onSelect }: { results: Simulation[]; selected: string; onSelect: (id: string) => void }) {
  return <nav className="timeline" aria-label="Scenario timeline"><div className="timeline-line" />
    {results.map((result, index) => <button key={result.id} onClick={() => onSelect(result.id)} className={`fork ${selected === result.id ? 'active' : ''}`}><span className="dot">{index + 1}</span><span><b>{result.branchName}</b><small>{result.horizonYears} years · seed {result.seed}</small></span></button>)}
  </nav>;
}
