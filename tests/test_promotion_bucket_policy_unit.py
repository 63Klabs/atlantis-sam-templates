"""
Unit tests for the cross-account promotion write statement
(AllowCrossAccountPromotionWrite) added to
templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml.

Covers Requirement 7 (empty PromotionSourceAccountIds omits the statement
entirely; non-empty renders it scoped to promotions/* and the
*-PromoteServiceRole principal condition).

Validates: Requirements 7.2, 7.3, 7.4, 7.5, 19.2, 19.3
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
    / "s3-artifacts-bucket-policy.yml"
)


@pytest.fixture
def template():
    """Load the S3 artifacts bucket policy module."""
    return load_template(TEMPLATE_PATH)


@pytest.fixture
def statements(template):
    return template["Properties"]["PolicyDocument"]["Statement"]


def _find_cross_account_statement_node(statements):
    """Return the raw (un-evaluated) Fn::If node wrapping the
    AllowCrossAccountPromotionWrite statement, if present."""
    for stmt in statements:
        if isinstance(stmt, dict) and "Fn::If" in stmt:
            cond_name, true_branch, _false_branch = stmt["Fn::If"]
            if isinstance(true_branch, dict) and true_branch.get("Sid") == "AllowCrossAccountPromotionWrite":
                return cond_name, true_branch
    return None, None


class TestStatementGatedByCondition:
    """Req 7.2: the statement is wrapped in Fn::If[HasPromotionSourceAccounts, ...]
    so that when the condition is false, it resolves to AWS::NoValue and the
    existing (pre-feature) statement list is otherwise unaffected."""

    def test_cross_account_statement_wrapped_in_fn_if(self, statements):
        cond_name, branch = _find_cross_account_statement_node(statements)
        assert cond_name is not None, "AllowCrossAccountPromotionWrite statement not found wrapped in Fn::If"
        assert cond_name == "HasPromotionSourceAccounts"

    def test_false_branch_is_no_value(self, statements):
        for stmt in statements:
            if isinstance(stmt, dict) and "Fn::If" in stmt:
                _cond, true_branch, false_branch = stmt["Fn::If"]
                if isinstance(true_branch, dict) and true_branch.get("Sid") == "AllowCrossAccountPromotionWrite":
                    assert false_branch == {"Ref": "AWS::NoValue"}
                    return
        pytest.fail("AllowCrossAccountPromotionWrite Fn::If node not found")

    def test_base_three_statements_still_present(self, statements):
        """Pre-existing statements (Deny/WhitelistedGet/WhitelistedPut) are
        untouched; the new statement is purely additive."""
        sids = []
        for stmt in statements:
            if isinstance(stmt, dict) and "Sid" in stmt:
                sids.append(stmt["Sid"])
        assert "DenyNonSecureTransportAccess" in sids
        assert "WhitelistedGet" in sids
        assert "WhitelistedPut" in sids


class TestCrossAccountStatementContent:
    """Req 7.3, 7.4, 7.5: when rendered, the statement grants exactly the
    documented actions, is scoped to promotions/* only, and its principal
    condition matches *-PromoteServiceRole."""

    @pytest.fixture
    def branch(self, statements):
        _cond, branch = _find_cross_account_statement_node(statements)
        assert branch is not None
        return branch

    def test_effect_is_allow(self, branch):
        assert branch["Effect"] == "Allow"

    def test_principal_aws_references_promotion_source_account_ids(self, branch):
        principal = branch["Principal"]
        assert principal == {"AWS": {"Ref": "PromotionSourceAccountIds"}}

    def test_actions_are_exactly_put_get_getversion(self, branch):
        expected_actions = ["s3:PutObject", "s3:GetObject", "s3:GetObjectVersion"]
        assert branch["Action"] == expected_actions

    def test_resource_is_scoped_to_promotions_prefix_only(self, branch):
        resource = branch["Resource"]
        assert isinstance(resource, list)
        assert len(resource) == 1, "Resource should be scoped to a single promotions/* ARN pattern"
        sub_value = resource[0]["Fn::Sub"]
        assert sub_value == "${S3ArtifactsBucketRegional.Arn}/promotions/*"
        # Ensure no bucket-root or wildcard-beyond-promotions access is granted.
        assert "promotions/*" in sub_value
        assert sub_value.count("/") == 2  # "<bucket-arn>/promotions/*" - no extra path segments implied

    def test_condition_matches_promote_service_role_suffix(self, branch):
        condition = branch["Condition"]
        assert "StringLike" in condition
        principal_arn_pattern = condition["StringLike"]["aws:PrincipalArn"]
        assert principal_arn_pattern == "arn:aws:iam::*:role/*-PromoteServiceRole"

    def test_condition_does_not_match_other_role_types(self, branch):
        """The pattern should be suffix-scoped to *-PromoteServiceRole and not
        match unrelated role name suffixes."""
        import fnmatch

        condition = branch["Condition"]
        pattern = condition["StringLike"]["aws:PrincipalArn"]
        # Strip the "arn:aws:iam::*:role/" prefix for fnmatch against role names.
        role_glob = pattern.split(":role/")[-1]

        matching_role = "acme-Worker-myapp-test-PromoteServiceRole"
        non_matching_role = "acme-Worker-myapp-test-CodeBuildServiceRole"

        assert fnmatch.fnmatch(matching_role, role_glob), (
            f"Pattern '{role_glob}' should match a real PromoteServiceRole name"
        )
        assert not fnmatch.fnmatch(non_matching_role, role_glob), (
            f"Pattern '{role_glob}' should NOT match a CodeBuildServiceRole name"
        )
