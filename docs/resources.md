# Resource and dependency statement

The Linux scientific campaign uses a single Python worker. `run.py` installs a 3 GiB virtual-address-space ceiling and a 2700-second CPU ceiling before model processing. The retained historical full campaign records 7.5145 CPU seconds, 7.5055 wall seconds, and 410,016 KiB peak process RSS. An earlier 13-test contract run records approximately 1.3 wall seconds and 179 MiB peak RSS; it is not the current 29-test suite. These measurements are historical observations, not portable performance guarantees or measurements of the separate Windows standard-library checks.

Producer dependencies are SciPy for the compact LP and NetworkX for integer min-cost circulation. The checker imports neither package; it reconstructs the policy graph and checks the certificate with standard-library Python and exact integers. The producer fails closed if a floating-point candidate cannot be paired with an exact primal/dual certificate.

No dependency source was modified. No external solver executable, paper PDF, routing trace, topology, binary wheel, cache, model weight, or private file is bundled. The artifact contains only owned source, owned synthetic JSON, outputs, documentation, and the repository license.
