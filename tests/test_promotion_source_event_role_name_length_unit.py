"""
Unit tests for the rendered IAM RoleName length of
templates/v2/modules/pipeline/promotion-source-event-service-role.yml.

IAM role names have a hard maximum of 64 characters (the role path is a
separate value that does not count toward that limit). This module's RoleName
is built as:

    ${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole

These tests statically resolve the long-form Fn::Sub RoleName AST against the
documented "assumed footprint" (Prefix 6, ProjectId 20, StageId 6 = 32
characters of variable content) and assert the rendered name stays within the
64-character IAM limit (expected exactly 64 at this footprint). A second guard
asserts the static/descriptive suffix stays within the worker-role budget of
22 characters.

Validates: Requirements 1.5, 2.2, 3.1
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template, resolve_longform


MODULES_DIR = Path(__file__).parent.parent / "templates" / "v2" / "modules" / "pipeline"

# The documented "assumed footprint" from the naming length budget:
#   Prefix = 6, ProjectId = 20, StageId = 6  ->  32 chars of variable content.
ASSUMED_PREFIX = "abcdef"                    # 6 chars
ASSUMED_PROJECT_ID = "abcdefghijklmnopqrst"  # 20 chars
ASSUMED_STAGE_ID = "abcdef"                  # 6 chars

# IAM role name hard limit (role path excluded).
IAM_ROLE_NAME_MAX = 64

# Worker-role descriptive suffix budget (see AGENTS.md name-length budget).
WORKER_ROLE_SUFFIX_MAX = 22

# The abbreviated static/descriptive suffix chosen for this role.
EXPECTED_SUFFIX = "PromoteSrcEventSvcRole"


@pytest.fixture
def promotion_source_event_service_role():
    return load_template(MODULES_DIR / "promotion-source-event-service-role.yml")


class TestRenderedRoleNameLength:
    """The rendered RoleName must fit within the 64-character IAM role name
    limit at the assumed footprint."""

    def test_footprint_fixtures_have_expected_lengths(self):
        # Guard the assumptions the length math depends on.
        assert len(ASSUMED_PREFIX) == 6
        assert len(ASSUMED_PROJECT_ID) == 20
        assert len(ASSUMED_STAGE_ID) == 6

    def test_rendered_role_name_within_iam_limit(self, promotion_source_event_service_role):
        role_name_node = promotion_source_event_service_role["Properties"]["RoleName"]

        refs = {
            "Prefix": ASSUMED_PREFIX,
            "ProjectId": ASSUMED_PROJECT_ID,
            "StageId": ASSUMED_STAGE_ID,
        }
        # RoleName is a plain Fn::Sub with no Fn::If, so no conditions are needed.
        rendered = resolve_longform(role_name_node, {}, refs)

        assert rendered == (
            f"{ASSUMED_PREFIX}-Worker-{ASSUMED_PROJECT_ID}-{ASSUMED_STAGE_ID}-{EXPECTED_SUFFIX}"
        ), f"unexpected rendered role name: {rendered}"

        assert len(rendered) <= IAM_ROLE_NAME_MAX, (
            f"rendered role name is {len(rendered)} chars (> {IAM_ROLE_NAME_MAX}): {rendered}"
        )
        # At the assumed footprint the name should land exactly at the boundary.
        assert len(rendered) == 64, (
            f"expected exactly 64 chars at the assumed footprint, got {len(rendered)}: {rendered}"
        )


class TestSuffixBudgetGuard:
    """The static/descriptive suffix must stay within the worker-role budget."""

    def test_suffix_within_worker_role_budget(self, promotion_source_event_service_role):
        role_name_node = promotion_source_event_service_role["Properties"]["RoleName"]
        sub_template = role_name_node["Fn::Sub"]

        # The suffix is the static text after the final "-${StageId}-" segment.
        marker = "-${StageId}-"
        assert marker in sub_template, f"unexpected RoleName template: {sub_template}"
        suffix = sub_template.split(marker, 1)[1]

        assert suffix == EXPECTED_SUFFIX, f"unexpected suffix: {suffix}"
        assert len(suffix) <= WORKER_ROLE_SUFFIX_MAX, (
            f"suffix '{suffix}' is {len(suffix)} chars (> {WORKER_ROLE_SUFFIX_MAX})"
        )
