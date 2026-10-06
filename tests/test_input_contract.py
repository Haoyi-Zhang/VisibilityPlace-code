"""Solver-free regressions for the declared model/certificate input contract."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from checker import Rejected, verify
from instances import all_cases
from io_utils import load_json, parse_json, write_json
from model import validate_model


class InputContractTests(unittest.TestCase):
    def test_policy_action_requires_string(self):
        for value in ([], {}, None, True, 0):
            model = deepcopy(all_cases()[0])
            model["edges"][0][3] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "policy action"):
                validate_model(model)

    def test_flow_edge_identifier_requires_string(self):
        model = all_cases()[0]
        certificate = load_json(ROOT / "results/campaign/certificates/T000.json")
        for value in ([], {}, None, True, 0):
            candidate = deepcopy(certificate)
            candidate["flow"][0][0] = value
            with self.subTest(value=value), self.assertRaisesRegex(Rejected, "positive flow entry"):
                verify(model, candidate)

    def test_duplicate_json_fields_rejected_at_every_object_depth(self):
        for text in ('{"cost":0,"cost":1}',
                     '{"outer":{"case":"First","case":"Second"}}'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "duplicate JSON"):
                parse_json(text)
        self.assertEqual({"case": "A", "cost": 1}, parse_json('{"case":"A","cost":1}'))

    def test_non_json_numeric_constants_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "non-JSON"):
                parse_json('{"cost":' + value + '}')

    def test_json_writer_uses_utf8_and_literal_lf(self):
        with patch.object(Path, "write_text", autospec=True) as writer:
            write_json("unused-owned-output.json", {"cost": 1})
        writer.assert_called_once_with(Path("unused-owned-output.json"),
                                       '{\n  "cost": 1\n}\n',
                                       encoding="utf-8", newline="\n")


if __name__ == "__main__":
    unittest.main()
