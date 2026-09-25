import type { components } from '../generated/api';
import { tr } from '../translations';

type Job = components['schemas']['JobView'];
const phases = {
  loading_model: 'Loading local model', transcribing: 'Transcribing audio',
  extracting: 'Reading transcript', checking: 'Checking evidence and changes',
  diarizing: 'Separating speakers', stage_complete: 'Stage complete',
};

export function JobProgress({job}: {job: Job}) {
  if (job.state === 'complete') return <p className="caption">{tr('Analysis saved. Ready for review.')}</p>;
  const p = job.progress;
  if (!p && !['queued', 'running'].includes(job.state)) return <p className="caption">{tr('Processing stopped. The last observed progress is retained.')}</p>;
  if (!p) return <div className="job-progress"><progress aria-label={tr('Analysis progress')}/><small>{tr(job.state === 'queued' ? 'Waiting for the local worker' : 'Waiting for a progress update')}</small></div>;
  const running = job.state === 'running';
  const age = Math.max(0, Date.now() / 1000 - p.updated_at);
  const elapsed = Math.floor(p.elapsed_seconds + (running ? age : 0));
  const eta = running && p.eta_seconds != null && p.eta_seconds > age ? Math.ceil((p.eta_seconds - age) / 60) : null;
  return <div className="job-progress">
    <div className="progress-heading"><strong>{tr(phases[p.phase])}</strong><span>{tr('Elapsed')}: {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}</span></div>
    <progress aria-label={tr('Current step progress')} max={p.total ?? 1} value={p.total == null ? undefined : p.completed}/>
    <small>{p.total != null ? `${Math.floor(p.completed)} / ${Math.ceil(p.total)} ${tr(p.unit)}` : tr('Preparing local processing')}</small>
    {running && <small>{eta != null ? `${tr('Estimated remaining in this step')}: ~${eta} ${tr('min')}` : tr('Estimating remaining time…')}</small>}
    {running && <small>{tr('Estimates cover this step. Later steps and human review are not included.')}</small>}
    {!running && <small>{tr('Processing stopped. The last observed progress is retained.')}</small>}
  </div>;
}
