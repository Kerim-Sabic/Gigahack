from scripts.qualify import qualification_passed


def test_successful_smoke_cannot_pass_unmeasured_qualification():
    report = {
        "checks": {
            "assets": True,
            "real_browser_workflow": True,
            "target_memory_budgets": True,
            "target_hardware": True,
        },
        "unverified": ["human RO/RU/EN accuracy"],
        "human_accuracy": "not measured",
        "host_egress": "not measured",
        "thermals": "not measured",
    }
    assert not qualification_passed(report)
    assert not qualification_passed({"checks": {"assets": True}})
