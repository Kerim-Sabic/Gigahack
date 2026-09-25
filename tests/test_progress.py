import json

from services.api.progress import ProgressReporter, read_progress


def test_eta_requires_observed_work_and_never_implies_job_success(tmp_path):
    clock = [0.0]
    folder = tmp_path / "jobs/j"
    reporter = ProgressReporter(folder, "whisper", clock=lambda: clock[0], wall_clock=lambda: clock[0])
    reporter.begin("transcribing", 100, "seconds")
    clock[0] = 5
    reporter.advance(10)
    assert json.loads((folder / "progress.json").read_text())["eta_seconds"] is None
    clock[0] = 10
    reporter.advance(20)
    observed = read_progress(tmp_path, {"id": "j", "state": "running", "stage": "whisper"})
    assert observed["eta_seconds"] == 40 and observed["eta_scope"] == "current_phase"
    assert "state" not in observed  # Database publication is authoritative.
    assert read_progress(tmp_path, {"id": "j", "state": "queued", "stage": "whisper"}) is None
    assert read_progress(tmp_path, {"id": "j", "state": "running", "stage": "extract"}) is None


def test_corrupt_progress_is_unknown_not_zero_success(tmp_path):
    folder = tmp_path / "jobs/j"
    folder.mkdir(parents=True)
    (folder / "progress.json").write_text('{"completed":100}')
    assert read_progress(tmp_path, {"id": "j", "state": "running", "stage": "whisper"}) is None


def test_resumed_work_is_not_counted_as_new_eta_throughput(tmp_path):
    clock = [0.0]
    reporter = ProgressReporter(tmp_path, 'whisper', clock=lambda: clock[0], wall_clock=lambda: clock[0])
    reporter.begin('transcribing', 100, 'seconds', initial_completed=60)
    clock[0] = 5
    reporter.advance(70)
    clock[0] = 10
    reporter.advance(80)
    observed = json.loads((tmp_path / 'progress.json').read_text())
    assert observed['eta_seconds'] == 10  # 20 new units / 10 seconds; 20 units remain.
