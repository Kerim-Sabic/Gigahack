"""Local resource sampling with explicit attribution and observation health.

NVIDIA WDDM can expose total memory while withholding per-process use. Missing
attribution remains None; idle subtraction is only an estimate, never a budget gate.
"""

import csv
import io
import subprocess
import time

import psutil


def number(value):
    try:
        parsed = float(value.strip())
        return parsed if parsed >= 0 else None
    except (ValueError, AttributeError):
        return None


def parse_devices(text):
    result = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 6:
            continue
        index, ident, name, total, used, temperature = [item.strip() for item in row]
        result[ident] = {
            "index": index,
            "name": name,
            "total_mib": number(total),
            "used_mib": number(used),
            "temperature_c": number(temperature),
        }
    return result


def parse_processes(text):
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 3:
            continue
        ident, pid, memory = [item.strip() for item in row]
        if pid.isdigit():
            rows.append({"gpu_uuid": ident, "pid": int(pid), "used_mib": number(memory)})
    return rows


def query_gpu():
    def run(query):
        return subprocess.run(
            ["nvidia-smi", query, "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout

    result = {"devices": {}, "processes": [], "errors": []}
    try:
        result["devices"] = parse_devices(
            run("--query-gpu=index,uuid,name,memory.total,memory.used,temperature.gpu")
        )
        if not result["devices"]:
            result["errors"].append("gpu_inventory_empty_or_unparseable")
    except (OSError, subprocess.SubprocessError):
        result["errors"].append("gpu_inventory_unavailable")
    try:
        result["processes"] = parse_processes(run("--query-compute-apps=gpu_uuid,pid,used_gpu_memory"))
    except (OSError, subprocess.SubprocessError):
        result["errors"].append("gpu_process_attribution_unavailable")
    return result


class ResourceSampler:
    def __init__(self, baseline=None):
        self.baseline = baseline if baseline is not None else query_gpu()
        self.devices = {}
        self.samples = 0
        self.attributed_samples = 0
        self.errors = {}
        self.peak_tree_rss = None
        self.peak_host_used = None
        self.peak_owned_gpu_processes = None
        self.started = time.time()
        for code in self.baseline["errors"]:
            self.errors[code] = self.errors.get(code, 0) + 1

    def observe_gpu(self, sample, owned_pids):
        self.samples += 1
        for code in sample["errors"]:
            self.errors[code] = self.errors.get(code, 0) + 1
        owned = [r for r in sample["processes"] if r["pid"] in owned_pids]
        if owned:
            self.peak_owned_gpu_processes = max(
                self.peak_owned_gpu_processes or 0, len({r["pid"] for r in owned})
            )
        for ident, device in sample["devices"].items():
            target = self.devices.setdefault(
                ident,
                {
                    "index": device["index"],
                    "name": device["name"],
                    "total_mib": device["total_mib"],
                    "idle_total_mib": self.baseline["devices"].get(ident, {}).get("used_mib"),
                    "peak_total_mib": None,
                    "peak_owned_process_mib": None,
                    "peak_temperature_c": None,
                    "attributed_samples": 0,
                },
            )
            for source, destination in [
                ("used_mib", "peak_total_mib"),
                ("temperature_c", "peak_temperature_c"),
            ]:
                value = device[source]
                if value is not None:
                    target[destination] = max(target[destination] or 0, value)
            on_device = [r for r in owned if r["gpu_uuid"] == ident]
            if on_device and all(r["used_mib"] is not None for r in on_device):
                target["peak_owned_process_mib"] = max(
                    target["peak_owned_process_mib"] or 0, sum(r["used_mib"] for r in on_device)
                )
                target["attributed_samples"] += 1
                self.attributed_samples += 1

    def sample(self, pid):
        owned = set()
        try:
            parent = psutil.Process(pid)
            processes = [parent, *parent.children(recursive=True)]
            owned = {process.pid for process in processes}
            rss = sum(process.memory_info().rss for process in processes)
            self.peak_tree_rss = max(self.peak_tree_rss or 0, rss)
        except psutil.Error:
            self.errors["process_tree_memory_unavailable"] = (
                self.errors.get("process_tree_memory_unavailable", 0) + 1
            )
        try:
            memory = psutil.virtual_memory()
            self.peak_host_used = max(self.peak_host_used or 0, memory.total - memory.available)
        except (OSError, psutil.Error):
            self.errors["host_memory_unavailable"] = self.errors.get("host_memory_unavailable", 0) + 1
        self.observe_gpu(query_gpu(), owned)

    def report(self):
        devices = []
        for device in self.devices.values():
            idle, peak = device["idle_total_mib"], device["peak_total_mib"]
            devices.append(
                {
                    **device,
                    "approximate_peak_minus_idle_mib": max(0, peak - idle)
                    if idle is not None and peak is not None
                    else None,
                }
            )
        return {
            "scope": "stage subprocess and observed descendants; device total includes unrelated activity",
            "sample_interval_seconds": 1,
            "samples": self.samples,
            "elapsed_seconds": time.time() - self.started,
            "gpu_devices": devices,
            "peak_process_tree_rss_bytes": self.peak_tree_rss,
            "rss_scope": "sum of RSS; shared pages may be counted more than once",
            "peak_host_used_bytes": self.peak_host_used,
            "peak_observed_owned_gpu_processes": self.peak_owned_gpu_processes,
            "monitor_errors": self.errors,
            "process_gpu_attribution": "measured samples" if self.attributed_samples else "not measured",
            "model_allocator_bytes": None,
            "model_allocator_status": "not exposed by a common trusted interface",
            "idle_subtraction_scope": "approximation only; not authoritative process memory and not a target-fit gate",
        }
