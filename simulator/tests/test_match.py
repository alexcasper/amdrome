"""League runner tests (dawn-safe: 2-episode scale)."""

import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


class TestRunMatch(unittest.TestCase):
    def test_match_deterministic(self):
        runs = []
        for _ in range(2):
            out = subprocess.run(
                [sys.executable, os.path.join(ROOT, "bin", "run_match.py"),
                 "--agents", os.path.join(ROOT, "agents", "blind.py"),
                 "--seed", "7", "--episodes", "2"],
                capture_output=True, text=True, check=True)
            runs.append(out.stdout)
        self.assertEqual(runs[0], runs[1])

    def test_summary_present(self):
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "run_match.py"),
             "--agents", os.path.join(ROOT, "agents", "blind.py"),
             os.path.join(ROOT, "agents", "cautious.py"),
             "--seed", "9", "--episodes", "1"],
            capture_output=True, text=True, check=True)
        lines = out.stdout.strip().splitlines()
        summary = json.loads(lines[-1])
        self.assertTrue(summary["summary"])
        self.assertEqual(sorted(summary["agents"]),
                         ["blind", "cautious"])

    def test_validator_rejects_garbage(self):
        bad = "/tmp/_amdrome_bad_agent.py"
        with open(bad, "w") as f:
            f.write("def act(obs):\n    return {'caps': [1, 2, 3]}\n")
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "envs", "kaggle_env",
                                          "validate_agents.py"), bad],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("FAIL", out.stdout)


if __name__ == "__main__":
    unittest.main()
