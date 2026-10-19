"""Publication boundary regressions use authored temporary fixtures only."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publication_checker", ROOT / "tools" / "check_publication.py")
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)
DEPLOYED_POLICY = CHECKER.load_policy(ROOT / "publication-policy.json")
# Authored safety fixtures exercise generic rules independently of the deployed index inventory.
POLICY = dict(DEPLOYED_POLICY, approved_top_level_directories=["tools", "tests", "docs", ".github", "src", "examples", "configs"])


class PublicationPolicyTest(unittest.TestCase):
    def make_file(self, root: Path, relative: str, text: str = "# Authored fixture\n") -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def scan(self, root: Path):
        return CHECKER.scan_repository(root, POLICY)

    def test_deployed_index_policy_rejects_project_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_file(root, "projects/example/source.py")
            self.make_file(root, "src/example.py")
            self.make_file(root, "pyproject.toml")
            findings = CHECKER.scan_repository(root, DEPLOYED_POLICY).findings
            self.assertIn(CHECKER.Finding("projects", "DIRECTORY_NOT_ALLOWLISTED"), findings)
            self.assertIn(CHECKER.Finding("src", "DIRECTORY_NOT_ALLOWLISTED"), findings)
            self.assertIn(CHECKER.Finding("pyproject.toml", "PATH_NOT_ALLOWLISTED"), findings)

    def test_secret_report_contains_no_secret_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "repo"
            secret = "gh" + "p_" + "A" * 36
            self.make_file(root, "README.md", "credential = '" + secret + "'\n")
            self.make_file(root, "publication-policy.json", json.dumps(POLICY))
            output = io.StringIO()
            report = parent / "audit.json"
            with redirect_stdout(output):
                status = CHECKER.main(["--root", str(root), "--report", str(report)])
            serialized = report.read_text(encoding="utf-8")
            self.assertEqual(status, 1)
            self.assertNotIn(secret, output.getvalue())
            self.assertNotIn(secret, serialized)
            self.assertIn("GITHUB_TOKEN", serialized)
            self.assertIn('"line": 1', serialized)

    def test_private_data_and_manuscript_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_file(root, "data/observations.csv", "x,y\n1,2\n")
            self.make_file(root, "docs/manuscript.pdf", "authored binary placeholder")
            self.make_file(root, "src/observations.csv", "x,y\n1,2\n")
            rules = {finding.rule for finding in self.scan(root).findings}
            self.assertIn("FORBIDDEN_DIRECTORY", rules)
            self.assertIn("FORBIDDEN_FILE_TYPE", rules)
            self.assertIn("DATA_OUTSIDE_SYNTHETIC_SCOPE", rules)

    def test_small_synthetic_examples_and_fixtures_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_file(root, "examples/synthetic_jobs.csv", "category,text\nA,authored sample\n")
            self.make_file(root, "src/job_text_classification/examples/synthetic_jobs.jsonl", '{"label": "A", "text": "authored sample"}\n')
            self.make_file(root, "tests/fixtures/tiny.json", '{"sample": [1, 2]}\n')
            self.make_file(root, "configs/demo.json", '{"iterations": 2}\n')
            self.assertEqual(self.scan(root).findings, [])

    def test_symlink_is_rejected_without_following_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "repo"
            root.mkdir()
            target = self.make_file(parent, "outside.txt")
            link = root / "README.md"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("Host cannot create a temporary symlink")
            self.assertEqual(self.scan(root).findings, [CHECKER.Finding("README.md", "SYMLINK_OR_REPARSE_POINT")])

    def test_reparse_entry_rejected_on_hosts_without_symlink_privilege(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            linked = self.make_file(root, "README.md")
            original_check = CHECKER._is_link_or_reparse
            with mock.patch.object(CHECKER, "_is_link_or_reparse", side_effect=lambda path: path == linked or original_check(path)):
                self.assertEqual(self.scan(root).findings, [CHECKER.Finding("README.md", "SYMLINK_OR_REPARSE_POINT")])

    def test_nested_git_is_rejected_but_root_metadata_skipped(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_file(root, ".git/config", "metadata outside content scan")
            self.make_file(root, "docs/.git", "gitdir: ../elsewhere")
            self.assertEqual(self.scan(root).findings, [CHECKER.Finding("docs/.git", "NESTED_GIT")])

    def test_private_identifiers_detected_without_number_false_positives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            email = "person" + "@" + "example.invalid"
            private_address = "192" + ".168" + ".10" + ".20"
            local_path = "D:" + "\\" + "private" + "\\" + "research.py"
            telephone = "13" + "800" + "000" + "000"
            content = "\n".join([email, private_address, local_path, "mobile: " + telephone])
            self.make_file(root, "README.md", content)
            rules = {finding.rule for finding in self.scan(root).findings}
            self.assertEqual(rules, {"PERSONAL_EMAIL", "PRIVATE_NETWORK_ADDRESS", "PRIVATE_ABSOLUTE_PATH", "PERSONAL_PHONE"})
            self.make_file(root, "README.md", "https://github.com/example/project\nexpected = " + telephone + "\n")
            self.assertEqual(self.scan(root).findings, [])

    def test_report_cannot_be_written_inside_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_file(root, "README.md")
            self.make_file(root, "publication-policy.json", json.dumps(POLICY))
            with self.assertRaises(SystemExit) as error:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    CHECKER.main(["--root", str(root), "--report", str(root / "docs" / "audit.json")])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((root / "docs" / "audit.json").exists())


@unittest.skipUnless(shutil.which("git"), "Git is unavailable")
class StagedPublicationPolicyTest(unittest.TestCase):
    make_file = PublicationPolicyTest.make_file

    def git(self, root: Path, *arguments: str, payload: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", "-C", str(root), *arguments], input=payload,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30,
        ).stdout

    def initialize(self, root: Path) -> None:
        self.git(root, "init", "-q")
        self.make_file(root, "publication-policy.json", json.dumps(POLICY))
        self.make_file(root, "README.md")
        self.git(root, "add", "publication-policy.json", "README.md")

    def test_staged_secret_detected_after_working_tree_is_clean(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "repo"
            root.mkdir()
            self.initialize(root)
            secret = "gh" + "p_" + "B" * 36
            self.make_file(root, "README.md", "credential = '" + secret + "'\n")
            self.git(root, "add", "README.md")
            self.make_file(root, "README.md", "Clean working-tree content\n")
            report = parent / "staged-report.json"
            output = io.StringIO()
            with redirect_stdout(output):
                status = CHECKER.main(["--root", str(root), "--staged", "--json-report", str(report)])
            serialized = report.read_text(encoding="utf-8")
            self.assertEqual(status, 1)
            self.assertIn("GITHUB_TOKEN", serialized)
            self.assertIn('"scope": "git_index"', serialized)
            self.assertNotIn(secret, serialized + output.getvalue())
            self.assertEqual(CHECKER.scan_repository(root, POLICY).findings, [])

    def test_ignored_runtime_artifacts_do_not_enter_index_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.initialize(root)
            self.make_file(root, ".gitignore", ".venv/\n__pycache__/\n*.egg-info/\n")
            self.make_file(root, ".venv/ignored.py")
            self.make_file(root, "memlab/__pycache__/ignored.pyc")
            self.make_file(root, "memlab.egg-info/PKG-INFO")
            self.git(root, "add", "-A")
            self.assertEqual(CHECKER.scan_staged(root).findings, [])
            self.assertTrue(CHECKER.scan_repository(root, POLICY).findings)

    def test_symlink_and_submodule_index_entries_rejected_without_materialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.initialize(root)
            identifier = self.git(root, "hash-object", "-w", "--stdin", payload=b"outside-target").decode().strip()
            self.git(root, "update-index", "--add", "--cacheinfo", f"120000,{identifier},README.md")
            self.git(root, "update-index", "--add", "--cacheinfo", f"160000,{identifier},external")
            findings = CHECKER.scan_staged(root).findings
            self.assertIn(CHECKER.Finding("README.md", "SYMLINK_INDEX_ENTRY"), findings)
            self.assertIn(CHECKER.Finding("external", "SUBMODULE_INDEX_ENTRY"), findings)

    def test_unmerged_index_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.initialize(root)
            identifier = self.git(root, "hash-object", "-w", "--stdin", payload=b"authored conflict fixture").decode().strip()
            self.git(root, "update-index", "--force-remove", "README.md")
            index_info = f"100644 {identifier} 1\tREADME.md\n100644 {identifier} 2\tREADME.md\n"
            self.git(root, "update-index", "--index-info", payload=index_info.encode())
            self.assertIn(CHECKER.Finding("README.md", "UNMERGED_INDEX"), CHECKER.scan_staged(root).findings)

    def test_large_blob_rejected_before_reading_its_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.initialize(root)
            self.make_file(root, "README.md", "x" * (POLICY["max_file_bytes"] + 1))
            self.git(root, "add", "README.md")
            with mock.patch.object(CHECKER, "_git", wraps=CHECKER._git) as reader:
                result = CHECKER.scan_staged(root, POLICY)
            self.assertIn(CHECKER.Finding("README.md", "FILE_TOO_LARGE"), result.findings)
            large_identifier = self.git(root, "rev-parse", ":README.md").decode().strip()
            self.assertFalse(any(call.args[1:] == ("cat-file", "blob", large_identifier) for call in reader.call_args_list))

    def test_unstaged_policy_change_does_not_weaken_index_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.initialize(root)
            self.make_file(root, "data/observations.csv", "x,y\n1,2\n")
            self.git(root, "add", "data/observations.csv")
            changed = dict(POLICY, forbidden_directory_names=[])
            self.make_file(root, "publication-policy.json", json.dumps(changed))
            self.assertIn(
                CHECKER.Finding("data", "FORBIDDEN_DIRECTORY"),
                CHECKER.scan_staged(root).findings,
            )

    def test_unsafe_index_path_validation(self):
        for name in ("../README.md", "/README.md", "D:" + "/private.py", "a\\b.py", "a/../b.py", "a/./b.py", "a//b.py", "CON.py", "a/name. "):
            with self.subTest(name=name):
                self.assertFalse(CHECKER._safe_index_path(name))
        self.assertTrue(CHECKER._safe_index_path("tools/check.py"))

    def test_case_collisions_cannot_hide_a_staged_blob(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.initialize(root)
            first = self.git(root, "hash-object", "-w", "--stdin", payload=b"# first authored blob\n").decode().strip()
            second = self.git(root, "hash-object", "-w", "--stdin", payload=b"# second authored blob\n").decode().strip()
            upper = "tools/A.py"
            lower = "tools/a.py"
            self.git(root, "-c", "core.ignorecase=false", "update-index", "--add", "--cacheinfo", f"100644,{first},{upper}")
            self.git(root, "-c", "core.ignorecase=false", "update-index", "--add", "--cacheinfo", f"100644,{second},{lower}")
            findings = CHECKER.scan_staged(root).findings
            self.assertIn(CHECKER.Finding(upper, "INDEX_PATH_COLLISION"), findings)
            self.assertIn(CHECKER.Finding(lower, "INDEX_PATH_COLLISION"), findings)


if __name__ == "__main__":
    unittest.main()
