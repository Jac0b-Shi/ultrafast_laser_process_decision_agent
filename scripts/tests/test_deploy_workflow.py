"""Exercise deployment commands with the same piped stdin used by the runner."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


class DeploymentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        config = yaml.safe_load((root / ".workflow/main-docker-deploy.yml").read_text())
        deploy = next(stage for stage in config["stages"] if stage["name"] == "deploy")
        cls.script = deploy["steps"][0]["script"][0]

    def run_shell(self, script, docker="cat >/dev/null\n", compose="exit 2\n"):
        with tempfile.TemporaryDirectory() as folder:
            for name, body in (("docker", docker), ("docker-compose", compose)):
                path = Path(folder) / name
                path.write_text("#!/bin/sh\n" + body)
                path.chmod(0o755)
            env = {**os.environ, "PATH": folder + os.pathsep + os.environ["PATH"]}
            return subprocess.run(
                ["bash", "-Eeuo", "pipefail"], input=script, text=True,
                capture_output=True, env=env, timeout=10,
            )

    def test_control_reproduces_premature_success(self):
        result = self.run_shell("docker compose run web\nprintf 'AFTER_CHECK\\n'\n")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("AFTER_CHECK", result.stdout)

    def test_runtime_checks_preserve_remaining_deployment_input(self):
        commands = [line.strip() for line in self.script.splitlines()
                    if "$COMPOSE" in line and "node scripts/check-runtime.cjs" in line]
        self.assertEqual(len(commands), 1)  # Running-container check.
        commands += [line.strip() for line in self.script.splitlines()
                     if "$COMPOSE" in line and "--entrypoint node" in line]
        self.assertEqual(len(commands), 2)
        for command in commands:
            with self.subTest(command=command):
                result = self.run_shell('COMPOSE="docker compose"\n' + command + "\nprintf 'AFTER_CHECK\\n'\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("AFTER_CHECK", result.stdout)

    def test_invalid_compose_fallback_fails_instead_of_selecting_file(self):
        selector = self.script.split("if docker compose version", 1)[1].split("\n            fi", 1)[0]
        result = self.run_shell(
            "if docker compose version" + selector + "\nfi\nprintf 'SELECTED\\n'\n",
            docker="exit 1\n", compose="printf '<!DOCTYPE html>\\n'\nexit 2\n",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("SELECTED", result.stdout)

    def test_deployment_bash_syntax(self):
        result = subprocess.run(["bash", "-n"], input=self.script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
