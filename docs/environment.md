# Environment and dependency record

## Historical retained campaign

The retained 120-case campaign preserved its model inputs, certificate objects, case rows, control outcomes, summary, derived manuscript data, and resource observations. It did **not** preserve a recoverable Python/NumPy/SciPy/HiGHS/NetworkX fingerprint. The historical record therefore remains usable as finite evidence, but its missing versions are unknown and are not reconstructed from guesswork.

Historical retained resource observations are approximately 7.51 wall seconds, 7.51 campaign CPU seconds, and 410,016 KiB peak process RSS. They are descriptive for that run only.

## Current repair/replay environment

The following values were queried directly in the environment used for the current repair and replay:

| Component | Observed value |
|---|---|
| OS/kernel | Linux 6.18.44, x86-64 |
| C library | glibc 2.41 |
| Python | CPython 3.13.5 (GCC 14.2.0) |
| pip | 25.1.1 |
| NumPy | 2.3.5 |
| SciPy | 1.17.0 |
| bundled HiGHS | 1.8.0, from `scipy.optimize._highspy._core` constants |
| NetworkX | 3.6.1 |
| standalone `highspy` | not installed; SciPy's bundled interface was used |

The corresponding producer dependency file is:

```text
numpy==2.3.5
scipy==1.17.0
networkx==3.6.1
```

## Installation

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade 'pip==25.1.1'
python -m pip install -r requirements-producer.txt
python - <<'PY'
import platform, sys
import numpy, scipy, networkx
from scipy.optimize._highspy import _core
print(platform.platform())
print(sys.version)
print('NumPy', numpy.__version__)
print('SciPy', scipy.__version__)
print('HiGHS', _core.HIGHS_VERSION_MAJOR,
      _core.HIGHS_VERSION_MINOR,
      _core.HIGHS_VERSION_PATCH)
print('NetworkX', networkx.__version__)
PY
```

The exact operating-system package installation route is outside the repository and may differ by host. A Python 3.13 environment with wheels for the pinned packages was used here.

## Which commands need producer dependencies

The following commands invoke certificate production or production-based exact checks and therefore require NumPy, SciPy, and NetworkX:

```text
python3 test.py
python3 fuzz.py --out ...
python3 run.py pilot --out ...
python3 run.py reproduce --out ...
```

`exhaustive.py` uses only the repository's finite combinatorial logic and standard library. Once result directories exist, `run.py compare`, `audit.py`, and `run.py check` do not need the producer solver packages. The documented `python3 -S run.py check ...` invocation disables site packages and is the explicit checker-only test.

## Reproduction meanings

A strict comparison in the pinned environment compares exact certificate objects and the floating producer diagnostics `lp_objective` and `rounding_alpha`, excluding run-local producer/checker milliseconds. It is the repository's fixed-environment object-replication contract, not a guarantee across arbitrary BLAS, solver, Python, or dependency releases.

A semantic comparison validates each new certificate against the current model and compares the status and certified optimum together with deterministic model/baseline fields. It excludes floating producer diagnostics and witness identity. Semantic replay is therefore the portable validity contract when a solver may choose a different but equally valid witness.
