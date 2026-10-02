#!/usr/bin/env python3
"""Run contract tests under the same single-process resource guard."""
from pathlib import Path
import json
import resource
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from bounds import install_limits
install_limits()
start = time.perf_counter()
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({
    "tests": result.testsRun,
    "failures": len(result.failures),
    "errors": len(result.errors),
    "passed": result.wasSuccessful(),
    "wall_seconds": time.perf_counter() - start,
    "process_cpu_seconds_recorded": time.process_time(),
    "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
}, sort_keys=True))
raise SystemExit(0 if result.wasSuccessful() else 1)
