"""
Unit tests for the target-bucket derivation logic shared by
templates/v2/modules/pipeline/promote-service-role.yml (IAM resource ARN) and
templates/v2/modules/pipeline/promote-project.yml (PROMOTE_TARGET_BUCKET env var).

Both modules implement the same design-§5.3 formula:

    PROMOTE_TARGET_BUCKET =
      HasPromoteTargetBucket ? PromoteTargetBucket
      : UseS3BucketNameOrgPrefix
          ? "${S3BucketNameOrgPrefix}-cf-artifacts-${TargetAccount}-${TargetRegion}-an"
          : "cf-artifacts-${TargetAccount}-${TargetRegion}-an"
    where TargetAccount = HasPromoteTargetAccount ? PromoteTargetAccountId : AWS::AccountId
          TargetRegion  = HasPromoteTargetRegion  ? PromoteTargetRegion    : AWS::Region

These tests statically resolve the long-form Fn::If / Fn::Sub / Ref ASTs in
each module against a matrix of org-prefix x same/cross account x
same/cross region scenarios and assert the resolved bucket name (or ARN
suffix) matches the expected derivation.

Validates: Requirements 10.5, 19.2, 19.3
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template, resolve_longform


MODULES_DIR = Path(__file__).parent.parent / "templates" / "v2" / "modules" / "pipeline"

CURRENT_ACCOUNT_ID = "111111111111"
CURRENT_REGION = "us-east-1"


# Each scenario: (label, refs, conditions, expected_bucket_name)
# refs: Ref/pseudo-parameter values used by the module.
# conditions: precomputed booleans for the module's Fn::If conditions.
SCENARIOS = [
    (
        "no-org-prefix_same-account_same-region",
        {
            "S3BucketNameOrgPrefix": "",
            "PromoteTargetAccountId": "",
            "PromoteTargetRegion": "",
            "PromoteTargetBucket": "",
            "AWS::AccountId": CURRENT_ACCOUNT_ID,
            "AWS::Region": CURRENT_REGION,
        },
        {
            "HasPromoteTargetBucket": False,
            "UseS3BucketNameOrgPrefix": False,
            "HasPromoteTargetAccount": False,
            "HasPromoteTargetRegion": False,
        },
        f"cf-artifacts-{CURRENT_ACCOUNT_ID}-{CURRENT_REGION}-an",
    ),
    (
        "org-prefix_same-account_same-region",
        {
            "S3BucketNameOrgPrefix": "acme",
            "PromoteTargetAccountId": "",
            "PromoteTargetRegion": "",
            "PromoteTargetBucket": "",
            "AWS::AccountId": CURRENT_ACCOUNT_ID,
            "AWS::Region": CURRENT_REGION,
        },
        {
            "HasPromoteTargetBucket": False,
            "UseS3BucketNameOrgPrefix": True,
            "HasPromoteTargetAccount": False,
            "HasPromoteTargetRegion": False,
        },
        f"acme-cf-artifacts-{CURRENT_ACCOUNT_ID}-{CURRENT_REGION}-an",
    ),
    (
        "no-org-prefix_cross-account_same-region",
        {
            "S3BucketNameOrgPrefix": "",
            "PromoteTargetAccountId": "222222222222",
            "PromoteTargetRegion": "",
            "PromoteTargetBucket": "",
            "AWS::AccountId": CURRENT_ACCOUNT_ID,
            "AWS::Region": CURRENT_REGION,
        },
        {
            "HasPromoteTargetBucket": False,
            "UseS3BucketNameOrgPrefix": False,
            "HasPromoteTargetAccount": True,
            "HasPromoteTargetRegion": False,
        },
        f"cf-artifacts-222222222222-{CURRENT_REGION}-an",
    ),
    (
        "org-prefix_cross-account_cross-region",
        {
            "S3BucketNameOrgPrefix": "acme",
            "PromoteTargetAccountId": "222222222222",
            "PromoteTargetRegion": "eu-west-1",
            "PromoteTargetBucket": "",
            "AWS::AccountId": CURRENT_ACCOUNT_ID,
            "AWS::Region": CURRENT_REGION,
        },
        {
            "HasPromoteTargetBucket": False,
            "UseS3BucketNameOrgPrefix": True,
            "HasPromoteTargetAccount": True,
            "HasPromoteTargetRegion": True,
        },
        "acme-cf-artifacts-222222222222-eu-west-1-an",
    ),
    (
        "explicit-target-bucket-overrides-derivation",
        {
            "S3BucketNameOrgPrefix": "acme",
            "PromoteTargetAccountId": "222222222222",
            "PromoteTargetRegion": "eu-west-1",
            "PromoteTargetBucket": "custom-explicit-bucket",
            "AWS::AccountId": CURRENT_ACCOUNT_ID,
            "AWS::Region": CURRENT_REGION,
        },
        {
            "HasPromoteTargetBucket": True,
            "UseS3BucketNameOrgPrefix": True,
            "HasPromoteTargetAccount": True,
            "HasPromoteTargetRegion": True,
        },
        "custom-explicit-bucket",
    ),
]


@pytest.fixture
def promote_service_role():
    return load_template(MODULES_DIR / "promote-service-role.yml")


@pytest.fixture
def promote_project():
    return load_template(MODULES_DIR / "promote-project.yml")


class TestPromoteServiceRoleTargetBucketArn:
    """The WritePromotionToTarget statement's Resource ARN must resolve to
    <derived-bucket>/promotions/* for each scenario."""

    @pytest.mark.parametrize("label,refs,conditions,expected_bucket", SCENARIOS, ids=[s[0] for s in SCENARIOS])
    def test_resolved_arn_matches_expected_bucket(self, promote_service_role, label, refs, conditions, expected_bucket):
        statements = promote_service_role["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
        write_stmt = next(s for s in statements if s["Sid"] == "WritePromotionToTarget")
        resource_node = write_stmt["Resource"]

        resolved = resolve_longform(resource_node, conditions, refs)
        expected_arn = f"arn:aws:s3:::{expected_bucket}/promotions/*"
        assert resolved == expected_arn, f"[{label}] expected {expected_arn}, got {resolved}"


class TestPromoteProjectTargetBucketEnvVar:
    """The PROMOTE_TARGET_BUCKET CodeBuild environment variable must resolve
    to the same derived bucket name for each scenario."""

    @pytest.mark.parametrize("label,refs,conditions,expected_bucket", SCENARIOS, ids=[s[0] for s in SCENARIOS])
    def test_resolved_env_var_matches_expected_bucket(self, promote_project, label, refs, conditions, expected_bucket):
        env_vars = promote_project["Properties"]["Environment"]["EnvironmentVariables"]
        target_bucket_var = next(v for v in env_vars if v["Name"] == "PROMOTE_TARGET_BUCKET")

        resolved = resolve_longform(target_bucket_var["Value"], conditions, refs)
        assert resolved == expected_bucket, f"[{label}] expected {expected_bucket}, got {resolved}"


class TestPromoteProjectTargetAccountAndRegionEnvVars:
    """PROMOTE_TARGET_ACCOUNT_ID / PROMOTE_TARGET_REGION should resolve to
    the target values (or fall back to the current account/region)."""

    @pytest.mark.parametrize(
        "label,refs,conditions,_expected_bucket",
        SCENARIOS,
        ids=[s[0] for s in SCENARIOS],
    )
    def test_target_account_id_env_var(self, promote_project, label, refs, conditions, _expected_bucket):
        env_vars = promote_project["Properties"]["Environment"]["EnvironmentVariables"]
        var = next(v for v in env_vars if v["Name"] == "PROMOTE_TARGET_ACCOUNT_ID")
        resolved = resolve_longform(var["Value"], conditions, refs)

        expected = refs["PromoteTargetAccountId"] if conditions["HasPromoteTargetAccount"] else refs["AWS::AccountId"]
        assert resolved == expected, f"[{label}] expected account {expected}, got {resolved}"

    @pytest.mark.parametrize(
        "label,refs,conditions,_expected_bucket",
        SCENARIOS,
        ids=[s[0] for s in SCENARIOS],
    )
    def test_target_region_env_var(self, promote_project, label, refs, conditions, _expected_bucket):
        env_vars = promote_project["Properties"]["Environment"]["EnvironmentVariables"]
        var = next(v for v in env_vars if v["Name"] == "PROMOTE_TARGET_REGION")
        resolved = resolve_longform(var["Value"], conditions, refs)

        expected = refs["PromoteTargetRegion"] if conditions["HasPromoteTargetRegion"] else refs["AWS::Region"]
        assert resolved == expected, f"[{label}] expected region {expected}, got {resolved}"
