"""
Unit tests for the ArtifactBucketGetObjectForManagedStacks S3 artifacts bucket
fallback in the management-role modules.

Validates that both pipeline-mgmt-role.yml and storage-mgmt-role.yml resolve the
ArtifactBucketGetObjectForManagedStacks Resource via an Fn::If on the
HasS3ArtifactsBucketOverride condition:
- true branch  -> arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-* (backward compatible)
- false branch -> imported bucket name from the account-wide export
                  ${OrgPrefix}-S3-Artifacts-Bucket-Name via Fn::ImportValue

Also verifies the statement keeps least-privilege actions, uses long-form
intrinsics only (no !-tag shorthand), an unrelated statement is unchanged, and
each module's header contract comment documents OrgPrefix and
HasS3ArtifactsBucketOverride.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7,
           5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 10.3
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


# --- Paths ---

MODULES_DIR = (
    Path(__file__).parent.parent
    / "templates"
    / "v2"
    / "modules"
    / "management-roles"
)
PIPELINE_MODULE_PATH = MODULES_DIR / "pipeline-mgmt-role.yml"
STORAGE_MODULE_PATH = MODULES_DIR / "storage-mgmt-role.yml"


# --- Fixtures ---


@pytest.fixture
def pipeline_template():
    """Load the pipeline management role module template."""
    return load_template(PIPELINE_MODULE_PATH)


@pytest.fixture
def storage_template():
    """Load the storage management role module template."""
    return load_template(STORAGE_MODULE_PATH)


@pytest.fixture
def pipeline_statements(pipeline_template):
    """Extract policy statements from the pipeline template."""
    return pipeline_template["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]


@pytest.fixture
def storage_statements(storage_template):
    """Extract policy statements from the storage template."""
    return storage_template["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]


def find_statement_by_sid(statements, sid):
    """Find a statement by its Sid field."""
    for stmt in statements:
        if stmt.get("Sid") == sid:
            return stmt
    return None


def has_shorthand_tag_keys(obj):
    """
    Recursively determine whether any mapping key in a parsed structure starts
    with '!'. The CFNLoader in cfn_test_utils registers shorthand tags (!Sub,
    !Ref, ...) as keys of the form {'!Sub': ...}; long-form intrinsics
    (Fn::Sub, Fn::If, Fn::ImportValue) parse as plain keys. So the presence of
    any key beginning with '!' indicates shorthand was used.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.startswith("!"):
                return True
            if has_shorthand_tag_keys(value):
                return True
        return False
    if isinstance(obj, list):
        return any(has_shorthand_tag_keys(item) for item in obj)
    return False


# --- Expected values ---

EXPECTED_ACTIONS = ["s3:GetObject", "s3:GetObjectVersion"]
EXPECTED_TRUE_BRANCH = {"Fn::Sub": "arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*"}
CONDITION_NAME = "HasS3ArtifactsBucketOverride"
EXPORT_NAME_SUB = "${OrgPrefix}-S3-Artifacts-Bucket-Name"
FALSE_BRANCH_TEMPLATE_FRAGMENT = "${ArtifactsBucketName}/${Prefix}-*"

# (fixture_name, module_path, human-readable label)
MODULE_CASES = [
    ("pipeline_statements", PIPELINE_MODULE_PATH, "pipeline"),
    ("storage_statements", STORAGE_MODULE_PATH, "storage"),
]


# --- Statement Effect and actions (Req 4.1 / 5.1) ---


class TestArtifactStatementEffectAndActions:
    """ArtifactBucketGetObjectForManagedStacks keeps Effect Allow and exact actions."""

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_statement_exists(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        assert stmt is not None, (
            f"ArtifactBucketGetObjectForManagedStacks not found in {_label} module"
        )

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_effect_is_allow(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        assert stmt["Effect"] == "Allow"

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_actions_exactly_get_object(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert actions == EXPECTED_ACTIONS, (
            f"Expected actions {EXPECTED_ACTIONS}, got {actions}"
        )


# --- Resource is Fn::If on HasS3ArtifactsBucketOverride (Req 4.2 / 5.2) ---


class TestArtifactStatementResourceIsFnIf:
    """The Resource is an Fn::If keyed on HasS3ArtifactsBucketOverride."""

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_resource_is_fn_if(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        resource = stmt["Resource"]
        assert isinstance(resource, dict) and "Fn::If" in resource, (
            f"Resource must be an Fn::If mapping, got: {resource}"
        )

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_fn_if_condition_is_first_element(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        fn_if = stmt["Resource"]["Fn::If"]
        assert isinstance(fn_if, list) and len(fn_if) == 3, (
            f"Fn::If must be a 3-element list, got: {fn_if}"
        )
        assert fn_if[0] == CONDITION_NAME, (
            f"Fn::If element 0 must be '{CONDITION_NAME}', got '{fn_if[0]}'"
        )


# --- True branch: override path (Req 4.3 / 5.3) ---


class TestArtifactStatementTrueBranch:
    """True branch (element 1) preserves the backward-compatible override ARN."""

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_true_branch_uses_s3_artifacts_bucket(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        true_branch = stmt["Resource"]["Fn::If"][1]
        assert true_branch == EXPECTED_TRUE_BRANCH, (
            f"True branch must be {EXPECTED_TRUE_BRANCH}, got {true_branch}"
        )


# --- False branch: import path (Req 4.4 / 5.4) ---


class TestArtifactStatementFalseBranch:
    """False branch (element 2) imports the account-wide artifacts bucket export."""

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_false_branch_is_fn_sub_list_form(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        false_branch = stmt["Resource"]["Fn::If"][2]
        assert isinstance(false_branch, dict) and "Fn::Sub" in false_branch, (
            f"False branch must be an Fn::Sub mapping, got: {false_branch}"
        )
        fn_sub = false_branch["Fn::Sub"]
        assert isinstance(fn_sub, list) and len(fn_sub) == 2, (
            f"False branch Fn::Sub must use the list form [template, vars], got: {fn_sub}"
        )

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_false_branch_template_string(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        template_string = stmt["Resource"]["Fn::If"][2]["Fn::Sub"][0]
        assert FALSE_BRANCH_TEMPLATE_FRAGMENT in template_string, (
            f"False branch template must contain '{FALSE_BRANCH_TEMPLATE_FRAGMENT}', "
            f"got '{template_string}'"
        )

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_false_branch_imports_export_via_org_prefix(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        var_map = stmt["Resource"]["Fn::If"][2]["Fn::Sub"][1]
        assert "ArtifactsBucketName" in var_map, (
            f"False branch var map must define ArtifactsBucketName, got: {var_map}"
        )
        import_value = var_map["ArtifactsBucketName"]
        assert isinstance(import_value, dict) and "Fn::ImportValue" in import_value, (
            f"ArtifactsBucketName must resolve via Fn::ImportValue, got: {import_value}"
        )
        inner_sub = import_value["Fn::ImportValue"]
        assert isinstance(inner_sub, dict) and "Fn::Sub" in inner_sub, (
            f"Fn::ImportValue must wrap an Fn::Sub, got: {inner_sub}"
        )
        assert inner_sub["Fn::Sub"] == EXPORT_NAME_SUB, (
            f"Import name must be '{EXPORT_NAME_SUB}', got '{inner_sub['Fn::Sub']}'"
        )


# --- Long-form intrinsics only (Req 4.5 / 5.5) ---


class TestArtifactStatementLongFormOnly:
    """No shorthand !-tag keys appear anywhere in the artifacts statement."""

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_no_shorthand_tag_keys(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "ArtifactBucketGetObjectForManagedStacks")
        assert not has_shorthand_tag_keys(stmt), (
            f"ArtifactBucketGetObjectForManagedStacks in {_label} module must use "
            f"long-form intrinsics only (found a '!'-prefixed key)"
        )


# --- Unrelated statement unchanged (Req 4.7 / 5.7) ---


class TestUnrelatedStatementUnchanged:
    """S3ModuleBucketGetObject remains a plain Allow GetObject statement."""

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_s3_module_bucket_get_object_unchanged(self, fixture_name, _path, _label, request):
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "S3ModuleBucketGetObject")
        assert stmt is not None, (
            f"S3ModuleBucketGetObject not found in {_label} module"
        )
        assert stmt["Effect"] == "Allow"
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert actions == EXPECTED_ACTIONS, (
            f"S3ModuleBucketGetObject actions must remain {EXPECTED_ACTIONS}, got {actions}"
        )

    @pytest.mark.parametrize("fixture_name,_path,_label", MODULE_CASES)
    def test_s3_module_bucket_get_object_resource_is_not_fn_if(self, fixture_name, _path, _label, request):
        """The unrelated statement must not have picked up the Fn::If fallback."""
        statements = request.getfixturevalue(fixture_name)
        stmt = find_statement_by_sid(statements, "S3ModuleBucketGetObject")
        resource = stmt["Resource"]
        assert isinstance(resource, list), (
            f"S3ModuleBucketGetObject Resource should remain a list, got: {resource}"
        )
        assert resource == [
            {"Fn::Sub": "arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*"}
        ], f"S3ModuleBucketGetObject Resource changed unexpectedly: {resource}"


# --- Header contract comment updates (Req 4.6 / 5.6) ---


class TestModuleHeaderContract:
    """Each module header documents OrgPrefix and HasS3ArtifactsBucketOverride."""

    @pytest.mark.parametrize("_fixture_name,module_path,_label", MODULE_CASES)
    def test_header_contains_org_prefix(self, _fixture_name, module_path, _label):
        text = module_path.read_text(encoding="utf-8")
        assert "OrgPrefix" in text, (
            f"{_label} module header/text must mention OrgPrefix"
        )

    @pytest.mark.parametrize("_fixture_name,module_path,_label", MODULE_CASES)
    def test_header_contains_override_condition(self, _fixture_name, module_path, _label):
        text = module_path.read_text(encoding="utf-8")
        assert "HasS3ArtifactsBucketOverride" in text, (
            f"{_label} module header/text must mention HasS3ArtifactsBucketOverride"
        )
