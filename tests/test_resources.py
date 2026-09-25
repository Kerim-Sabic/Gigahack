from services.worker.resources import ResourceSampler, parse_devices, parse_processes


def sample(memory="1024", used="1800"):
    return {
        "devices": parse_devices(f"0, GPU-test, Test GPU, 8192, {used}, 45"),
        "processes": parse_processes(f"GPU-test, 20, {memory}"),
        "errors": [],
    }


def test_gpu_attribution_separates_unrelated_total_and_owned_process():
    monitor = ResourceSampler(
        {"devices": parse_devices("0, GPU-test, Test GPU, 8192, 700, 40"), "processes": [], "errors": []}
    )
    reading = sample()
    reading["processes"] += parse_processes("GPU-test, 99, 300")
    monitor.observe_gpu(reading, {20})
    device = monitor.report()["gpu_devices"][0]
    assert device["peak_total_mib"] == 1800
    assert device["peak_owned_process_mib"] == 1024
    assert device["approximate_peak_minus_idle_mib"] == 1100


def test_wddm_unavailable_process_memory_is_never_zero_success():
    monitor = ResourceSampler(sample("N/A"))
    monitor.observe_gpu(sample("[N/A]"), {20})
    report = monitor.report()
    assert report["gpu_devices"][0]["peak_total_mib"] == 1800
    assert report["gpu_devices"][0]["peak_owned_process_mib"] is None
    assert report["process_gpu_attribution"] == "not measured"
    assert report["peak_process_tree_rss_bytes"] is None


def test_missing_monitor_and_unrelated_processes_do_not_claim_attribution():
    monitor = ResourceSampler({"devices": {}, "processes": [], "errors": ["gpu_inventory_unavailable"]})
    monitor.observe_gpu(sample(), {77})
    assert monitor.report()["gpu_devices"][0]["peak_owned_process_mib"] is None
    assert monitor.report()["monitor_errors"]["gpu_inventory_unavailable"] == 1
