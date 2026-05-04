"""
Unit tests for S3 OAC domain format in template-storage-s3-oac-for-cloudfront.yml.

Bug condition exploration tests encode the EXPECTED (correct) behavior.
On UNFIXED code, they MUST FAIL — confirming the bug exists:
  - The output uses !GetAtt OriginBucketRegional.DomainName (global domain format)
  - It should use !Sub with regional domain pattern including AWS::Region

Validates: Requirements 1.1, 1.2, 2.1, 2.2
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
    """Load the S3 OAC for CloudFront template for testing."""
    template_path = (
        Path(__file__).parent.parent
        / "templates"
        / "v2"
        / "storage"
        / "template-storage-s3-oac-for-cloudfront.yml"
    )
    return load_template(template_path)


# =============================================================================
# Bug Condition Exploration Tests
# These tests MUST FAIL on unfixed code to confirm the bug exists.
# DO NOT fix the template or modify these tests to make them pass.
# =============================================================================


class TestOriginBucketDomainUsesSubNotGetAtt:
    """Bug condition: OriginBucketDomainForCloudFront must use !Sub, not !GetAtt.

    Validates: Requirements 1.2, 2.2
    """

    def test_output_value_uses_sub(self, template):
        """OriginBucketDomainForCloudFront output value should use !Sub intrinsic."""
        output = template["Outputs"]["OriginBucketDomainForCloudFront"]
        value = output["Value"]

        assert isinstance(value, dict) and "!Sub" in value, (
            f"COUNTEREXAMPLE: OriginBucketDomainForCloudFront output value is {value}. "
            "Expected a !Sub expression for regional domain format, "
            "but found !GetAtt which produces the global S3 domain format."
        )


class TestOriginBucketDomainContainsRegion:
    """Bug condition: OriginBucketDomainForCloudFront must contain AWS::Region.

    Validates: Requirements 1.1, 2.2
    """

    def test_output_value_contains_aws_region(self, template):
        """OriginBucketDomainForCloudFront output value should reference AWS::Region."""
        output = template["Outputs"]["OriginBucketDomainForCloudFront"]
        value = output["Value"]

        # Convert value to string for region check
        value_str = str(value)

        assert "AWS::Region" in value_str, (
            f"COUNTEREXAMPLE: OriginBucketDomainForCloudFront output value is {value}. "
            "The value does NOT contain AWS::Region. "
            "Without the region, the domain resolves to the global S3 endpoint "
            "which causes 307 redirects for CloudFront OAC distributions."
        )


class TestOriginBucketDomainMatchesRegionalPattern:
    """Bug condition: OriginBucketDomainForCloudFront must match regional domain pattern.

    Validates: Requirements 2.1, 2.2
    """

    def test_output_value_matches_regional_domain_pattern(self, template):
        """OriginBucketDomainForCloudFront should produce https://<bucket>.s3.<region>.amazonaws.com."""
        output = template["Outputs"]["OriginBucketDomainForCloudFront"]
        value = output["Value"]

        expected_pattern = "https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com"

        # The value must be a !Sub with the regional domain pattern
        assert isinstance(value, dict) and "!Sub" in value, (
            f"COUNTEREXAMPLE: OriginBucketDomainForCloudFront output value is {value}. "
            f"Expected !Sub with pattern '{expected_pattern}'."
        )

        sub_value = value["!Sub"]
        assert sub_value == expected_pattern, (
            f"COUNTEREXAMPLE: OriginBucketDomainForCloudFront !Sub value is '{sub_value}'. "
            f"Expected '{expected_pattern}'. "
            "The output must use the regional S3 domain format with https:// prefix."
        )


# =============================================================================
# Preservation Tests (Task 2)
# These tests capture the baseline behavior of the UNFIXED template.
# They MUST PASS on unfixed code to confirm no regressions after the fix.
# DO NOT modify these tests when implementing the fix.
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
# =============================================================================


class TestParametersPreservation:
    """All template parameters must remain identical after the fix.

    Validates: Requirements 3.1, 3.2
    """

    EXPECTED_PARAMETERS = [
        "Prefix",
        "ProjectId",
        "S3BucketNameOrgPrefix",
        "RolePath",
        "AlarmNotificationEmail",
        "PermissionsBoundaryArn",
        "S3LogBucketName",
        "InvalidatorArn",
    ]

    def test_all_expected_parameters_exist(self, template):
        """Template must contain exactly the expected set of parameters."""
        params = template["Parameters"]
        assert sorted(params.keys()) == sorted(self.EXPECTED_PARAMETERS), (
            f"Parameter mismatch. Expected: {sorted(self.EXPECTED_PARAMETERS)}, "
            f"Got: {sorted(params.keys())}"
        )

    def test_prefix_parameter(self, template):
        """Prefix parameter definition must be unchanged."""
        param = template["Parameters"]["Prefix"]
        assert param["Type"] == "String"
        assert param["Default"] == "acme"
        assert param["AllowedPattern"] == "^[a-z][a-z0-9-]{0,6}[a-z0-9]$"
        assert param["MinLength"] == 2
        assert param["MaxLength"] == 8

    def test_project_id_parameter(self, template):
        """ProjectId parameter definition must be unchanged."""
        param = template["Parameters"]["ProjectId"]
        assert param["Type"] == "String"
        assert param["AllowedPattern"] == "^[a-z][a-z0-9-]{0,24}[a-z0-9]$"
        assert param["MinLength"] == 2
        assert param["MaxLength"] == 26

    def test_s3_bucket_name_org_prefix_parameter(self, template):
        """S3BucketNameOrgPrefix parameter definition must be unchanged."""
        param = template["Parameters"]["S3BucketNameOrgPrefix"]
        assert param["Type"] == "String"
        assert param["Default"] == ""
        assert param["AllowedPattern"] == "^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$|^$"

    def test_role_path_parameter(self, template):
        """RolePath parameter definition must be unchanged."""
        param = template["Parameters"]["RolePath"]
        assert param["Type"] == "String"
        assert param["Default"] == "/"
        assert param["AllowedPattern"] == "^\\/([a-zA-Z0-9-_]+[\\/])+$|^\\/$"

    def test_alarm_notification_email_parameter(self, template):
        """AlarmNotificationEmail parameter definition must be unchanged."""
        param = template["Parameters"]["AlarmNotificationEmail"]
        assert param["Type"] == "String"
        assert param["AllowedPattern"] == "^[\\w\\-\\.]+@([\\w\\-]+\\.)+[\\w\\-]{2,4}$"

    def test_permissions_boundary_arn_parameter(self, template):
        """PermissionsBoundaryArn parameter definition must be unchanged."""
        param = template["Parameters"]["PermissionsBoundaryArn"]
        assert param["Type"] == "String"
        assert param["Default"] == ""

    def test_s3_log_bucket_name_parameter(self, template):
        """S3LogBucketName parameter definition must be unchanged."""
        param = template["Parameters"]["S3LogBucketName"]
        assert param["Type"] == "String"
        assert param["Default"] == ""
        assert param["AllowedPattern"] == "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"

    def test_invalidator_arn_parameter(self, template):
        """InvalidatorArn parameter definition must be unchanged."""
        param = template["Parameters"]["InvalidatorArn"]
        assert param["Type"] == "String"
        assert param["Default"] == ""
        assert param["AllowedPattern"] == "^$|^arn:aws:lambda:[a-z0-9-]+:\\d{12}:function:[a-zA-Z0-9-_]+$"


class TestConditionsPreservation:
    """All template conditions must remain identical after the fix.

    Validates: Requirements 3.1, 3.2
    """

    EXPECTED_CONDITIONS = [
        "UseS3BucketNameOrgPrefix",
        "HasLoggingBucket",
        "HasInvalidatorArn",
    ]

    def test_all_expected_conditions_exist(self, template):
        """Template must contain exactly the expected set of conditions."""
        conditions = template["Conditions"]
        assert sorted(conditions.keys()) == sorted(self.EXPECTED_CONDITIONS), (
            f"Condition mismatch. Expected: {sorted(self.EXPECTED_CONDITIONS)}, "
            f"Got: {sorted(conditions.keys())}"
        )

    def test_use_s3_bucket_name_org_prefix_condition(self, template):
        """UseS3BucketNameOrgPrefix condition must check S3BucketNameOrgPrefix != empty."""
        condition = template["Conditions"]["UseS3BucketNameOrgPrefix"]
        # Structure: !Not [!Equals [!Ref S3BucketNameOrgPrefix, ""]]
        assert "!Not" in condition
        inner = condition["!Not"]
        assert len(inner) == 1
        equals_expr = inner[0]
        assert "!Equals" in equals_expr
        equals_args = equals_expr["!Equals"]
        assert {"!Ref": "S3BucketNameOrgPrefix"} in equals_args
        assert "" in equals_args

    def test_has_logging_bucket_condition(self, template):
        """HasLoggingBucket condition must check S3LogBucketName != empty."""
        condition = template["Conditions"]["HasLoggingBucket"]
        assert "!Not" in condition
        inner = condition["!Not"]
        assert len(inner) == 1
        equals_expr = inner[0]
        assert "!Equals" in equals_expr
        equals_args = equals_expr["!Equals"]
        assert {"!Ref": "S3LogBucketName"} in equals_args
        assert "" in equals_args

    def test_has_invalidator_arn_condition(self, template):
        """HasInvalidatorArn condition must check InvalidatorArn != empty."""
        condition = template["Conditions"]["HasInvalidatorArn"]
        assert "!Not" in condition
        inner = condition["!Not"]
        assert len(inner) == 1
        equals_expr = inner[0]
        assert "!Equals" in equals_expr
        equals_args = equals_expr["!Equals"]
        assert {"!Ref": "InvalidatorArn"} in equals_args
        assert "" in equals_args


class TestOriginBucketRegionalPreservation:
    """OriginBucketRegional S3 bucket resource properties must be unchanged.

    Validates: Requirements 3.1
    """

    def test_resource_type(self, template):
        """OriginBucketRegional must be an S3 bucket."""
        resource = template["Resources"]["OriginBucketRegional"]
        assert resource["Type"] == "AWS::S3::Bucket"

    def test_deletion_policy(self, template):
        """OriginBucketRegional DeletionPolicy must be Delete."""
        resource = template["Resources"]["OriginBucketRegional"]
        assert resource["DeletionPolicy"] == "Delete"

    def test_bucket_name_uses_conditional(self, template):
        """BucketName must use !If with UseS3BucketNameOrgPrefix condition."""
        props = template["Resources"]["OriginBucketRegional"]["Properties"]
        bucket_name = props["BucketName"]
        assert "!If" in bucket_name
        if_args = bucket_name["!If"]
        assert if_args[0] == "UseS3BucketNameOrgPrefix"

    def test_bucket_name_with_org_prefix(self, template):
        """BucketName with org prefix must use the expected Sub pattern."""
        props = template["Resources"]["OriginBucketRegional"]["Properties"]
        if_args = props["BucketName"]["!If"]
        # Second element: with org prefix
        with_prefix = if_args[1]
        assert "!Sub" in with_prefix
        assert with_prefix["!Sub"] == "${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-origin-${AWS::AccountId}-${AWS::Region}-an"

    def test_bucket_name_without_org_prefix(self, template):
        """BucketName without org prefix must use the expected Sub pattern."""
        props = template["Resources"]["OriginBucketRegional"]["Properties"]
        if_args = props["BucketName"]["!If"]
        # Third element: without org prefix
        without_prefix = if_args[2]
        assert "!Sub" in without_prefix
        assert without_prefix["!Sub"] == "${Prefix}-${ProjectId}-origin-${AWS::AccountId}-${AWS::Region}-an"

    def test_bucket_encryption(self, template):
        """BucketEncryption must use AES256 with BucketKeyEnabled."""
        props = template["Resources"]["OriginBucketRegional"]["Properties"]
        encryption = props["BucketEncryption"]
        config = encryption["ServerSideEncryptionConfiguration"]
        assert len(config) == 1
        rule = config[0]
        assert rule["BucketKeyEnabled"] is True
        assert rule["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"

    def test_public_access_block(self, template):
        """PublicAccessBlockConfiguration must block all public access."""
        props = template["Resources"]["OriginBucketRegional"]["Properties"]
        public_access = props["PublicAccessBlockConfiguration"]
        assert public_access["BlockPublicAcls"] is True
        assert public_access["BlockPublicPolicy"] is True
        assert public_access["IgnorePublicAcls"] is True
        assert public_access["RestrictPublicBuckets"] is True


class TestBucketPolicyPreservation:
    """BucketPolicy resource and all policy statements must be unchanged.

    Validates: Requirements 3.2
    """

    def test_resource_type(self, template):
        """BucketPolicy must be an S3 BucketPolicy."""
        resource = template["Resources"]["BucketPolicy"]
        assert resource["Type"] == "AWS::S3::BucketPolicy"

    def test_bucket_reference(self, template):
        """BucketPolicy must reference OriginBucketRegional."""
        props = template["Resources"]["BucketPolicy"]["Properties"]
        assert props["Bucket"] == {"!Ref": "OriginBucketRegional"}

    def test_policy_version(self, template):
        """Policy document version must be 2012-10-17."""
        policy = template["Resources"]["BucketPolicy"]["Properties"]["PolicyDocument"]
        assert policy["Version"] == "2012-10-17"

    def test_policy_has_three_statements(self, template):
        """Policy must have exactly 3 statements."""
        policy = template["Resources"]["BucketPolicy"]["Properties"]["PolicyDocument"]
        assert len(policy["Statement"]) == 3

    def test_deny_non_secure_transport_statement(self, template):
        """DenyNonSecureTransportAccess statement must be unchanged."""
        policy = template["Resources"]["BucketPolicy"]["Properties"]["PolicyDocument"]
        stmt = policy["Statement"][0]
        assert stmt["Sid"] == "DenyNonSecureTransportAccess"
        assert stmt["Effect"] == "Deny"
        assert stmt["Principal"] == "*"
        assert stmt["Action"] == "s3:*"
        assert stmt["Condition"] == {"Bool": {"aws:SecureTransport": False}}

    def test_allow_cloudfront_read_only_statement(self, template):
        """AllowCloudFrontServicePrincipalReadOnly statement must be unchanged."""
        policy = template["Resources"]["BucketPolicy"]["Properties"]["PolicyDocument"]
        stmt = policy["Statement"][1]
        assert stmt["Sid"] == "AllowCloudFrontServicePrincipalReadOnly"
        assert stmt["Effect"] == "Allow"
        assert stmt["Action"] == ["s3:GetObject"]
        assert stmt["Principal"] == {"Service": "cloudfront.amazonaws.com"}
        assert stmt["Resource"] == {"!Sub": "${OriginBucketRegional.Arn}/*"}
        assert stmt["Condition"] == {
            "StringLike": {
                "aws:SourceArn": {
                    "!Sub": "arn:aws:cloudfront::${AWS::AccountId}:distribution/*"
                }
            }
        }

    def test_allow_codebuild_read_write_delete_statement(self, template):
        """AllowCodeBuildReadWriteDelete statement must be unchanged."""
        policy = template["Resources"]["BucketPolicy"]["Properties"]["PolicyDocument"]
        stmt = policy["Statement"][2]
        assert stmt["Sid"] == "AllowCodeBuildReadWriteDelete"
        assert stmt["Effect"] == "Allow"
        assert stmt["Action"] == ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        assert stmt["Principal"] == {"Service": "codebuild.amazonaws.com"}
        assert stmt["Resource"] == {"!Sub": "${OriginBucketRegional.Arn}/*"}
        assert stmt["Condition"] == {
            "StringLike": {
                "aws:SourceArn": {
                    "!Sub": "arn:aws:codebuild:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-${ProjectId}-*"
                }
            }
        }


class TestS3InvokeLambdaPermissionPreservation:
    """S3InvokeLambdaPermission resource must be unchanged.

    Validates: Requirements 3.5
    """

    def test_resource_type(self, template):
        """S3InvokeLambdaPermission must be a Lambda Permission."""
        resource = template["Resources"]["S3InvokeLambdaPermission"]
        assert resource["Type"] == "AWS::Lambda::Permission"

    def test_condition(self, template):
        """S3InvokeLambdaPermission must have HasInvalidatorArn condition."""
        resource = template["Resources"]["S3InvokeLambdaPermission"]
        assert resource["Condition"] == "HasInvalidatorArn"

    def test_properties(self, template):
        """S3InvokeLambdaPermission properties must be unchanged."""
        props = template["Resources"]["S3InvokeLambdaPermission"]["Properties"]
        assert props["FunctionName"] == {"!Ref": "InvalidatorArn"}
        assert props["Action"] == "lambda:InvokeFunction"
        assert props["Principal"] == "s3.amazonaws.com"
        assert props["SourceAccount"] == {"!Ref": "AWS::AccountId"}
        assert props["SourceArn"] == {"!GetAtt": "OriginBucketRegional.Arn"}


class TestOutputsPreservation:
    """All outputs (except OriginBucketDomainForCloudFront value) must be unchanged.

    Validates: Requirements 3.3, 3.4, 3.5
    """

    def test_bucket_name_output(self, template):
        """BucketName output must use !Ref OriginBucketRegional."""
        output = template["Outputs"]["BucketName"]
        assert output["Value"] == {"!Ref": "OriginBucketRegional"}
        assert "Description" in output

    def test_allowed_cloudfront_and_codebuild_output(self, template):
        """AllowedCloudFrontAndCodeBuild output must use !Sub with Prefix-ProjectId."""
        output = template["Outputs"]["AllowedCloudFrontAndCodeBuild"]
        assert output["Value"] == {"!Sub": "${Prefix}-${ProjectId}"}
        assert "Description" in output

    def test_logging_bucket_name_output(self, template):
        """LoggingBucketName output must be conditional and reference S3LogBucketName."""
        output = template["Outputs"]["LoggingBucketName"]
        assert output["Condition"] == "HasLoggingBucket"
        assert output["Value"] == {"!Ref": "S3LogBucketName"}
        assert "Description" in output

    def test_invalidator_arn_output(self, template):
        """InvalidatorArn output must be conditional and reference InvalidatorArn param."""
        output = template["Outputs"]["InvalidatorArn"]
        assert output["Condition"] == "HasInvalidatorArn"
        assert output["Value"] == {"!Ref": "InvalidatorArn"}
        assert "Description" in output

    def test_invalidation_events_enabled_output(self, template):
        """InvalidationEventsEnabled output must use !If with HasInvalidatorArn."""
        output = template["Outputs"]["InvalidationEventsEnabled"]
        value = output["Value"]
        assert "!If" in value
        if_args = value["!If"]
        assert if_args[0] == "HasInvalidatorArn"
        assert if_args[1] == "true"
        assert if_args[2] == "false"
        assert "Description" in output
