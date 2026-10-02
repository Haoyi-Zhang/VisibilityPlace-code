"""Conservative single-process scientific resource guard."""
from __future__ import annotations

import resource


def install_limits():
    # Leave headroom under the project ceilings.  RLIMIT_AS is unavailable on
    # some non-Unix systems; this repository targets the supplied Linux route.
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (2700, 2700))
