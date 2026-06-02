"""
Unit tests for S3 artifacts bucket policy module.

Bug condition exploration tests encode the EXPECTED (correct) behavior.
On UNFIXED code, they MUST FAIL — confirming the bug exists:
  - WhitelistedGet/WhitelistedPut use named Principal.AWS ARNs (should use Principal: "*")
  - No Condition.ArnLike block exists (should have aws:PrincipalArn condition)
  - Wildcard patterns use role-type-prefix convention (should use suffix convention)

Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4
"""

import fnmatch
import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


@pytest.fixture
def template():
    """Load the S3 artifacts bucket policy template for testing."""
    template_path = (
        Path(__file__).parent.parent
        / "templates"
        / "v2"
        / "modules"
        / "account-wide"
        / "s3-artifacts-bucket-policy.yml"
    )
    return load_template(template_path)


@pytest.fixture
def statements(template):
    """Extract the policy statements from the template."""
    return template["Properties"]["PolicyDocument"]["Statement"]


@pytest.fixture
def whitelisted_get(statements):
    """Extract the WhitelistedGet statement."""
    for stmt in statements:
        if stmt.get("Sid") == "WhitelistedGet":
            return stmt
    pytest.fail("WhitelistedGet statement not found")


@pytest.fixture
def whitelisted_put(statements):
    """Extract the WhitelistedPut statement."""
    for stmt in statements:
        if stmt.get("Sid") == "WhitelistedPut":
            return stmt
    pytest.fail("WhitelistedPut statement not found")


# =============================================================================
# Bug Condition Exploration Tests - Principal Structure
# These tests MUST FAIL on unfixed code to confirm the bug exists.
# DO NOT fix the template or modify these tests to make them pass.
# =============================================================================


class TestBugConditionPrincipalStructure:
    """Bug condition: WhitelistedGet/WhitelistedPut must use Principal: "*" with Condition.

    The current (buggy) code uses Principal.AWS with named ARNs, which causes
    "Invalid principal in policy" errors because S3 validates that named principals
    exist at policy creation time.

    Validates: Requirements 2.1
    """

    def test_whitelisted_get_uses_wildcard_principal(self, whitelisted_get):
        """WhitelistedGet should use Principal: '*' (not Principal.AWS named ARNs)."""
        principal = whitelisted_get.get("Principal")

        assert principal == "*", (
            f"COUNTEREXAMPLE: WhitelistedGet uses Principal: {principal}. "
            "Expected Principal: '*' (wildcard) for condition-based access control, "
            "but found named Principal.AWS ARNs which require roles to exist at policy creation time."
        )

    def test_whitelisted_put_uses_wildcard_principal(self, whitelisted_put):
        """WhitelistedPut should use Principal: '*' (not Principal.AWS named ARNs)."""
        principal = whitelisted_put.get("Principal")

        assert principal == "*", (
            f"COUNTEREXAMPLE: WhitelistedPut uses Principal: {principal}. "
            "Expected Principal: '*' (wildcard) for condition-based access control, "
            "but found named Principal.AWS ARNs which require roles to exist at policy creation time."
        )

    def test_whitelisted_get_has_arnlike_condition(self, whitelisted_get):
        """WhitelistedGet should have Condition.ArnLike['aws:PrincipalArn']."""
        condition = whitelisted_get.get("Condition", {})
        arn_like = condition.get("ArnLike", {})
        principal_arn = arn_like.get("aws:PrincipalArn")

        assert principal_arn is not None, (
            f"COUNTEREXAMPLE: WhitelistedGet has Condition: {condition}. "
            "Expected Condition.ArnLike['aws:PrincipalArn'] with role patterns, "
            "but no ArnLike condition found. The policy uses named principals instead."
        )

    def test_whitelisted_put_has_arnlike_condition(self, whitelisted_put):
        """WhitelistedPut should have Condition.ArnLike['aws:PrincipalArn']."""
        condition = whitelisted_put.get("Condition", {})
        arn_like = condition.get("ArnLike", {})
        principal_arn = arn_like.get("aws:PrincipalArn")

        assert principal_arn is not None, (
            f"COUNTEREXAMPLE: WhitelistedPut has Condition: {condition}. "
            "Expected Condition.ArnLike['aws:PrincipalArn'] with role patterns, "
            "but no ArnLike condition found. The policy uses named principals instead."
        )


# =============================================================================
# Bug Condition Exploration Tests - Wildcard Patterns
# These tests MUST FAIL on unfixed code to confirm the bug exists.
# DO NOT fix the template or modify these tests to make them pass.
# =============================================================================


class TestBugConditionWildcardPatterns:
    """Bug condition: ArnLike patterns must use suffix convention (*-RoleType).

    The current (buggy) code uses role-type-prefix patterns (e.g., CodePipelineServiceRole-*)
    which don't match actual role names where the role type is a suffix
    (e.g., acme-Worker-myapp-test-CodePipelineServiceRole).

    Validates: Requirements 2.2, 2.3, 2.4
    """

    def _get_arnlike_patterns(self, statement):
        """Extract ArnLike patterns from a statement's Condition block."""
        condition = statement.get("Condition", {})
        arn_like = condition.get("ArnLike", {})
        patterns = arn_like.get("aws:PrincipalArn", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        # Handle Fn::Sub patterns - extract the string value
        resolved = []
        for p in patterns:
            if isinstance(p, dict) and "!Sub" in p:
                resolved.append(p["!Sub"])
            elif isinstance(p, dict) and "Fn::Sub" in p:
                resolved.append(p["Fn::Sub"])
            elif isinstance(p, str):
                resolved.append(p)
        return resolved

    def test_arnlike_patterns_end_with_code_pipeline_service_role(self, whitelisted_get):
        """ArnLike patterns should end with '-CodePipelineServiceRole' (suffix convention)."""
        patterns = self._get_arnlike_patterns(whitelisted_get)

        matching = [p for p in patterns if p.endswith("-CodePipelineServiceRole")]

        assert len(matching) > 0, (
            f"COUNTEREXAMPLE: ArnLike patterns are {patterns}. "
            "Expected at least one pattern ending with '-CodePipelineServiceRole' (suffix convention), "
            "but current patterns use 'CodePipelineServiceRole-*' (prefix convention) which is reversed."
        )

    def test_arnlike_patterns_end_with_code_build_service_role(self, whitelisted_get):
        """ArnLike patterns should end with '-CodeBuildServiceRole' (suffix convention)."""
        patterns = self._get_arnlike_patterns(whitelisted_get)

        matching = [p for p in patterns if p.endswith("-CodeBuildServiceRole")]

        assert len(matching) > 0, (
            f"COUNTEREXAMPLE: ArnLike patterns are {patterns}. "
            "Expected at least one pattern ending with '-CodeBuildServiceRole' (suffix convention), "
            "but current patterns use 'CodeBuildServiceRole-*' (prefix convention) which is reversed."
        )

    def test_arnlike_patterns_end_with_cloud_formation_svc_role(self, whitelisted_get):
        """ArnLike patterns should end with '-CloudFormationSvcRole' (suffix convention)."""
        patterns = self._get_arnlike_patterns(whitelisted_get)

        matching = [p for p in patterns if p.endswith("-CloudFormationSvcRole")]

        assert len(matching) > 0, (
            f"COUNTEREXAMPLE: ArnLike patterns are {patterns}. "
            "Expected at least one pattern ending with '-CloudFormationSvcRole' (suffix convention), "
            "but current patterns use 'CloudFormationSvcRole-*' (prefix convention) which is reversed."
        )

    def test_fnmatch_suffix_pattern_matches_real_role_name(self, whitelisted_get):
        """Pattern '*-CodePipelineServiceRole' should match real role names.

        Real role names follow: {Prefix}-Worker-{ProjectId}-{StageId}-CodePipelineServiceRole
        The correct pattern uses wildcard BEFORE the role type suffix.
        """
        real_role_name = "acme-Worker-myapp-test-CodePipelineServiceRole"
        correct_pattern = "*-CodePipelineServiceRole"

        # This assertion encodes expected behavior - it will pass after fix
        # On unfixed code, the patterns use prefix convention (CodePipelineServiceRole-*)
        # which does NOT match real role names
        patterns = self._get_arnlike_patterns(whitelisted_get)

        # Find a pattern that would match the real role name using fnmatch
        # Resolve ${RolePath} to "/" (default IAM path) before matching
        matches_found = any(
            fnmatch.fnmatch(
                real_role_name,
                p.split(":role")[-1].replace("${RolePath}", "/").lstrip("/"),
            )
            for p in patterns
            if ":role" in p
        )

        assert matches_found, (
            f"COUNTEREXAMPLE: No ArnLike pattern matches real role name '{real_role_name}'. "
            f"Current patterns: {patterns}. "
            f"The correct pattern '{correct_pattern}' would match, but current code uses "
            "'CodePipelineServiceRole-*' which has the wildcard on the wrong end."
        )


# =============================================================================
# Preservation Tests - Baseline Behavior That Must Not Change
# These tests MUST PASS on both unfixed and fixed code.
# They capture the correct behavior that the fix must preserve.
# =============================================================================


class TestPreservationDenyStatement:
    """Preservation: DenyNonSecureTransportAccess statement must remain unchanged.

    Validates: Requirements 3.1
    """

    @pytest.fixture
    def deny_statement(self, statements):
        """Extract the DenyNonSecureTransportAccess statement."""
        for stmt in statements:
            if stmt.get("Sid") == "DenyNonSecureTransportAccess":
                return stmt
        pytest.fail("DenyNonSecureTransportAccess statement not found")

    def test_deny_statement_sid_exists(self, deny_statement):
        """DenyNonSecureTransportAccess Sid must exist."""
        assert deny_statement["Sid"] == "DenyNonSecureTransportAccess"

    def test_deny_statement_effect_is_deny(self, deny_statement):
        """DenyNonSecureTransportAccess Effect must be 'Deny'."""
        assert deny_statement["Effect"] == "Deny"

    def test_deny_statement_principal_is_wildcard(self, deny_statement):
        """DenyNonSecureTransportAccess Principal must be '*'."""
        assert deny_statement["Principal"] == "*"

    def test_deny_statement_action_is_s3_wildcard(self, deny_statement):
        """DenyNonSecureTransportAccess Action must be 's3:*'."""
        assert deny_statement["Action"] == "s3:*"

    def test_deny_statement_condition_is_secure_transport_false(self, deny_statement):
        """DenyNonSecureTransportAccess Condition must be Bool: aws:SecureTransport = false."""
        condition = deny_statement.get("Condition")
        assert condition is not None, "Condition must exist"
        assert "Bool" in condition, "Condition must contain 'Bool'"
        assert condition["Bool"] == {"aws:SecureTransport": False}

    def test_deny_statement_resource_references_bucket_arn(self, deny_statement):
        """DenyNonSecureTransportAccess Resource must reference S3ArtifactsBucketRegional ARN and ARN/*."""
        resource = deny_statement["Resource"]
        assert isinstance(resource, list), "Resource must be a list"
        assert len(resource) == 2, "Resource must have exactly 2 entries (ARN and ARN/*)"

        # First resource: Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]
        assert resource[0] == {"Fn::GetAtt": ["S3ArtifactsBucketRegional", "Arn"]}

        # Second resource: Fn::Join with ARN/*
        join_resource = resource[1]
        assert "Fn::Join" in join_resource, "Second resource must use Fn::Join"
        join_parts = join_resource["Fn::Join"]
        assert join_parts[0] == "/", "Join delimiter must be '/'"
        assert join_parts[1][0] == {"Fn::GetAtt": ["S3ArtifactsBucketRegional", "Arn"]}
        assert join_parts[1][1] == "*", "Join must append '*'"


class TestPreservationActionsAndResources:
    """Preservation: WhitelistedGet/Put actions and resource scoping must remain unchanged.

    Validates: Requirements 3.2, 3.3, 3.4
    """

    def test_whitelisted_get_actions_are_exact(self, whitelisted_get):
        """WhitelistedGet actions must be exactly: s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning."""
        expected_actions = ["s3:GetObject", "s3:GetObjectVersion", "s3:GetBucketVersioning"]
        assert whitelisted_get["Action"] == expected_actions

    def test_whitelisted_put_actions_are_exact(self, whitelisted_put):
        """WhitelistedPut actions must be exactly: s3:PutObject."""
        expected_actions = ["s3:PutObject"]
        assert whitelisted_put["Action"] == expected_actions

    def test_whitelisted_get_resource_references_bucket_arn(self, whitelisted_get):
        """WhitelistedGet Resource must reference S3ArtifactsBucketRegional ARN and ARN/*."""
        resource = whitelisted_get["Resource"]
        assert isinstance(resource, list), "Resource must be a list"
        assert len(resource) == 2, "Resource must have exactly 2 entries"

        # First resource: Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]
        assert resource[0] == {"Fn::GetAtt": ["S3ArtifactsBucketRegional", "Arn"]}

        # Second resource: Fn::Join with ARN/*
        join_resource = resource[1]
        assert "Fn::Join" in join_resource
        join_parts = join_resource["Fn::Join"]
        assert join_parts[0] == "/"
        assert join_parts[1][0] == {"Fn::GetAtt": ["S3ArtifactsBucketRegional", "Arn"]}
        assert join_parts[1][1] == "*"

    def test_whitelisted_put_resource_references_bucket_arn(self, whitelisted_put):
        """WhitelistedPut Resource must reference S3ArtifactsBucketRegional ARN and ARN/*."""
        resource = whitelisted_put["Resource"]
        assert isinstance(resource, list), "Resource must be a list"
        assert len(resource) == 2, "Resource must have exactly 2 entries"

        # First resource: Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]
        assert resource[0] == {"Fn::GetAtt": ["S3ArtifactsBucketRegional", "Arn"]}

        # Second resource: Fn::Join with ARN/*
        join_resource = resource[1]
        assert "Fn::Join" in join_resource
        join_parts = join_resource["Fn::Join"]
        assert join_parts[0] == "/"
        assert join_parts[1][0] == {"Fn::GetAtt": ["S3ArtifactsBucketRegional", "Arn"]}
        assert join_parts[1][1] == "*"


class TestPreservationStructure:
    """Preservation: Overall policy structure must remain unchanged.

    Validates: Requirements 3.5
    """

    def test_resource_level_condition_is_enable_s3_artifacts_bucket(self, template):
        """Resource-level Condition must be 'EnableS3ArtifactsBucket'."""
        assert template.get("Condition") == "EnableS3ArtifactsBucket"

    def test_policy_document_version(self, template):
        """PolicyDocument Version must be '2012-10-17'."""
        policy_doc = template["Properties"]["PolicyDocument"]
        assert policy_doc["Version"] == "2012-10-17"

    def test_policy_document_id(self, template):
        """PolicyDocument Id must be 'SSEAndSSLPolicy'."""
        policy_doc = template["Properties"]["PolicyDocument"]
        assert policy_doc["Id"] == "SSEAndSSLPolicy"

    def test_exactly_three_statements(self, statements):
        """Policy must have exactly 3 statements: DenyNonSecureTransportAccess, WhitelistedGet, WhitelistedPut."""
        assert len(statements) == 3, f"Expected 3 statements, got {len(statements)}"
        sids = [stmt.get("Sid") for stmt in statements]
        assert "DenyNonSecureTransportAccess" in sids
        assert "WhitelistedGet" in sids
        assert "WhitelistedPut" in sids
