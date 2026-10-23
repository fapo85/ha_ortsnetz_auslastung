"""Check release gates and exercise publishing logic without network writes."""

import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name):
    # BaseLoader preserves the GitHub Actions key `on` instead of treating it as True.
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


def test_release_requires_all_checks_for_the_same_commit():
    workflow = _workflow("release.yml")
    assert workflow["permissions"] == {"contents": "read"}
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    release = workflow["jobs"]["release"]
    assert release["needs"] == ["tests", "hassfest", "hacs"]
    assert release["if"] == "github.ref == 'refs/heads/main'"
    assert release["permissions"] == {"contents": "write"}
    assert release["steps"][0]["with"]["persist-credentials"] == "false"
    for job, name in (("tests", "tests.yaml"), ("hassfest", "hassfest.yaml"), ("hacs", "validate.yaml")):
        assert workflow["jobs"][job]["uses"] == f"./.github/workflows/{name}"
        assert "workflow_call" in _workflow(name)["on"]
    assert "always()" not in release["if"]


@pytest.fixture
def publish(tmp_path):
    """Replace external commands so no test can create a real tag or release."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    commands = {
        "jq": '#!/bin/bash\nprintf "%s\\n" "$TEST_VERSION"\n',
        "git": '''#!/bin/bash
if [[ "$1" == "show-ref" ]]; then
  [[ "$TEST_TAG_EXISTS" == "true" ]]
elif [[ "$1" == "rev-parse" ]]; then
  printf '%s\\n' "$TEST_TAG_SHA"
else
  exit 90
fi
''',
        "gh": '''#!/bin/bash
if [[ "$1 $2" == "release view" ]]; then
  [[ "$TEST_RELEASE_EXISTS" == "true" ]]
elif [[ "$1 $2" == "release create" ]]; then
  printf '%s\\n' "$@" > "$TEST_CALLS"
  exit "$TEST_CREATE_EXIT"
else
  exit 90
fi
''',
    }
    for name, source in commands.items():
        path = bin_dir / name
        path.write_text(source)
        path.chmod(0o755)
    calls = tmp_path / "calls"
    script = _workflow("release.yml")["jobs"]["release"]["steps"][-1]["run"]

    def run(**overrides):
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
               "GITHUB_SHA": "tested-commit", "TEST_VERSION": "1.0.2",
               "TEST_RELEASE_EXISTS": "false", "TEST_TAG_EXISTS": "false",
               "TEST_TAG_SHA": "tested-commit", "TEST_CALLS": str(calls),
               "TEST_CREATE_EXIT": "0", **overrides}
        result = subprocess.run(["bash", "-c", script], env=env, cwd=ROOT,
                                capture_output=True, text=True)
        return result, calls.read_text().splitlines() if calls.exists() else []

    return run


def test_release_targets_tested_commit(publish):
    result, args = publish()
    assert result.returncode == 0, result.stderr
    assert args == ["release", "create", "v1.0.2", "--target", "tested-commit",
                    "--generate-notes", "--title", "v1.0.2"]


def test_existing_release_is_left_unchanged(publish):
    result, args = publish(TEST_RELEASE_EXISTS="true")
    assert result.returncode == 0
    assert not args


def test_existing_tag_can_recover_missing_release(publish):
    result, args = publish(TEST_TAG_EXISTS="true")
    assert result.returncode == 0
    assert args[:3] == ["release", "create", "v1.0.2"]


def test_wrong_tag_target_is_rejected(publish):
    result, args = publish(TEST_TAG_EXISTS="true", TEST_TAG_SHA="old-commit")
    assert result.returncode != 0
    assert not args


@pytest.mark.parametrize("version", ["", "null", "1.0.2b1", "1.0.2\nmalformed", "1.0.2;echo unsafe"])
def test_invalid_stable_version_is_rejected(publish, version):
    result, args = publish(TEST_VERSION=version)
    assert result.returncode != 0
    assert not args


def test_publishing_failure_is_not_hidden(publish):
    result, _ = publish(TEST_CREATE_EXIT="1")
    assert result.returncode != 0
