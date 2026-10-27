"""pytest plugin（僅變異測試使用）：記錄每個測試 setup+call+teardown 的總耗時到 $MUT_DURATIONS_FILE。"""
import json
import os
from collections import defaultdict

_durations: dict[str, float] = defaultdict(float)


def pytest_runtest_logreport(report):
    _durations[report.nodeid] += report.duration


def pytest_sessionfinish(session, exitstatus):
    path = os.environ.get("MUT_DURATIONS_FILE")
    if path:
        with open(path, "w") as f:
            json.dump(_durations, f)
