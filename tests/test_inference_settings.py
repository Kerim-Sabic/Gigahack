import json

import httpx
import pytest
from pydantic import ValidationError

from services.worker.settings import InferenceSettings, load_settings, settings_for
from services.worker.stage import bounded_completion


def test_invalid_budgets_and_model_paths_fail_before_loading():
    profile = load_settings().model_dump()
    for changes in (
        {"model_directory": "../other"},
        {"model_file": "https://remote/model.gguf"},
        {"source_window_tokens": 4000},
        {"reasoning_tokens": 4096},
        {"micro_batch_size": 512, "batch_size": 256},
    ):
        with pytest.raises(ValidationError):
            InferenceSettings.model_validate({**profile, "llm": {**profile["llm"], **changes}})


def test_frozen_job_settings_do_not_read_changed_developer_file(monkeypatch):
    from services.worker import settings

    frozen = load_settings().model_dump()
    monkeypatch.setattr(settings, "load_settings", lambda: (_ for _ in ()).throw(AssertionError("must use snapshot")))
    assert settings_for({"config": {"inference": frozen}}).model_dump() == frozen


def test_custom_context_and_reasoning_reach_template_and_completion(tmp_path):
    base = load_settings().model_dump()
    llm = InferenceSettings.model_validate({**base, "llm": {**base["llm"], "context_tokens": 8192, "reasoning_tokens": 128}}).llm
    seen = []

    def handle(request):
        payload = json.loads(request.content)
        seen.append((request.url.path, payload))
        if request.url.path == "/apply-template":
            return httpx.Response(200, json={"prompt": "template"})
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": list(range(5000))})
        return httpx.Response(200, json={"choices": []})

    with httpx.Client(transport=httpx.MockTransport(handle), base_url="http://local.test") as client:
        bounded_completion(client, {"messages": [], "max_tokens": 100, "response_format": {"json_schema": {"name": "fields"}}}, tmp_path / "raw.jsonl", llm)
    assert seen[0][1]["chat_template_kwargs"]["enable_thinking"] is True
    assert seen[-1][1]["max_tokens"] == 260
