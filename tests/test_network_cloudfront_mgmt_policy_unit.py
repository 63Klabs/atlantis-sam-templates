"""
Unit tests for the network-cloudfront-mgmt-policy.yml module template.

Validates that the policy contains the correct statements for CloudFront
Origin Request Policy read, API Gateway /apis read, S3 bucket read for
logging (fixed pattern), and that existing statements remain unchanged.

Validates: Requirements 1.1, 2.1, 3.1, 4.2
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


# --- Fixtures ---


@pytest.fixture
def template():
    """Load the network CloudFront management policy module template."""
    template_path = (
        Path(__file__).parent.parent
        / "templates"
        / "v2"
        / "modules"
        / "management-roles"
        / "network-cloudfront-mgmt-policy.yml"
    )
    return load_template(template_path)


@pytest.fixture
def statements(template):
    """Extract policy statements from the template."""
    return template["Properties"]["PolicyDocument"]["Statement"]


def find_statement_by_sid(statements, sid):
    """Find a statement by its Sid field."""
    for stmt in statements:
        if stmt.get("Sid") == sid:
            return stmt
    return None


# --- Task 5.1: CloudFrontOriginRequestPolicyRead ---


class TestCloudFrontOriginRequestPolicyRead:
    """Verify CloudFrontOriginRequestPolicyRead exists with correct configuration."""

    def test_statement_exists(self, statements):
        """CloudFrontOriginRequestPolicyRead statement must exist."""
        stmt = find_statement_by_sid(statements, "CloudFrontOriginRequestPolicyRead")
        assert stmt is not None, "CloudFrontOriginRequestPolicyRead statement not found"

    def test_sid_is_correct(self, statements):
        """Statement Sid must be exactly CloudFrontOriginRequestPolicyRead."""
        stmt = find_statement_by_sid(statements, "CloudFrontOriginRequestPolicyRead")
        assert stmt["Sid"] == "CloudFrontOriginRequestPolicyRead"

    def test_effect_is_allow(self, statements):
        """CloudFrontOriginRequestPolicyRead must have Effect: Allow."""
        stmt = find_statement_by_sid(statements, "CloudFrontOriginRequestPolicyRead")
        assert stmt["Effect"] == "Allow"

    def test_has_all_three_actions(self, statements):
        """CloudFrontOriginRequestPolicyRead must have all three required actions."""
        stmt = find_statement_by_sid(statements, "CloudFrontOriginRequestPolicyRead")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        expected_actions = [
            "cloudfront:GetOriginRequestPolicy",
            "cloudfront:GetOriginRequestPolicyConfig",
            "cloudfront:ListOriginRequestPolicies",
        ]
        assert sorted(actions) == sorted(expected_actions)

    def test_resource_is_wildcard(self, statements):
        """CloudFrontOriginRequestPolicyRead must have Resource: '*'."""
        stmt = find_statement_by_sid(statements, "CloudFrontOriginRequestPolicyRead")
        assert stmt["Resource"] == "*"


# --- Task 5.2: ApiGatewayV2ReadApis ---


class TestApiGatewayV2ReadApis:
    """Verify ApiGatewayV2ReadApis exists with correct configuration."""

    def test_statement_exists(self, statements):
        """ApiGatewayV2ReadApis statement must exist."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2ReadApis")
        assert stmt is not None, "ApiGatewayV2ReadApis statement not found"

    def test_sid_is_correct(self, statements):
        """Statement Sid must be exactly ApiGatewayV2ReadApis."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2ReadApis")
        assert stmt["Sid"] == "ApiGatewayV2ReadApis"

    def test_effect_is_allow(self, statements):
        """ApiGatewayV2ReadApis must have Effect: Allow."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2ReadApis")
        assert stmt["Effect"] == "Allow"

    def test_action_is_apigateway_get(self, statements):
        """ApiGatewayV2ReadApis must have action apigateway:GET."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2ReadApis")
        action = stmt["Action"]
        if isinstance(action, list):
            assert action == ["apigateway:GET"]
        else:
            assert action == "apigateway:GET"

    def test_resource_arns_use_fn_sub(self, statements):
        """ApiGatewayV2ReadApis resources must use Fn::Sub for both /apis and /apis/*."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2ReadApis")
        resource = stmt["Resource"]
        assert isinstance(resource, list), "Resource should be a list of ARNs"
        assert len(resource) == 2, "Resource should contain exactly 2 ARNs"

        # Both entries should be Fn::Sub dicts
        for r in resource:
            assert isinstance(r, dict), "Each resource entry should be a dict (Fn::Sub)"
            assert "Fn::Sub" in r, "Each resource must use Fn::Sub"

    def test_resource_contains_apis_path(self, statements):
        """ApiGatewayV2ReadApis resources must contain /apis and /apis/* paths."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2ReadApis")
        resource = stmt["Resource"]

        # Extract the Fn::Sub values
        sub_values = [r["Fn::Sub"] for r in resource]
        assert "arn:aws:apigateway:${AWS::Region}::/apis" in sub_values
        assert "arn:aws:apigateway:${AWS::Region}::/apis/*" in sub_values


# --- Task 5.3: S3BucketReadForLogging pattern fix ---


class TestS3BucketReadForLoggingPattern:
    """Verify S3BucketReadForLogging resource uses corrected pattern."""

    def test_statement_exists(self, statements):
        """S3BucketReadForLogging statement must exist."""
        stmt = find_statement_by_sid(statements, "S3BucketReadForLogging")
        assert stmt is not None, "S3BucketReadForLogging statement not found"

    def test_resource_uses_fn_sub_with_fn_if(self, statements):
        """S3BucketReadForLogging resource must use Fn::Sub with Fn::If."""
        stmt = find_statement_by_sid(statements, "S3BucketReadForLogging")
        resource = stmt["Resource"]

        # Resource is a list with one Fn::Sub entry
        assert isinstance(resource, list), "Resource should be a list"
        fn_sub_entry = resource[0]
        assert isinstance(fn_sub_entry, dict), "Resource entry should be a dict"
        assert "Fn::Sub" in fn_sub_entry, "Resource must use Fn::Sub"

        # Fn::Sub value is a list: [template_string, variable_map]
        fn_sub_value = fn_sub_entry["Fn::Sub"]
        assert isinstance(fn_sub_value, list), "Fn::Sub should be a list [template, vars]"
        assert len(fn_sub_value) == 2, "Fn::Sub should have template and variable map"

        # Variable map must contain BucketPrefix with Fn::If
        var_map = fn_sub_value[1]
        assert "BucketPrefix" in var_map, "Variable map must contain BucketPrefix"
        bucket_prefix = var_map["BucketPrefix"]
        assert "Fn::If" in bucket_prefix, "BucketPrefix must use Fn::If"

    def test_fn_if_uses_use_s3_bucket_name_org_prefix_condition(self, statements):
        """Fn::If must reference the UseS3BucketNameOrgPrefix condition."""
        stmt = find_statement_by_sid(statements, "S3BucketReadForLogging")
        resource = stmt["Resource"]
        fn_sub_value = resource[0]["Fn::Sub"]
        var_map = fn_sub_value[1]
        fn_if = var_map["BucketPrefix"]["Fn::If"]

        assert fn_if[0] == "UseS3BucketNameOrgPrefix", (
            "Fn::If condition must be UseS3BucketNameOrgPrefix"
        )

    def test_non_org_prefix_branch_resolves_to_prefix_only(self, statements):
        """Non-org-prefix branch must resolve to ${Prefix} (not ${Prefix}-${AWS::AccountId}-${AWS::Region})."""
        stmt = find_statement_by_sid(statements, "S3BucketReadForLogging")
        resource = stmt["Resource"]
        fn_sub_value = resource[0]["Fn::Sub"]
        var_map = fn_sub_value[1]
        fn_if = var_map["BucketPrefix"]["Fn::If"]

        # fn_if[2] is the non-org-prefix (false) branch
        non_org_branch = fn_if[2]
        assert isinstance(non_org_branch, dict), "Non-org branch should be a dict (Fn::Sub)"
        assert "Fn::Sub" in non_org_branch, "Non-org branch must use Fn::Sub"

        sub_value = non_org_branch["Fn::Sub"]
        assert sub_value == "${Prefix}", (
            f"Non-org-prefix branch should be '${{Prefix}}' but got '{sub_value}'"
        )
        # Explicitly verify it does NOT contain AccountId or Region
        assert "${AWS::AccountId}" not in sub_value, (
            "Non-org-prefix branch must NOT contain ${AWS::AccountId}"
        )
        assert "${AWS::Region}" not in sub_value, (
            "Non-org-prefix branch must NOT contain ${AWS::Region}"
        )


# --- Task 5.4: Existing statements unchanged ---


EXPECTED_CLOUDFRONT_DISTRIBUTION_CRUD_ACTIONS = [
    "cloudfront:CreateDistribution",
    "cloudfront:CreateDistributionWithTags",
    "cloudfront:UpdateDistribution",
    "cloudfront:DeleteDistribution",
    "cloudfront:GetDistribution",
    "cloudfront:GetDistributionConfig",
    "cloudfront:ListDistributions",
    "cloudfront:TagResource",
    "cloudfront:UntagResource",
    "cloudfront:ListTagsForResource",
]

EXPECTED_CLOUDFRONT_OAC_CRUD_ACTIONS = [
    "cloudfront:CreateOriginAccessControl",
    "cloudfront:UpdateOriginAccessControl",
    "cloudfront:DeleteOriginAccessControl",
    "cloudfront:GetOriginAccessControl",
    "cloudfront:GetOriginAccessControlConfig",
    "cloudfront:ListOriginAccessControls",
]

EXPECTED_CLOUDFRONT_CACHE_POLICY_CRUD_ACTIONS = [
    "cloudfront:CreateCachePolicy",
    "cloudfront:UpdateCachePolicy",
    "cloudfront:DeleteCachePolicy",
    "cloudfront:GetCachePolicy",
    "cloudfront:GetCachePolicyConfig",
    "cloudfront:ListCachePolicies",
]

EXPECTED_API_GATEWAY_V2_DOMAIN_CRUD_ACTIONS = [
    "apigateway:POST",
    "apigateway:GET",
    "apigateway:PATCH",
    "apigateway:DELETE",
    "apigateway:PUT",
]


class TestExistingStatementsUnchanged:
    """Verify existing statements remain unchanged after adding new permissions."""

    def test_cloudfront_distribution_crud_exists(self, statements):
        """CloudFrontDistributionCRUD statement must still exist."""
        stmt = find_statement_by_sid(statements, "CloudFrontDistributionCRUD")
        assert stmt is not None, "CloudFrontDistributionCRUD statement not found"

    def test_cloudfront_distribution_crud_actions(self, statements):
        """CloudFrontDistributionCRUD must have all expected actions."""
        stmt = find_statement_by_sid(statements, "CloudFrontDistributionCRUD")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert sorted(actions) == sorted(EXPECTED_CLOUDFRONT_DISTRIBUTION_CRUD_ACTIONS)

    def test_cloudfront_oac_crud_exists(self, statements):
        """CloudFrontOACCRUD statement must still exist."""
        stmt = find_statement_by_sid(statements, "CloudFrontOACCRUD")
        assert stmt is not None, "CloudFrontOACCRUD statement not found"

    def test_cloudfront_oac_crud_actions(self, statements):
        """CloudFrontOACCRUD must have all expected actions."""
        stmt = find_statement_by_sid(statements, "CloudFrontOACCRUD")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert sorted(actions) == sorted(EXPECTED_CLOUDFRONT_OAC_CRUD_ACTIONS)

    def test_cloudfront_cache_policy_crud_exists(self, statements):
        """CloudFrontCachePolicyCRUD statement must still exist."""
        stmt = find_statement_by_sid(statements, "CloudFrontCachePolicyCRUD")
        assert stmt is not None, "CloudFrontCachePolicyCRUD statement not found"

    def test_cloudfront_cache_policy_crud_actions(self, statements):
        """CloudFrontCachePolicyCRUD must have all expected actions."""
        stmt = find_statement_by_sid(statements, "CloudFrontCachePolicyCRUD")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert sorted(actions) == sorted(EXPECTED_CLOUDFRONT_CACHE_POLICY_CRUD_ACTIONS)

    def test_api_gateway_v2_domain_crud_exists(self, statements):
        """ApiGatewayV2DomainCRUD statement must still exist."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2DomainCRUD")
        assert stmt is not None, "ApiGatewayV2DomainCRUD statement not found"

    def test_api_gateway_v2_domain_crud_actions(self, statements):
        """ApiGatewayV2DomainCRUD must have all expected actions."""
        stmt = find_statement_by_sid(statements, "ApiGatewayV2DomainCRUD")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert sorted(actions) == sorted(EXPECTED_API_GATEWAY_V2_DOMAIN_CRUD_ACTIONS)
