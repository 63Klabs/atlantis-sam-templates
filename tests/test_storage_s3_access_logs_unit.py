"""
Unit tests for storage S3 access logs template.
Tests for CloudFront legacy logging ACL support (bug condition exploration).

These tests encode the EXPECTED behavior after the fix is applied.
On unfixed code, they will FAIL — confirming the bug exists.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


@pytest.fixture
def template():
    """Load the S3 access logs template for testing."""
    template_path = Path(__file__).parent.parent / "templates" / "v2" / "storage" / "template-storage-s3-access-logs.yml"
    return load_template(template_path)


# =============================================================================
# Bug Condition Exploration Tests
# These tests MUST FAIL on unfixed code to confirm the bug exists.
# =============================================================================

class TestAllowLegacyCloudFrontLogsParameter:
    """Bug condition: AllowLegacyCloudFrontLogs parameter must exist."""

    def test_parameter_exists(self, template):
        """Parameter AllowLegacyCloudFrontLogs should exist in the template."""
        params = template.get("Parameters", {})
        assert "AllowLegacyCloudFrontLogs" in params, (
            "COUNTEREXAMPLE: AllowLegacyCloudFrontLogs parameter is missing. "
            "There is no mechanism to opt in to CloudFront legacy logging."
        )

    def test_parameter_type_is_string(self, template):
        """Parameter should be of type String."""
        param = template.get("Parameters", {}).get("AllowLegacyCloudFrontLogs", {})
        assert param.get("Type") == "String"

    def test_parameter_default_is_false(self, template):
        """Parameter should default to 'false' so existing deployments are unaffected."""
        param = template.get("Parameters", {}).get("AllowLegacyCloudFrontLogs", {})
        assert param.get("Default") == "false"

    def test_parameter_allowed_values(self, template):
        """Parameter should only allow 'true' or 'false'."""
        param = template.get("Parameters", {}).get("AllowLegacyCloudFrontLogs", {})
        assert param.get("AllowedValues") == ["true", "false"]


class TestEnableLegacyCloudFrontLogsCondition:
    """Bug condition: EnableLegacyCloudFrontLogs condition must exist."""

    def test_condition_exists(self, template):
        """Condition EnableLegacyCloudFrontLogs should exist in the template."""
        conditions = template.get("Conditions", {})
        assert "EnableLegacyCloudFrontLogs" in conditions, (
            "COUNTEREXAMPLE: EnableLegacyCloudFrontLogs condition is missing. "
            "No conditional logic exists to toggle CloudFront legacy logging."
        )


class TestBlockPublicAclsConditional:
    """Bug condition: BlockPublicAcls must use conditional logic, not hardcoded true."""

    def test_block_public_acls_uses_if_condition(self, template):
        """BlockPublicAcls should use !If referencing EnableLegacyCloudFrontLogs."""
        bucket = template["Resources"]["Bucket"]["Properties"]
        block_public_acls = bucket["PublicAccessBlockConfiguration"]["BlockPublicAcls"]

        # On unfixed code, this is hardcoded to True — no conditional logic
        assert isinstance(block_public_acls, dict) or isinstance(block_public_acls, list), (
            f"COUNTEREXAMPLE: BlockPublicAcls is hardcoded to {block_public_acls}. "
            "It should use !If [EnableLegacyCloudFrontLogs, false, true] "
            "to allow ACL grants when CloudFront logging is enabled."
        )

    def test_block_public_acls_references_condition(self, template):
        """BlockPublicAcls !If should reference EnableLegacyCloudFrontLogs condition."""
        bucket = template["Resources"]["Bucket"]["Properties"]
        block_public_acls = bucket["PublicAccessBlockConfiguration"]["BlockPublicAcls"]

        # CFNLoader preserves !If tag as {"!If": [...]}
        if isinstance(block_public_acls, dict) and "!If" in block_public_acls:
            condition_ref = block_public_acls["!If"][0]
            assert condition_ref == "EnableLegacyCloudFrontLogs"
        else:
            pytest.fail(
                f"COUNTEREXAMPLE: BlockPublicAcls is {block_public_acls}, "
                "not a conditional !If expression."
            )


class TestOwnershipControls:
    """Bug condition: OwnershipControls with BucketOwnerPreferred must be present."""

    def test_ownership_controls_present(self, template):
        """Bucket should have OwnershipControls for CloudFront ACL-based delivery."""
        bucket_props = template["Resources"]["Bucket"]["Properties"]
        assert "OwnershipControls" in bucket_props, (
            "COUNTEREXAMPLE: OwnershipControls is not defined on the bucket. "
            "CloudFront standard logging requires ObjectOwnership: BucketOwnerPreferred."
        )


class TestCloudFrontLogDeliveryPolicyStatement:
    """Bug condition: Bucket policy must include CloudFront log delivery statement."""

    def _get_policy_statements(self, template):
        """Get all policy statements from the logging bucket policy."""
        return template["Resources"]["LoggingBucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]

    def _find_cloudfront_statement(self, statements):
        """Find the AllowCloudFrontLogDelivery statement."""
        for stmt in statements:
            # Check direct statement
            if isinstance(stmt, dict):
                if stmt.get("Sid") == "AllowCloudFrontLogDelivery":
                    return stmt
                # Check inside !If wrapper (CFNLoader preserves as "!If")
                if "!If" in stmt:
                    inner = stmt["!If"]
                    if len(inner) >= 2 and isinstance(inner[1], dict):
                        if inner[1].get("Sid") == "AllowCloudFrontLogDelivery":
                            return inner[1]
                # Check inside Fn::If wrapper (standard JSON format)
                if "Fn::If" in stmt:
                    inner = stmt["Fn::If"]
                    if len(inner) >= 2 and isinstance(inner[1], dict):
                        if inner[1].get("Sid") == "AllowCloudFrontLogDelivery":
                            return inner[1]
        return None

    def test_cloudfront_delivery_statement_exists(self, template):
        """Bucket policy should contain AllowCloudFrontLogDelivery statement."""
        statements = self._get_policy_statements(template)
        stmt = self._find_cloudfront_statement(statements)
        assert stmt is not None, (
            "COUNTEREXAMPLE: No policy statement with Sid 'AllowCloudFrontLogDelivery' found. "
            "The bucket policy does not allow delivery.logs.amazonaws.com to write logs."
        )

    def test_cloudfront_statement_principal(self, template):
        """CloudFront delivery statement should use delivery.logs.amazonaws.com principal."""
        statements = self._get_policy_statements(template)
        stmt = self._find_cloudfront_statement(statements)
        if stmt is None:
            pytest.fail("AllowCloudFrontLogDelivery statement not found")
        principal = stmt.get("Principal", {})
        assert principal.get("Service") == "delivery.logs.amazonaws.com"

    def test_cloudfront_statement_action(self, template):
        """CloudFront delivery statement should allow s3:PutObject."""
        statements = self._get_policy_statements(template)
        stmt = self._find_cloudfront_statement(statements)
        if stmt is None:
            pytest.fail("AllowCloudFrontLogDelivery statement not found")
        action = stmt.get("Action")
        assert action == "s3:PutObject" or action == ["s3:PutObject"]

    def test_cloudfront_statement_acl_condition(self, template):
        """CloudFront delivery statement should require bucket-owner-full-control ACL."""
        statements = self._get_policy_statements(template)
        stmt = self._find_cloudfront_statement(statements)
        if stmt is None:
            pytest.fail("AllowCloudFrontLogDelivery statement not found")
        condition = stmt.get("Condition", {})
        string_equals = condition.get("StringEquals", {})
        assert string_equals.get("s3:x-amz-acl") == "bucket-owner-full-control"


# =============================================================================
# Preservation Tests
# These tests MUST PASS on unfixed code to confirm baseline behavior.
# After the fix, they must STILL PASS to confirm no regressions.
# =============================================================================


class TestPreservationPublicAccessBlock:
    """Preservation: PublicAccessBlockConfiguration properties remain secure."""

    def test_block_public_acls_is_true(self, template):
        """BlockPublicAcls should be true on unfixed (default) template."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        # After fix, this may be a conditional (!If) that resolves to true when disabled.
        # Accept both hardcoded True and an !If whose third element (false-branch) is true.
        val = pac["BlockPublicAcls"]
        if isinstance(val, bool):
            assert val is True
        elif isinstance(val, dict) and "!If" in val:
            # !If [condition, true-branch, false-branch] — false-branch must be true
            assert val["!If"][2] is True
        else:
            pytest.fail(f"Unexpected BlockPublicAcls value: {val}")

    def test_block_public_policy_is_true(self, template):
        """BlockPublicPolicy must always be true."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        assert pac["BlockPublicPolicy"] is True

    def test_ignore_public_acls_is_true(self, template):
        """IgnorePublicAcls must always be true."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        assert pac["IgnorePublicAcls"] is True

    def test_restrict_public_buckets_is_true(self, template):
        """RestrictPublicBuckets must always be true."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        assert pac["RestrictPublicBuckets"] is True


class TestPreservationS3LogDeliveryPolicy:
    """Preservation: AllowS3LogDelivery policy statement unchanged."""

    def _get_statements(self, template):
        return template["Resources"]["LoggingBucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]

    def _find_statement(self, statements, sid):
        for stmt in statements:
            if isinstance(stmt, dict) and stmt.get("Sid") == sid:
                return stmt
        return None

    def test_allow_s3_log_delivery_exists(self, template):
        """AllowS3LogDelivery statement must exist."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "AllowS3LogDelivery")
        assert stmt is not None, "AllowS3LogDelivery policy statement is missing"

    def test_allow_s3_log_delivery_principal(self, template):
        """AllowS3LogDelivery must use logging.s3.amazonaws.com principal."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "AllowS3LogDelivery")
        assert stmt["Principal"]["Service"] == "logging.s3.amazonaws.com"

    def test_allow_s3_log_delivery_action(self, template):
        """AllowS3LogDelivery must allow s3:PutObject."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "AllowS3LogDelivery")
        action = stmt["Action"]
        if isinstance(action, list):
            assert "s3:PutObject" in action
        else:
            assert action == "s3:PutObject"

    def test_allow_s3_log_delivery_effect(self, template):
        """AllowS3LogDelivery must have Effect Allow."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "AllowS3LogDelivery")
        assert stmt["Effect"] == "Allow"


class TestPreservationDenyNonSecureTransport:
    """Preservation: DenyNonSecureTransportAccess policy statement unchanged."""

    def _get_statements(self, template):
        return template["Resources"]["LoggingBucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]

    def _find_statement(self, statements, sid):
        for stmt in statements:
            if isinstance(stmt, dict) and stmt.get("Sid") == sid:
                return stmt
        return None

    def test_deny_non_secure_transport_exists(self, template):
        """DenyNonSecureTransportAccess statement must exist."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "DenyNonSecureTransportAccess")
        assert stmt is not None, "DenyNonSecureTransportAccess policy statement is missing"

    def test_deny_non_secure_transport_effect(self, template):
        """DenyNonSecureTransportAccess must have Effect Deny."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "DenyNonSecureTransportAccess")
        assert stmt["Effect"] == "Deny"

    def test_deny_non_secure_transport_action(self, template):
        """DenyNonSecureTransportAccess must deny s3:*."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "DenyNonSecureTransportAccess")
        assert stmt["Action"] == "s3:*"

    def test_deny_non_secure_transport_condition(self, template):
        """DenyNonSecureTransportAccess must condition on aws:SecureTransport false."""
        stmts = self._get_statements(template)
        stmt = self._find_statement(stmts, "DenyNonSecureTransportAccess")
        condition = stmt["Condition"]["Bool"]
        assert condition["aws:SecureTransport"] is False


class TestPreservationBucketEncryption:
    """Preservation: BucketEncryption uses AES256 SSE algorithm."""

    def test_encryption_algorithm_is_aes256(self, template):
        """Bucket must use AES256 server-side encryption."""
        enc_config = template["Resources"]["Bucket"]["Properties"]["BucketEncryption"]
        sse_rules = enc_config["ServerSideEncryptionConfiguration"]
        assert len(sse_rules) >= 1
        sse_default = sse_rules[0]["ServerSideEncryptionByDefault"]
        assert sse_default["SSEAlgorithm"] == "AES256"

    def test_bucket_key_enabled(self, template):
        """Bucket key should be enabled for cost optimization."""
        enc_config = template["Resources"]["Bucket"]["Properties"]["BucketEncryption"]
        sse_rules = enc_config["ServerSideEncryptionConfiguration"]
        assert sse_rules[0]["BucketKeyEnabled"] is True


class TestPreservationLifecycleConfiguration:
    """Preservation: Lifecycle rule DeleteOldLogs with LogExpirationInDays."""

    def test_lifecycle_rule_exists(self, template):
        """DeleteOldLogs lifecycle rule must exist."""
        lifecycle = template["Resources"]["Bucket"]["Properties"]["LifecycleConfiguration"]
        rules = lifecycle["Rules"]
        rule_ids = [r["Id"] for r in rules]
        assert "DeleteOldLogs" in rule_ids

    def test_lifecycle_rule_enabled(self, template):
        """DeleteOldLogs rule must be enabled."""
        lifecycle = template["Resources"]["Bucket"]["Properties"]["LifecycleConfiguration"]
        rule = next(r for r in lifecycle["Rules"] if r["Id"] == "DeleteOldLogs")
        assert rule["Status"] == "Enabled"

    def test_lifecycle_expiration_references_parameter(self, template):
        """ExpirationInDays must reference LogExpirationInDays parameter."""
        lifecycle = template["Resources"]["Bucket"]["Properties"]["LifecycleConfiguration"]
        rule = next(r for r in lifecycle["Rules"] if r["Id"] == "DeleteOldLogs")
        expiration = rule["ExpirationInDays"]
        # CFNLoader preserves !Ref tag as {"!Ref": "LogExpirationInDays"}
        assert isinstance(expiration, dict)
        assert expiration.get("!Ref") == "LogExpirationInDays"


class TestPreservationRetentionPolicies:
    """Preservation: DeletionPolicy and UpdateReplacePolicy are Retain."""

    def test_deletion_policy_retain(self, template):
        """Bucket must have DeletionPolicy: Retain."""
        assert template["Resources"]["Bucket"]["DeletionPolicy"] == "Retain"

    def test_update_replace_policy_retain(self, template):
        """Bucket must have UpdateReplacePolicy: Retain."""
        assert template["Resources"]["Bucket"]["UpdateReplacePolicy"] == "Retain"


class TestPreservationBucketNaming:
    """Preservation: Bucket naming convention uses expected components."""

    def test_bucket_name_uses_join(self, template):
        """BucketName should use !Join to construct the name."""
        bucket_name = template["Resources"]["Bucket"]["Properties"]["BucketName"]
        assert "!Join" in bucket_name, "BucketName should use !Join"

    def test_bucket_name_separator_is_dash(self, template):
        """BucketName join separator should be a dash."""
        bucket_name = template["Resources"]["Bucket"]["Properties"]["BucketName"]
        separator = bucket_name["!Join"][0]
        assert separator == "-"

    def test_bucket_name_uses_conditional_org_prefix(self, template):
        """BucketName should use !If [UseS3BucketNameOrgPrefix, ...] for first segment."""
        bucket_name = template["Resources"]["Bucket"]["Properties"]["BucketName"]
        parts = bucket_name["!Join"][1]
        # First element should be an !If conditional
        first_part = parts[0]
        assert "!If" in first_part
        assert first_part["!If"][0] == "UseS3BucketNameOrgPrefix"

    def test_bucket_name_includes_region_and_account(self, template):
        """BucketName should include AWS::Region and AWS::AccountId via Sub."""
        bucket_name = template["Resources"]["Bucket"]["Properties"]["BucketName"]
        parts = bucket_name["!Join"][1]
        # Second element should be a Sub containing ProjectId, Region, AccountId
        second_part = parts[1]
        assert "!Sub" in second_part
        sub_str = second_part["!Sub"]
        assert "${ProjectId}" in sub_str
        assert "${AWS::Region}" in sub_str
        assert "${AWS::AccountId}" in sub_str


class TestPreservationOutputs:
    """Preservation: Outputs LoggingBucketName and LoggingBucketArn exist with exports."""

    def test_logging_bucket_name_output_exists(self, template):
        """LoggingBucketName output must exist."""
        outputs = template.get("Outputs", {})
        assert "LoggingBucketName" in outputs

    def test_logging_bucket_name_has_export(self, template):
        """LoggingBucketName must have an Export."""
        output = template["Outputs"]["LoggingBucketName"]
        assert "Export" in output
        assert "Name" in output["Export"]

    def test_logging_bucket_arn_output_exists(self, template):
        """LoggingBucketArn output must exist."""
        outputs = template.get("Outputs", {})
        assert "LoggingBucketArn" in outputs

    def test_logging_bucket_arn_has_export(self, template):
        """LoggingBucketArn must have an Export."""
        output = template["Outputs"]["LoggingBucketArn"]
        assert "Export" in output
        assert "Name" in output["Export"]


# =============================================================================
# Fix Verification Tests
# These tests verify the fix works correctly on the FIXED template.
# They validate conditional logic, structural correctness, and metadata.
# =============================================================================


class TestFixBlockPublicAclsConditionalLogic:
    """Verify BlockPublicAcls !If resolves correctly for both enabled and disabled."""

    def test_enabled_branch_is_false(self, template):
        """When AllowLegacyCloudFrontLogs is true, BlockPublicAcls should be false."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        val = pac["BlockPublicAcls"]
        assert isinstance(val, dict) and "!If" in val, (
            f"BlockPublicAcls should be an !If conditional, got: {val}"
        )
        if_list = val["!If"]
        assert if_list[0] == "EnableLegacyCloudFrontLogs"
        assert if_list[1] is False, (
            f"True-branch (enabled) should be false, got: {if_list[1]}"
        )

    def test_disabled_branch_is_true(self, template):
        """When AllowLegacyCloudFrontLogs is false/default, BlockPublicAcls should be true."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        val = pac["BlockPublicAcls"]
        if_list = val["!If"]
        assert if_list[2] is True, (
            f"False-branch (disabled) should be true, got: {if_list[2]}"
        )


class TestFixOwnershipControlsConditional:
    """Verify OwnershipControls uses !If with EnableLegacyCloudFrontLogs and AWS::NoValue."""

    def test_ownership_controls_uses_if(self, template):
        """OwnershipControls should be wrapped in !If conditional."""
        oc = template["Resources"]["Bucket"]["Properties"]["OwnershipControls"]
        assert isinstance(oc, dict) and "!If" in oc, (
            f"OwnershipControls should be an !If conditional, got: {oc}"
        )

    def test_ownership_controls_condition_name(self, template):
        """OwnershipControls !If should reference EnableLegacyCloudFrontLogs."""
        oc = template["Resources"]["Bucket"]["Properties"]["OwnershipControls"]
        assert oc["!If"][0] == "EnableLegacyCloudFrontLogs"

    def test_ownership_controls_enabled_value(self, template):
        """When enabled, OwnershipControls should set BucketOwnerPreferred."""
        oc = template["Resources"]["Bucket"]["Properties"]["OwnershipControls"]
        enabled_val = oc["!If"][1]
        rules = enabled_val.get("Rules", [])
        assert len(rules) >= 1
        assert rules[0]["ObjectOwnership"] == "BucketOwnerPreferred"

    def test_ownership_controls_disabled_is_novalue(self, template):
        """When disabled, OwnershipControls should use AWS::NoValue (absent)."""
        oc = template["Resources"]["Bucket"]["Properties"]["OwnershipControls"]
        disabled_val = oc["!If"][2]
        assert isinstance(disabled_val, dict) and "!Ref" in disabled_val
        assert disabled_val["!Ref"] == "AWS::NoValue"


class TestFixCloudFrontPolicyConditional:
    """Verify CloudFront log delivery policy statement uses !If with AWS::NoValue."""

    def _get_statements(self, template):
        return template["Resources"]["LoggingBucketPolicy"]["Properties"]["PolicyDocument"]["Statement"]

    def _find_cloudfront_if_wrapper(self, statements):
        """Find the !If wrapper around the CloudFront delivery statement."""
        for stmt in statements:
            if isinstance(stmt, dict) and "!If" in stmt:
                inner = stmt["!If"]
                if len(inner) >= 2 and isinstance(inner[1], dict):
                    if inner[1].get("Sid") == "AllowCloudFrontLogDelivery":
                        return inner
        return None

    def test_cloudfront_statement_wrapped_in_if(self, template):
        """CloudFront delivery statement should be wrapped in !If conditional."""
        stmts = self._get_statements(template)
        wrapper = self._find_cloudfront_if_wrapper(stmts)
        assert wrapper is not None, (
            "AllowCloudFrontLogDelivery should be wrapped in an !If conditional"
        )

    def test_cloudfront_if_references_condition(self, template):
        """CloudFront !If should reference EnableLegacyCloudFrontLogs."""
        stmts = self._get_statements(template)
        wrapper = self._find_cloudfront_if_wrapper(stmts)
        assert wrapper[0] == "EnableLegacyCloudFrontLogs"

    def test_cloudfront_if_disabled_is_novalue(self, template):
        """When disabled, CloudFront statement should use AWS::NoValue (absent)."""
        stmts = self._get_statements(template)
        wrapper = self._find_cloudfront_if_wrapper(stmts)
        disabled_val = wrapper[2]
        assert isinstance(disabled_val, dict) and "!Ref" in disabled_val
        assert disabled_val["!Ref"] == "AWS::NoValue"

    def test_cloudfront_statement_effect(self, template):
        """CloudFront delivery statement should have Effect Allow."""
        stmts = self._get_statements(template)
        wrapper = self._find_cloudfront_if_wrapper(stmts)
        stmt = wrapper[1]
        assert stmt["Effect"] == "Allow"

    def test_cloudfront_statement_resource(self, template):
        """CloudFront delivery statement resource should reference Bucket.Arn/*."""
        stmts = self._get_statements(template)
        wrapper = self._find_cloudfront_if_wrapper(stmts)
        stmt = wrapper[1]
        resource = stmt["Resource"]
        assert isinstance(resource, dict) and "!Sub" in resource
        assert "Bucket.Arn" in resource["!Sub"]


class TestFixOtherPublicAccessBlocksUnchanged:
    """Verify BlockPublicPolicy, IgnorePublicAcls, RestrictPublicBuckets are unconditionally true."""

    def test_block_public_policy_unconditionally_true(self, template):
        """BlockPublicPolicy must be a plain boolean true, not conditional."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        assert pac["BlockPublicPolicy"] is True

    def test_ignore_public_acls_unconditionally_true(self, template):
        """IgnorePublicAcls must be a plain boolean true, not conditional."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        assert pac["IgnorePublicAcls"] is True

    def test_restrict_public_buckets_unconditionally_true(self, template):
        """RestrictPublicBuckets must be a plain boolean true, not conditional."""
        pac = template["Resources"]["Bucket"]["Properties"]["PublicAccessBlockConfiguration"]
        assert pac["RestrictPublicBuckets"] is True


class TestFixMetadataParameterGroups:
    """Verify AllowLegacyCloudFrontLogs appears in Metadata ParameterGroups."""

    def test_parameter_in_metadata_groups(self, template):
        """AllowLegacyCloudFrontLogs should be listed in a Metadata ParameterGroup."""
        groups = template["Metadata"]["AWS::CloudFormation::Interface"]["ParameterGroups"]
        all_params = []
        for group in groups:
            all_params.extend(group.get("Parameters", []))
        assert "AllowLegacyCloudFrontLogs" in all_params, (
            "AllowLegacyCloudFrontLogs not found in any Metadata ParameterGroup"
        )


class TestFixTemplateVersion:
    """Verify template version has been incremented to v0.0.2."""

    def test_version_comment_is_v002(self):
        """Template version comment should be v0.0.2."""
        template_path = Path(__file__).parent.parent / "templates" / "v2" / "storage" / "template-storage-s3-access-logs.yml"
        content = template_path.read_text()
        assert "v0.0.2" in content, (
            "Template version should be v0.0.2 after the fix"
        )
