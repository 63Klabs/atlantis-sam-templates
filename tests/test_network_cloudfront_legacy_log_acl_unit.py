"""
Unit tests for the CloudFront legacy (v1) standard-logging ACL permissions in
network-cloudfront-mgmt-policy.yml.

CloudFront standard logging (legacy/v1) is ACL-based: on
CreateDistribution/UpdateDistribution with logging enabled, CloudFront rewrites
the destination bucket's ACL to grant the awslogsdelivery account FULL_CONTROL.
The calling principal (the CloudFormation service role) must therefore hold
s3:GetBucketAcl and s3:PutBucketAcl on that bucket, otherwise the distribution
fails with a 403 "You don't have permission to access the S3 bucket for
CloudFront logs".

Validates that:
- S3BucketAclForCloudFrontLegacyLogging exists with Effect: Allow
- It grants exactly s3:GetBucketAcl and s3:PutBucketAcl (no broader S3 actions)
- It covers the account-wide cloudfront-logs-legacy bucket (both the plain and
  the S3BucketNameOrgPrefix variant)
- It covers prefix-namespaced buckets for an explicit S3LogBucketName override
- Resources stay scoped (no "*" / whole-account wildcard)
- The pre-existing S3BucketReadForLogging statement is unchanged
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


ACL_SID = "S3BucketAclForCloudFrontLegacyLogging"
LEGACY_BUCKET_SUFFIX = "cloudfront-logs-legacy-${AWS::AccountId}-${AWS::Region}-an"


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


@pytest.fixture
def acl_statement(statements):
    """The CloudFront legacy logging ACL statement."""
    return find_statement_by_sid(statements, ACL_SID)


def find_statement_by_sid(statements, sid):
    """Find a statement by its Sid field."""
    for stmt in statements:
        if stmt.get("Sid") == sid:
            return stmt
    return None


def as_list(value):
    """Normalize a scalar-or-list policy field to a list."""
    if isinstance(value, list):
        return value
    return [value]


def flatten_resources(resources):
    """Return every literal Fn::Sub string reachable from a Resource entry.

    Handles the three shapes used by the module: a bare Fn::Sub string, an
    Fn::Sub with a variable map, and an Fn::If wrapping either of those.
    """
    strings = []
    for entry in as_list(resources):
        if isinstance(entry, str):
            strings.append(entry)
        elif isinstance(entry, dict) and "Fn::Sub" in entry:
            sub = entry["Fn::Sub"]
            strings.append(sub if isinstance(sub, str) else sub[0])
        elif isinstance(entry, dict) and "Fn::If" in entry:
            # [condition, if_true, if_false] - recurse into both branches
            strings.extend(flatten_resources(entry["Fn::If"][1:]))
    return strings


# --- Statement presence and shape ---


class TestAclStatementExists:
    """Verify the ACL statement exists and is well formed."""

    def test_statement_exists(self, acl_statement):
        """S3BucketAclForCloudFrontLegacyLogging statement must exist."""
        assert acl_statement is not None, f"{ACL_SID} statement not found"

    def test_effect_is_allow(self, acl_statement):
        """The statement must have Effect: Allow."""
        assert acl_statement["Effect"] == "Allow"

    def test_grants_both_acl_actions(self, acl_statement):
        """Both s3:GetBucketAcl and s3:PutBucketAcl are required by CloudFront."""
        actions = as_list(acl_statement["Action"])
        assert "s3:GetBucketAcl" in actions
        assert "s3:PutBucketAcl" in actions

    def test_grants_only_acl_actions(self, acl_statement):
        """The statement must not smuggle in broader S3 actions."""
        actions = as_list(acl_statement["Action"])
        assert sorted(actions) == ["s3:GetBucketAcl", "s3:PutBucketAcl"]


# --- Resource scoping ---


class TestAclStatementResources:
    """Verify the ACL grant reaches every v1 logging destination, scoped."""

    def test_covers_account_wide_legacy_bucket(self, acl_statement):
        """The plain account-wide cloudfront-logs-legacy bucket must be covered."""
        resources = flatten_resources(acl_statement["Resource"])
        assert f"arn:aws:s3:::{LEGACY_BUCKET_SUFFIX}" in resources

    def test_covers_org_prefixed_legacy_bucket(self, acl_statement):
        """The S3BucketNameOrgPrefix variant of the legacy bucket must be covered."""
        resources = flatten_resources(acl_statement["Resource"])
        expected = f"arn:aws:s3:::${{S3BucketNameOrgPrefix}}-{LEGACY_BUCKET_SUFFIX}"
        assert expected in resources

    def test_org_prefixed_bucket_is_conditional(self, acl_statement):
        """The org-prefixed ARN must be gated on UseS3BucketNameOrgPrefix."""
        conditional = [
            entry
            for entry in as_list(acl_statement["Resource"])
            if isinstance(entry, dict) and "Fn::If" in entry
        ]
        assert conditional, "Expected an Fn::If-wrapped resource entry"
        assert any(
            entry["Fn::If"][0] == "UseS3BucketNameOrgPrefix" for entry in conditional
        ), "Org-prefixed legacy bucket ARN must use the UseS3BucketNameOrgPrefix condition"

    def test_covers_prefix_namespaced_buckets(self, acl_statement):
        """An explicit S3LogBucketName inside the prefix namespace must be covered."""
        resources = flatten_resources(acl_statement["Resource"])
        assert "arn:aws:s3:::${BucketPrefix}-*" in resources

    def test_prefix_pattern_uses_condition_for_org_prefix(self, acl_statement):
        """The ${BucketPrefix} variable must branch on UseS3BucketNameOrgPrefix."""
        sub_with_vars = [
            entry["Fn::Sub"]
            for entry in as_list(acl_statement["Resource"])
            if isinstance(entry, dict)
            and isinstance(entry.get("Fn::Sub"), list)
        ]
        assert sub_with_vars, "Expected an Fn::Sub with a variable map"
        bucket_prefix = sub_with_vars[0][1]["BucketPrefix"]
        assert bucket_prefix["Fn::If"][0] == "UseS3BucketNameOrgPrefix"
        assert bucket_prefix["Fn::If"][1]["Fn::Sub"] == "${S3BucketNameOrgPrefix}-${Prefix}"
        assert bucket_prefix["Fn::If"][2]["Fn::Sub"] == "${Prefix}"

    def test_resources_are_not_wildcarded(self, acl_statement):
        """PutBucketAcl must never be granted on "*" or on all buckets."""
        resources = flatten_resources(acl_statement["Resource"])
        assert "*" not in resources
        assert "arn:aws:s3:::*" not in resources
        for resource in resources:
            assert resource.startswith("arn:aws:s3:::"), resource


# --- Regression: existing statement untouched ---


class TestExistingLoggingStatementUnchanged:
    """The pre-existing read statement must not have been repurposed."""

    def test_read_statement_still_exists(self, statements):
        """S3BucketReadForLogging must still be present."""
        stmt = find_statement_by_sid(statements, "S3BucketReadForLogging")
        assert stmt is not None, "S3BucketReadForLogging statement not found"

    def test_read_statement_actions_unchanged(self, statements):
        """S3BucketReadForLogging must still grant only the two read actions."""
        stmt = find_statement_by_sid(statements, "S3BucketReadForLogging")
        assert sorted(as_list(stmt["Action"])) == [
            "s3:GetBucketLocation",
            "s3:ListBucket",
        ]
