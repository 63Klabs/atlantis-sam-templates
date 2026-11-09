"""
Unit tests for the Secrets Manager statements in the pipeline
cloudformation-svc-role.yml module, the inline policy size guard, and the
version headers of the pipeline templates that were bumped for this change.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 10.4 (design D8)
"""

import json
import re
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template

REPO_ROOT = Path(__file__).parent.parent
PIPELINE_DIR = REPO_ROOT / "templates" / "v2" / "pipeline"
MODULE_PATH = (
    REPO_ROOT / "templates" / "v2" / "modules" / "pipeline" / "cloudformation-svc-role.yml"
)

CRUD_SID = "SecretsManagerCRUDThisDeploymentOnly"
RANDOM_PASSWORD_SID = "SecretsManagerGetRandomPassword"

EXPECTED_CRUD_ACTIONS = [
    "secretsmanager:CreateSecret",
    "secretsmanager:UpdateSecret",
    "secretsmanager:DeleteSecret",
    "secretsmanager:PutSecretValue",
    "secretsmanager:DescribeSecret",
    "secretsmanager:TagResource",
    "secretsmanager:UntagResource",
]

EXPECTED_CRUD_RESOURCE = (
    "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:"
    "${Prefix}-${ProjectId}-${StageId}-*"
)

INLINE_POLICY_LIMIT = 10240

# Worst-case rendered lengths (design D8)
VARIABLE_LENGTHS = {
    "Prefix": 8,
    "ProjectId": 26,
    "StageId": 8,
    "AWS::Region": 14,
    "AWS::AccountId": 12,
}
DEFAULT_VARIABLE_LENGTH = 20


# --- Helpers ---


def as_list(value):
    return [value] if isinstance(value, str) else list(value)


def find_statement_by_sid(statements, sid):
    for stmt in statements:
        if stmt.get("Sid") == sid:
            return stmt
    return None


def render_sub(sub_value):
    """Render an Fn::Sub value (string or [string, vars]) using worst-case lengths."""
    template_string = sub_value if isinstance(sub_value, str) else sub_value[0]
    return re.sub(
        r"\$\{([^}]+)\}",
        lambda m: "x" * VARIABLE_LENGTHS.get(m.group(1), DEFAULT_VARIABLE_LENGTH),
        template_string,
    )


def render(node):
    """Recursively replace every Fn::Sub with its worst-case rendered string."""
    if isinstance(node, dict):
        if set(node.keys()) == {"Fn::Sub"}:
            return render_sub(node["Fn::Sub"])
        return {k: render(v) for k, v in node.items()}
    if isinstance(node, list):
        return [render(item) for item in node]
    return node


# --- Fixtures ---


@pytest.fixture(scope="module")
def module_template():
    return load_template(MODULE_PATH)


@pytest.fixture(scope="module")
def policy_document(module_template):
    policies = module_template["Properties"]["Policies"]
    policy = next(p for p in policies if p["PolicyName"] == "CloudFormationRolePolicy")
    return policy["PolicyDocument"]


@pytest.fixture(scope="module")
def statements(policy_document):
    return policy_document["Statement"]


# --- R5.1 / R5.2: CRUD statement ---


class TestSecretsManagerCrudStatement:
    def test_statement_exists(self, statements):
        assert find_statement_by_sid(statements, CRUD_SID) is not None

    def test_effect_is_allow(self, statements):
        assert find_statement_by_sid(statements, CRUD_SID)["Effect"] == "Allow"

    def test_exact_seven_actions(self, statements):
        actions = as_list(find_statement_by_sid(statements, CRUD_SID)["Action"])
        assert len(actions) == 7
        assert sorted(actions) == sorted(EXPECTED_CRUD_ACTIONS)

    def test_resource_is_prefix_scoped_secret_arn_via_sub(self, statements):
        resource = find_statement_by_sid(statements, CRUD_SID)["Resource"]
        assert isinstance(resource, dict)
        assert resource == {"Fn::Sub": EXPECTED_CRUD_RESOURCE}

    def test_no_condition(self, statements):
        assert "Condition" not in find_statement_by_sid(statements, CRUD_SID)


# --- R5.3: GetRandomPassword statement ---


class TestSecretsManagerGetRandomPasswordStatement:
    def test_statement_exists(self, statements):
        assert find_statement_by_sid(statements, RANDOM_PASSWORD_SID) is not None

    def test_effect_is_allow(self, statements):
        assert find_statement_by_sid(statements, RANDOM_PASSWORD_SID)["Effect"] == "Allow"

    def test_only_get_random_password_action(self, statements):
        actions = as_list(find_statement_by_sid(statements, RANDOM_PASSWORD_SID)["Action"])
        assert actions == ["secretsmanager:GetRandomPassword"]

    def test_resource_is_wildcard(self, statements):
        assert find_statement_by_sid(statements, RANDOM_PASSWORD_SID)["Resource"] == "*"


# --- R5.4: no secret read access ---


class TestNoSecretValueRead:
    def test_no_statement_allows_get_secret_value(self, statements):
        offenders = []
        for stmt in statements:
            if stmt.get("Effect") != "Allow":
                continue
            for action in as_list(stmt.get("Action", [])):
                if action in ("secretsmanager:GetSecretValue", "secretsmanager:*", "*"):
                    offenders.append((stmt.get("Sid"), action))
        assert offenders == []


# --- R5.5 / D8: inline policy size guard ---


class TestInlinePolicySize:
    def test_rendered_policy_under_inline_limit(self, policy_document):
        rendered = render(policy_document)
        compact = json.dumps(rendered, separators=(",", ":"))
        compact = re.sub(r"\s+", "", compact)
        size = len(compact)
        assert size < INLINE_POLICY_LIMIT, (
            f"CloudFormationRolePolicy renders to {size} characters with worst-case "
            f"values; the IAM inline policy limit is {INLINE_POLICY_LIMIT}"
        )

    def test_render_replaces_all_sub_values(self, policy_document):
        compact = json.dumps(render(policy_document))
        assert "Fn::Sub" not in compact
        assert "${" not in compact


# --- R10.4: version headers ---


@pytest.mark.parametrize(
    "filename, expected_version",
    [
        ("template-pipeline.yml", "v2.0.24"),
        ("template-pipeline-github.yml", "v2.0.6"),
        ("template-pipeline-s3-source.yml", "v2.0.1"),
        ("template-pipeline-build-only.yml", "v2.0.7"),
    ],
)
def test_template_version_header(filename, expected_version):
    content = (PIPELINE_DIR / filename).read_text(encoding="utf-8")
    assert f"# Version: {expected_version}/" in content
