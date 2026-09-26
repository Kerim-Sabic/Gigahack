"""Actual process-crash rehearsal on explicitly synthetic text; never acoustic gold."""

import os
import subprocess
import sys


def run():
    import io
    import json
    import secrets
    import subprocess
    import sys
    import time
    import wave
    from pathlib import Path
    import httpx
    import psutil
    from playwright.sync_api import sync_playwright, expect

    root = Path(__file__).resolve().parents[1]
    folder = root / ".runtime" / ("app-crash-" + str(time.time_ns()))
    folder.mkdir(parents=True)
    origin = "http://127.0.0.1:18765"
    os.environ.update(MOM_DATA=str(folder), MOM_ORIGIN=origin)
    from services.api.db import transaction, canonical, uid
    from services.worker.supervisor import kill_tree
    from services.api.domain import reduce_events
    from scripts.variation_checks import check_variation

    owned = []
    model_children = []
    logs = []

    def start(module, args=()):
        f = (folder / (module.replace(".", "-") + "-" + str(len(logs)) + ".log")).open("wb")
        logs.append(f)
        p = subprocess.Popen([sys.executable, "-m", module, *args], stdout=f, stderr=f)
        owned.append(p)
        return p

    def api_start():
        p = start("uvicorn", ("services.api.main:app", "--host", "127.0.0.1", "--port", "18765"))
        for _ in range(60):
            if p.poll() is not None:
                raise RuntimeError("API exited")
            try:
                if httpx.get(origin, trust_env=False).status_code == 200:
                    return p
            except httpx.TransportError:
                pass
            time.sleep(0.5)
        raise RuntimeError("API startup timeout")

    def network():
        from scripts.qualify_isolated_app import network_proof

        proof = network_proof()
        if not proof["enforced"]:
            raise RuntimeError("Isolated network boundary not established")
        return proof

    report = {
        "folder": str(folder),
        "scope": "Actual API/supervisor hard crash and restart with actual Qwen, seeded synthetic reviewed transcript over silence; not acoustic recognition or power-loss qualification",
        "network_before": network(),
    }
    started = time.monotonic()
    try:
        api = api_start()
        guard = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"])
        owned.append(guard)
        with httpx.Client(base_url=origin, timeout=30, trust_env=False) as client:
            password = secrets.token_urlsafe(24)
            r = client.post("/api/v1/setup", json={"name": "crash-review", "password": password})
            r.raise_for_status()
            client.headers["x-csrf-token"] = r.json()["csrf"]
            r = client.post(
                "/api/v1/meetings",
                json={
                    "title": "Synthetic recovery rehearsal",
                    "date": "2027-06-01",
                    "timezone": "Europe/Chisinau",
                },
            )
            r.raise_for_status()
            meeting = r.json()
            base = "/api/v1/meetings/" + meeting["id"]
            stream = io.BytesIO()
            with wave.open(stream, "wb") as w:
                w.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                w.writeframes(b"\0\0" * 32000)
            r = client.post(
                base + "/uploads", files={"file": ("synthetic-silence.wav", stream.getvalue(), "audio/wav")}
            )
            r.raise_for_status()
            asset = r.json()["id"]
            with transaction() as c:
                for i, text in enumerate(
                    [
                        "Проверка лифта назначена на 9 июня, согласовано.",
                        "Может быть, перенесём проверку на 11 июня?",
                    ]
                ):
                    c.execute(
                        "INSERT INTO segments(id,meeting_id,asset_id,revision,start,end,text,raw) VALUES(?,?,?,1,?,?,?,?)",
                        (
                            uid(),
                            meeting["id"],
                            asset,
                            i * 16000,
                            (i + 1) * 16000,
                            text,
                            canonical({"origin": "explicit synthetic text fixture, not observed speech"}),
                        ),
                    )
            r = client.post(
                base + "/jobs", json={"asset_id": asset, "device": "cuda", "transcript_only": True}
            )
            r.raise_for_status()
            job = r.json()
            jobdir = folder / "jobs" / job["id"]
            report.update(job_id=job["id"], meeting_id=meeting["id"])
            (folder / "run.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report), flush=True)
            worker = start("services.worker.supervisor")
            deadline = time.monotonic() + 300
            while not list(jobdir.glob("extraction-checkpoints/*/event-*.json")):
                state = client.get(base).json()["jobs"][0]
                if state["state"] in ("failed", "complete"):
                    raise RuntimeError(
                        "No event checkpoint before " + state["state"] + ": " + str(state["error"])
                    )
                if time.monotonic() > deadline:
                    raise RuntimeError("Checkpoint observation deadline")
                time.sleep(0.2)
            children = [(p.pid, p.create_time()) for p in psutil.Process(worker.pid).children(recursive=True)]
            model_children = children
            worker.kill()
            worker.wait()
            api.kill()
            api.wait()
            report["killed_after_event_checkpoints"] = len(
                list(jobdir.glob("extraction-checkpoints/*/event-*.json"))
            )
            for _ in range(100):
                alive = []
                for pid, created in children:
                    try:
                        p = psutil.Process(pid)
                        if p.create_time() == created and p.status() != psutil.STATUS_ZOMBIE:
                            alive.append(pid)
                    except psutil.NoSuchProcess:
                        pass
                if not alive:
                    break
                time.sleep(0.1)
            assert not alive, ("owned model descendants survived", alive)
            assert guard.poll() is None
            report["owned_descendants_reaped"] = len(children)
            report["unrelated_process_survived"] = True
            with transaction() as c:
                report["pre_restart_candidates"] = c.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            assert report["pre_restart_candidates"] == 0
            print(json.dumps({"crash_verified": True, **report}), flush=True)
            api = api_start()
            worker = start("services.worker.supervisor")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                page.goto(origin)
                page.get_by_label("Username", exact=True).fill("crash-review")
                page.get_by_label("Password (12+ characters)", exact=True).fill(password)
                page.get_by_role("button", name="Continue").click()
                page.get_by_text("Synthetic recovery rehearsal", exact=True).click()
                deadline = time.monotonic() + 360
                while True:
                    detail = client.get(base).json()
                    state = detail["jobs"][0]
                    if state["state"] in ("complete", "failed", "cancelled"):
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError("Recovery observation deadline")
                    page.wait_for_timeout(1000)
                assert state["state"] == "complete", state
                expect(page.locator(".pageheading .badge").first).to_have_text(
                    "awaiting review", timeout=10000
                )
                page.screenshot(path=str(folder / "recovered-ui.png"))
                browser.close()
            ledger = client.get(base + "/items").json()
            checks = check_variation(
                {"category": "action", "status": "confirmed", "due": "2027-06-09", "pending": True},
                [x["body"] for x in ledger["candidates"]],
                reduce_events(ledger["candidates"]),
            )
            assert all(checks.values()), checks
            output = json.loads((jobdir / "extract-output.json").read_text())
            assert output["reused_units"]["group"] >= 1 and output["reused_units"]["event"] >= 1
            with transaction() as c:
                report["attempts"] = c.execute(
                    "SELECT attempt FROM jobs WHERE id=?", (job["id"],)
                ).fetchone()[0]
                report["counts"] = {
                    t: c.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
                    for t in ("candidates", "accepted_events", "snapshots", "outbox")
                }
            assert report["attempts"] == 2
            assert (
                report["counts"]["accepted_events"]
                == report["counts"]["snapshots"]
                == report["counts"]["outbox"]
                == 0
            )
            report.update(
                checks=checks,
                reused_units=output["reused_units"],
                elapsed_seconds=time.monotonic() - started,
                network_after=network(),
                status="PASS",
            )
            (folder / "report.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report), flush=True)
    finally:
        for pid, created in model_children:
            try:
                descendant = psutil.Process(pid)
                if descendant.create_time() == created:
                    descendant.kill()
            except psutil.NoSuchProcess:
                pass
        for p in reversed(owned):
            if p.poll() is None:
                kill_tree(p.pid)
            p.wait()
        for f in logs:
            f.close()


def main():
    if sys.platform != "linux":
        raise SystemExit("Use prepared Linux/WSL; this command does not change the Windows firewall.")
    if "--inside" not in sys.argv:
        raise SystemExit(
            subprocess.call(
                ["unshare", "-Urn", sys.executable, "-m", "scripts.qualify_crash_recovery", "--inside"]
            )
        )
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
    run()


if __name__ == "__main__":
    main()
