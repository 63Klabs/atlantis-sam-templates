"""
Unit tests for the artifacts-bucket parameters, condition, metadata grouping,
and version bumps across the three consuming templates that assemble the two
management-role modules:

  - templates/v2/account/prefix-based-infrastructure.yml
  - templates/v2/service-role/template-service-role-pipeline.yml
  - templates/v2/service-role/template-service-role-storage.yml

These tests verify the additive, backward-compatible changes introduced by the
"simplify parameters for account-wide" spec:

  * The optional OrgPrefix parameter (empty default, UPPER-CASE pattern, no MinLength).
  * The now-optional/deprecated S3ArtifactsBucket parameter.
  * The HasS3ArtifactsBucketOverride condition.
  * Metadata grouping of the new/updated parameters.
  * The bumped header version line for each template.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1, 6.4, 6.8,
8.1, 8.2, 8.3
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


# --- Paths ---

TEMPLATES_ROOT = Path(__file__).parent.parent / "templates" / "v2"

PREFIX_BASED_PATH = TEMPLATES_ROOT / "account" / "prefix-based-infrastructure.yml"
SERVICE_ROLE_PIPELINE_PATH = (
    TEMPLATES_ROOT / "service-role" / "template-service-role-pipeline.yml"
)
SERVICE_ROLE_STORAGE_PATH = (
    TEMPLATES_ROOT / "service-role" / "template-service-role-storage.yml"
)

# Expected bumped header version (major.minor.patch) for each template.
EXPECTED_VERSIONS = {
    PREFIX_BASED_PATH: "v0.0.2",
    SERVICE_ROLE_PIPELINE_PATH: "v0.0.19",
    SERVICE_ROLE_STORAGE_PATH: "v0.0.4",
}

# Expected constant parameter values shared across all three templates.
EXPECTED_ORG_PREFIX_PATTERN = "^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$|^$"
EXPECTED_ORG_PREFIX_MAX_LENGTH = 20

EXPECTED_ARTIFACTS_PATTERN = "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"
EXPECTED_ARTIFACTS_MAX_LENGTH = 63

# The CFNLoader parses YAML shorthand tags into single-key dicts keyed by the
# raw tag (e.g. "!Not", "!Equals", "!Ref"). This is the expected parsed shape of
#   HasS3ArtifactsBucketOverride: !Not [!Equals [!Ref S3ArtifactsBucket, ""]]
EXPECTED_OVERRIDE_CONDITION = {
    "!Not": [{"!Equals": [{"!Ref": "S3ArtifactsBucket"}, ""]}]
}


# --- Fixtures ---


@pytest.fixture(scope="module")
def prefix_based_template():
    return load_template(PREFIX_BASED_PATH)


@pytest.fixture(scope="module")
def service_role_pipeline_template():
    return load_template(SERVICE_ROLE_PIPELINE_PATH)


@pytest.fixture(scope="module")
def service_role_storage_template():
    return load_template(SERVICE_ROLE_STORAGE_PATH)


# Parametrize helper: maps a friendly id to the fixture name so each test runs
# against all three consuming templates.
CONSUMING_TEMPLATE_FIXTURES = [
    ("prefix_based", "prefix_based_template"),
    ("service_role_pipeline", "service_role_pipeline_template"),
    ("service_role_storage", "service_role_storage_template"),
]


@pytest.fixture
def consuming_template(request):
    """Resolve a consuming-template fixture by name (used with parametrize)."""
    return request.getfixturevalue(request.param)


# --- Metadata helpers ---


def get_parameter_groups(template):
    return template["Metadata"]["AWS::CloudFormation::Interface"]["ParameterGroups"]


def find_group_by_label(template, label):
    for group in get_parameter_groups(template):
        if group.get("Label", {}).get("default") == label:
            return group
    return None


# --- OrgPrefix parameter (Requirements 1.1-1.5) ---


@pytest.mark.parametrize(
    "consuming_template",
    [fixture for _, fixture in CONSUMING_TEMPLATE_FIXTURES],
    ids=[name for name, _ in CONSUMING_TEMPLATE_FIXTURES],
    indirect=True,
)
class TestOrgPrefixParameter:
    """OrgPrefix must be an optional, UPPER-CASE parameter with no MinLength."""

    def test_org_prefix_exists(self, consuming_template):
        assert "OrgPrefix" in consuming_template["Parameters"]

    def test_org_prefix_type_is_string(self, consuming_template):
        assert consuming_template["Parameters"]["OrgPrefix"]["Type"] == "String"

    def test_org_prefix_default_is_empty(self, consuming_template):
        assert consuming_template["Parameters"]["OrgPrefix"]["Default"] == ""

    def test_org_prefix_allowed_pattern(self, consuming_template):
        assert (
            consuming_template["Parameters"]["OrgPrefix"]["AllowedPattern"]
            == EXPECTED_ORG_PREFIX_PATTERN
        )

    def test_org_prefix_max_length(self, consuming_template):
        assert (
            consuming_template["Parameters"]["OrgPrefix"]["MaxLength"]
            == EXPECTED_ORG_PREFIX_MAX_LENGTH
        )

    def test_org_prefix_has_no_min_length(self, consuming_template):
        assert "MinLength" not in consuming_template["Parameters"]["OrgPrefix"]


# --- S3ArtifactsBucket parameter (Requirements 2.1-2.3) ---


@pytest.mark.parametrize(
    "consuming_template",
    [fixture for _, fixture in CONSUMING_TEMPLATE_FIXTURES],
    ids=[name for name, _ in CONSUMING_TEMPLATE_FIXTURES],
    indirect=True,
)
class TestS3ArtifactsBucketParameter:
    """S3ArtifactsBucket must be optional, deprecated, with no MinLength."""

    def test_artifacts_exists(self, consuming_template):
        assert "S3ArtifactsBucket" in consuming_template["Parameters"]

    def test_artifacts_default_is_empty(self, consuming_template):
        assert consuming_template["Parameters"]["S3ArtifactsBucket"]["Default"] == ""

    def test_artifacts_allowed_pattern(self, consuming_template):
        assert (
            consuming_template["Parameters"]["S3ArtifactsBucket"]["AllowedPattern"]
            == EXPECTED_ARTIFACTS_PATTERN
        )

    def test_artifacts_max_length(self, consuming_template):
        assert (
            consuming_template["Parameters"]["S3ArtifactsBucket"]["MaxLength"]
            == EXPECTED_ARTIFACTS_MAX_LENGTH
        )

    def test_artifacts_has_no_min_length(self, consuming_template):
        assert "MinLength" not in consuming_template["Parameters"]["S3ArtifactsBucket"]

    def test_artifacts_description_marked_deprecated(self, consuming_template):
        description = consuming_template["Parameters"]["S3ArtifactsBucket"]["Description"]
        assert description.startswith("DEPRECATED:")


# --- HasS3ArtifactsBucketOverride condition (Requirement 3.1) ---


@pytest.mark.parametrize(
    "consuming_template",
    [fixture for _, fixture in CONSUMING_TEMPLATE_FIXTURES],
    ids=[name for name, _ in CONSUMING_TEMPLATE_FIXTURES],
    indirect=True,
)
class TestHasS3ArtifactsBucketOverrideCondition:
    """The condition must equal Not(Equals(Ref S3ArtifactsBucket, ""))."""

    def test_condition_exists(self, consuming_template):
        assert "HasS3ArtifactsBucketOverride" in consuming_template["Conditions"]

    def test_condition_structure(self, consuming_template):
        condition = consuming_template["Conditions"]["HasS3ArtifactsBucketOverride"]
        assert condition == EXPECTED_OVERRIDE_CONDITION


# --- Metadata grouping (Requirements 1.5, 6.4, 6.8) ---


@pytest.mark.parametrize(
    "consuming_template",
    [fixture for _, fixture in CONSUMING_TEMPLATE_FIXTURES],
    ids=[name for name, _ in CONSUMING_TEMPLATE_FIXTURES],
    indirect=True,
)
class TestMetadataGrouping:
    """OrgPrefix belongs in Application Resource Naming; S3ArtifactsBucket in External Resources."""

    def test_org_prefix_in_application_resource_naming_group(self, consuming_template):
        group = find_group_by_label(consuming_template, "Application Resource Naming")
        assert group is not None, "Application Resource Naming group missing"
        assert "OrgPrefix" in group["Parameters"]

    def test_artifacts_in_external_resources_group(self, consuming_template):
        group = find_group_by_label(consuming_template, "External Resources")
        assert group is not None, "External Resources group missing"
        assert "S3ArtifactsBucket" in group["Parameters"]

    def test_org_prefix_not_in_external_resources_group(self, consuming_template):
        group = find_group_by_label(consuming_template, "External Resources")
        assert group is not None
        assert "OrgPrefix" not in group["Parameters"]


# --- Header version bumps (Requirements 8.1, 8.2, 8.3) ---


class TestHeaderVersions:
    """Each template header '# Version:' line must reflect the bumped version."""

    @pytest.mark.parametrize(
        "template_path",
        list(EXPECTED_VERSIONS.keys()),
        ids=[p.name for p in EXPECTED_VERSIONS.keys()],
    )
    def test_header_version_line(self, template_path):
        expected_version = EXPECTED_VERSIONS[template_path]
        with open(template_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        # e.g. "# Version: v0.0.2/2026-08-10" -> assert the "v0.0.2/" fragment.
        assert (
            f"# Version: {expected_version}/" in raw_text
        ), f"Expected version line '# Version: {expected_version}/...' not found in {template_path.name}"
