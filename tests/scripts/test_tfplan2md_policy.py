import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "tfplan2md-policy.py"
    spec = importlib.util.spec_from_file_location("tfplan2md_policy", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tfplan2MdPolicyTests(unittest.TestCase):
    def test_policy_allows_named_actor_on_develop(self):
        module = load_module()
        policy = {
            "rules": [
                {
                    "name": "terraform changes only by release owner on develop",
                    "when": {"hasChanges": True},
                    "allow": {"actors": ["alice"], "targetBranches": ["develop"]},
                }
            ]
        }
        context = {"actor": "alice", "targetBranch": "develop", "sourceBranch": "feature/plan", "hasChanges": True}

        result = module.evaluate_policy(policy, context)

        self.assertTrue(result["allowed"])
        self.assertEqual(["terraform changes only by release owner on develop"], result["matchedRules"])

    def test_policy_denies_named_actor_on_wrong_branch(self):
        module = load_module()
        policy = {
            "rules": [
                {
                    "name": "terraform changes only by release owner on develop",
                    "when": {"hasChanges": True},
                    "allow": {"actors": ["alice"], "targetBranches": ["develop"]},
                    "message": "Terraform changes require alice and develop.",
                }
            ]
        }
        context = {"actor": "alice", "targetBranch": "main", "sourceBranch": "feature/plan", "hasChanges": True}

        result = module.evaluate_policy(policy, context)

        self.assertFalse(result["allowed"])
        self.assertEqual("terraform changes only by release owner on develop", result["failures"][0]["rule"])
        self.assertIn("target branch 'main' is not allowed", result["failures"][0]["reasons"])

    def test_detect_has_changes_from_plan_json(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = Path(temp_dir) / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "resource_changes": [
                            {"change": {"actions": ["no-op"]}},
                            {"change": {"actions": ["update"]}},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(module.detect_has_changes(str(plan_path)))


if __name__ == "__main__":
    unittest.main()
