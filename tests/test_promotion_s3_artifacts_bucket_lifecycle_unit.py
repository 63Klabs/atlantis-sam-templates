"""
Unit tests for the account-wide artifacts bucket lifecycle change (design.md
DD-1 / §7.3, Requirement 12): NoncurrentVersionExpirationInDays raised from
30 to 365 (bucket-wide) while ExpirationInDays (current version) remains at
395, plus the EventBridge notification opt-in and BucketOwnerEnforced
ownership added by this feature.

Validates: Requirements 7.6, 8.1, 12.1, 12.2, 12.3, 19.2, 19.3
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


TEMPLATE_PATH = (
    Path(__file__).parent.parent
    / "templates"
    / "v2"
    / "modules"
    / "account-wide"
    / "s3-artifacts-bucket.yml"
)


@pytest.fixture
def template():
    """Load the account-wide S3 artifacts bucket module."""
    return load_template(TEMPLATE_PATH)


@pytest.fixture
def expire_objects_rule(template):
    rules = template["Properties"]["LifecycleConfiguration"]["Rules"]
    rule = next(r for r in rules if r.get("Id") == "ExpireObjects")
    return rule


class TestLifecycleRetentionValues:
    """Req 12.1, 12.2, 12.3: noncurrent-version retention raised to 365 days;
    current-version expiration unchanged at 395 days."""

    def test_noncurrent_version_expiration_is_365_days(self, expire_objects_rule):
        assert expire_objects_rule["NoncurrentVersionExpirationInDays"] == 365

    def test_current_version_expiration_is_395_days(self, expire_objects_rule):
        assert expire_objects_rule["ExpirationInDays"] == 395

    def test_abort_incomplete_multipart_upload_unchanged(self, expire_objects_rule):
        assert expire_objects_rule["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 1

    def test_rule_status_enabled(self, expire_objects_rule):
        assert expire_objects_rule["Status"] == "Enabled"

    def test_exactly_one_lifecycle_rule(self, template):
        """Req 12.4: no separate promotions/*-scoped rule was added; the
        bucket-wide rule was adjusted in place instead."""
        rules = template["Properties"]["LifecycleConfiguration"]["Rules"]
        assert len(rules) == 1, (
            "Expected exactly one lifecycle rule (bucket-wide ExpireObjects); "
            f"got {len(rules)}"
        )


class TestObjectOwnershipEnforced:
    """Req 7.6 / design §7.2: BucketOwnerEnforced ownership so cross-account
    writes are automatically owned by the receiving account."""

    def test_ownership_controls_present(self, template):
        ownership = template["Properties"]["OwnershipControls"]
        rules = ownership["Rules"]
        assert len(rules) == 1
        assert rules[0]["ObjectOwnership"] == "BucketOwnerEnforced"


class TestEventBridgeOptIn:
    """Req 8.1: EventBridge notifications are opt-in (gated behind
    EnableS3ArtifactsBucketEventBridge), defaulting to no notification
    configuration change for existing deployments."""

    def test_notification_configuration_gated_by_condition(self, template):
        notification_config = template["Properties"]["NotificationConfiguration"]
        assert "!If" in notification_config or "Fn::If" in notification_config
        if_key = "!If" if "!If" in notification_config else "Fn::If"
        cond_name, enabled_value, disabled_value = notification_config[if_key]
        assert cond_name == "EnableS3ArtifactsBucketEventBridge"
        assert enabled_value == {"EventBridgeConfiguration": {"EventBridgeEnabled": True}}

    def test_disabled_branch_is_no_value(self, template):
        notification_config = template["Properties"]["NotificationConfiguration"]
        if_key = "!If" if "!If" in notification_config else "Fn::If"
        _cond, _enabled, disabled_value = notification_config[if_key]
        no_value_key = "!Ref" if "!Ref" in disabled_value else "Ref"
        assert disabled_value[no_value_key] == "AWS::NoValue"
