"""Witness size is diagnostic in semantic mode and binding in strict mode."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
import audit
from checker import verify
from checker_compile import compile_for_checking
from comparison import project_summary
from io_utils import write_csv, write_json


def fixture():
    model = dict(case='SizePair', family='Tiny', nodes=3,
                 edges=[[0, 2, 0, 'keep'], [0, 1, 0, 'keep'], [1, 2, 0, 'keep']],
                 monitors=[], obligation=[0, 2, 0], horizon=2, failures=0)
    graph = compile_for_checking(model)
    paths = []
    def visit(vertex, prefix):
        if vertex == graph['target']:
            paths.append(prefix)
            return
        for edge in graph['out'][vertex]:
            visit(edge['v'], prefix + [edge['id']])
    visit(graph['source'], [])
    paths.sort(key=len)
    certificates = [dict(schema='vcm-certificate-1', case=model['case'],
                         status='infeasible', k=1, all_monitor_count=0, witness=p)
                    for p in (paths[0], paths[-1])]
    for certificate in certificates:
        verify(model, certificate)
    sizes = [len((json.dumps(c, indent=2, sort_keys=True) + '\n').encode('utf-8'))
             for c in certificates]
    assert sizes[0] != sizes[1]
    return model, certificates, sizes


def campaign(path, model, certificate, size):
    path.mkdir(parents=True)
    (path / 'certificates').mkdir()
    row = dict.fromkeys(audit.SEMANTIC_CASE_FIELDS, '0')
    row.update(case=model['case'], family=model['family'], status='infeasible',
               nodes='3', horizon='2', optimal_cost='', accepted='yes',
               certificate_bytes=str(size), producer_ms='0', checker_ms='0')
    write_csv(path / 'cases.csv', [row])
    write_csv(path / 'controls.csv', [dict(control='OwnCase', outcome='rejected')])
    write_json(path / 'summary.json', dict(cases=1, optimal=0, infeasible=1,
                                         vacuous=0, max_certificate_bytes=size))
    write_json(path / 'certificates' / (model['case'] + '.json'), certificate)


class SemanticSummaryTests(unittest.TestCase):
    def test_only_witness_size_is_excluded(self):
        base = dict(cases=1, optimal=0, infeasible=1, max_certificate_bytes=100)
        alternative = dict(base, max_certificate_bytes=120)
        self.assertEqual(project_summary(base, 'semantic'), project_summary(alternative, 'semantic'))
        self.assertNotEqual(project_summary(base, 'strict'), project_summary(alternative, 'strict'))
        for key in ('cases', 'optimal', 'infeasible'):
            changed = dict(alternative, **{key: alternative[key] + 1})
            self.assertNotEqual(project_summary(base, 'semantic'), project_summary(changed, 'semantic'))

    def test_audit_accepts_valid_different_size_witness_only_semantically(self):
        model, certificates, sizes = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected, observed = root / 'results/campaign', root / 'observed'
            campaign(expected, model, certificates[0], sizes[0])
            campaign(observed, model, certificates[1], sizes[1])
            with patch.object(audit, 'ROOT', root), patch.object(audit, 'all_cases', return_value=[model]):
                self.assertEqual(audit.audit_campaign(observed, 'semantic'), 1)
                with self.assertRaises(ValueError):
                    audit.audit_campaign(observed, 'strict')
                changed = json.loads((observed / 'summary.json').read_text())
                changed['infeasible'] = 2
                write_json(observed / 'summary.json', changed)
                with self.assertRaisesRegex(ValueError, 'summary'):
                    audit.audit_campaign(observed, 'semantic')

    @unittest.skipUnless(os.name == 'posix', 'run.py uses the POSIX resource module')
    def test_command_comparison_uses_the_same_contract(self):
        spec = importlib.util.spec_from_file_location('owned_compare_command', ROOT / 'run.py')
        command = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(command)
        model, certificates, sizes = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected, observed = root / 'results/campaign', root / 'observed'
            campaign(expected, model, certificates[0], sizes[0])
            campaign(observed, model, certificates[1], sizes[1])
            with patch.object(command, 'ROOT', root), patch.object(command, 'all_cases', return_value=[model]), patch.object(command, 'install_limits'):
                with patch.object(sys, 'argv', ['run.py', 'compare', '--observed', str(observed), '--mode', 'semantic']):
                    command.main()
                with patch.object(sys, 'argv', ['run.py', 'compare', '--observed', str(observed), '--mode', 'strict']):
                    with self.assertRaises(ValueError):
                        command.main()


if __name__ == '__main__':
    unittest.main()
