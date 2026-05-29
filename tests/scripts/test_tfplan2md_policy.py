import json
import tempfile
import unittest
from pathlib import Path
from module_loader import load_script_module


class Tfplan2MdPolicyTests(unittest.TestCase):
    def test_policy_allows_named_actor_on_develop(self):
        module = load_script_module("tfplan2md_policy", "tfplan2md-policy.py")
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
        module = load_script_module("tfplan2md_policy", "tfplan2md-policy.py")
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
        module = load_script_module("tfplan2md_policy", "tfplan2md-policy.py")
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
