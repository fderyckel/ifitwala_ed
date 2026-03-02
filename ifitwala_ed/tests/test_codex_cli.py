# ifitwala_ed/tests/test_codex_cli.py

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed import codex_cli


class TestCodexCli(TestCase):
    def test_backend_smoke_requires_site(self):
        rc = codex_cli.main(["backend-smoke", "--dry-run"])
        self.assertEqual(rc, 2)

    def test_ci_requires_site_when_backend_enabled(self):
        rc = codex_cli.main(["ci", "--dry-run", "--skip-lint", "--skip-frontend"])
        self.assertEqual(rc, 2)

    def test_ci_allows_no_site_when_backend_skipped(self):
        rc = codex_cli.main(["ci", "--dry-run", "--skip-backend"])
        self.assertEqual(rc, 0)

    @patch("ifitwala_ed.codex_cli.subprocess.run")
    def test_backend_smoke_executes_all_modules(self, run_mock):
        run_mock.return_value = SimpleNamespace(returncode=0)
        rc = codex_cli.main(
            [
                "backend-smoke",
                "--site",
                "test_site",
                "--module",
                "ifitwala_ed.api.test_users",
                "--module",
                "ifitwala_ed.api.test_guardian_home",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(run_mock.call_count, 2)

    def test_lint_with_all_checks_skipped_is_noop(self):
        rc = codex_cli.main(["lint", "--dry-run", "--skip-ruff", "--skip-contracts", "--skip-metrics"])
        self.assertEqual(rc, 0)
