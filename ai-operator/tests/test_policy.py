import pytest
from pathlib import Path
from app.core.policy import PolicyEnforcer

@pytest.fixture
def policy_enforcer(tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return PolicyEnforcer(sandbox_root=str(sandbox))

def test_allowed_command(policy_enforcer):
    is_allowed, _ = policy_enforcer.check_all("git status", policy_enforcer.sandbox_root)
    assert is_allowed is True

def test_disallowed_command(policy_enforcer):
    is_allowed, reason = policy_enforcer.check_all("rm -rf /", policy_enforcer.sandbox_root)
    assert is_allowed is False
    assert "not in the allowed list" in reason

def test_path_in_sandbox(policy_enforcer):
    project_a = policy_enforcer.sandbox_root / "projectA"
    project_a.mkdir()
    is_allowed, _ = policy_enforcer.check_all("dir", project_a)
    assert is_allowed is True

def test_path_outside_sandbox(policy_enforcer):
    outside_path = policy_enforcer.sandbox_root.parent / "outside"
    outside_path.mkdir(exist_ok=True)
    is_allowed, reason = policy_enforcer.check_all("dir", outside_path)
    assert is_allowed is False
    assert "outside the security sandbox" in reason

def test_path_traversal_attack(policy_enforcer):
    malicious_path = Path(policy_enforcer.sandbox_root) / ".." / "some_other_dir"
    is_allowed, reason = policy_enforcer.check_all("dir", malicious_path)
    assert is_allowed is False
    assert "outside the security sandbox" in reason

def test_command_with_extra_spaces(policy_enforcer):
    is_allowed, _ = policy_enforcer.check_all("  git status  ", policy_enforcer.sandbox_root)
    assert is_allowed is True

def test_no_cwd_provided(policy_enforcer):
    is_allowed, reason = policy_enforcer.check_all("git status", None)
    assert is_allowed is False
    assert "must be provided" in reason


def test_allow_file_write_command_in_sandbox(policy_enforcer):
    is_allowed, reason = policy_enforcer.check_all(
        'echo hello > greeting.txt',
        policy_enforcer.sandbox_root,
    )
    assert is_allowed is True
    assert "allowed" in reason


def test_block_absolute_path_in_command(policy_enforcer):
    is_allowed, reason = policy_enforcer.check_all(
        r'echo hello > C:\Users\gbin8\Desktop\greeting.txt',
        policy_enforcer.sandbox_root,
    )
    assert is_allowed is False
    assert "disallowed path pattern" in reason


def test_block_parent_traversal_in_command(policy_enforcer):
    is_allowed, reason = policy_enforcer.check_all(
        r'echo hello > ..\outside.txt',
        policy_enforcer.sandbox_root,
    )
    assert is_allowed is False
    assert "disallowed path pattern" in reason
