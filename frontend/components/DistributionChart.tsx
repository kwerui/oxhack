import type { Simulation } from '../lib/types';

export function DistributionChart({ results }: { results: Simulation[] }) {
  const colors = ['#B8F560', '#A78BFA', '#67E8F9'];
  const max = Math.max(1, ...results.flatMap(result => result.histogram.map(bin => bin.count)));
  return <section className="panel chart-panel" aria-labelledby="distribution-title">
    <div className="panel-heading"><div><p className="eyebrow">OUTCOME DISTRIBUTION</p><h2 id="distribution-title">Where each timeline can land</h2></div><span className="chart-key"><i /> Base & branches</span></div>
    <div className="bars" role="img" aria-label="Histogram comparing simulated outcome distributions">
      {results[0]?.histogram.map((_, index) => <div className="bar-group" key={index}>
        {results.map((result, resultIndex) => <div key={result.id} className="bar" style={{height: `${(result.histogram[index].count / max) * 100}%`, background: colors[resultIndex % colors.length]}} title={`${result.branchName}: ${result.histogram[index].count} paths`} />)}
      </div>)}
    </div>
    <div className="chart-labels"><span>Lower outcomes</span><span>More likely regions</span><span>Higher outcomes</span></div>
  </section>;
}
