"""
Unit tests for the Promote / ApproveToPromote stage composition on the three
origin ("send") pipeline templates: template-pipeline.yml,
template-pipeline-github.yml, and template-pipeline-build-only.yml.

Fast, concrete unit tests (no property-based testing) per the repository's
testing guidelines. Statically evaluates the ProjectPipeline Stages list
against a small set of parameter scenarios using the short-form condition
evaluator in cfn_test_utils.

Validates: Requirements 3.7, 19.2, 19.3 (design.md Correctness Properties 1-2)
"""

import sys
import os
from pathlib import Path

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template, get_included_stage_names


TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "v2" / "pipeline"

TEMPLATE_FILES = [
    "template-pipeline.yml",
    "template-pipeline-github.yml",
    "template-pipeline-build-only.yml",
]

# Baseline parameter defaults shared by every scenario; only the promotion
# parameters vary per test. These match each template's actual Default
# values so "defaults" scenarios are a faithful backward-compatibility check.
BASE_PARAMS = {
    "DeployEnvironment": "PROD",
    "S3BucketNameOrgPrefix": "",
    "PermissionsBoundaryArn": "",
    "BuildSpec": "application-infrastructure/buildspec.yml",
    "PostDeployStageEnabled": "false",
    "PostDeployBuildSpec": "application-infrastructure/buildspec-postdeploy.yml",
    "CodeBuildSvcRoleIncludeManagedPolicyArns": "",
    "PostDeploySvcRoleIncludeManagedPolicyArns": "",
    "CloudFormationSvcRoleIncludeManagedPolicyArns": "",
    # Promotion parameters at their documented defaults (disabled)
    "PromoteTargetStageId": "",
    "PromoteApprovalRequired": "true",
    "PromoteTargetAccountId": "",
    "PromoteTargetRegion": "",
    "PromoteTargetBucket": "",
}


@pytest.fixture(params=TEMPLATE_FILES, ids=TEMPLATE_FILES)
def pipeline_template(request):
    """Load each origin pipeline template as a parameterized fixture."""
    return load_template(TEMPLATE_DIR / request.param)


def _stage_names(template, params):
    """Resolve the ordered list of included stage Names for given params."""
    stages = template["Resources"]["ProjectPipeline"]["Properties"]["Stages"]
    conditions = template["Conditions"]
    return get_included_stage_names(stages, conditions, params)


class TestDefaultsProduceNoPromotionStages:
    """Req 3.7 / Correctness Property 1: all promotion params at their
    defaults => no Promote or ApproveToPromote stage is present."""

    def test_no_promote_stage_at_defaults(self, pipeline_template):
        names = _stage_names(pipeline_template, BASE_PARAMS)
        assert "Promote" not in names, f"Promote stage should be absent at defaults, got stages: {names}"

    def test_no_approve_to_promote_stage_at_defaults(self, pipeline_template):
        names = _stage_names(pipeline_template, BASE_PARAMS)
        assert "ApproveToPromote" not in names, (
            f"ApproveToPromote stage should be absent at defaults, got stages: {names}"
        )

    def test_source_and_build_stages_still_present(self, pipeline_template):
        """Sanity check: the base pipeline stages are unaffected."""
        names = _stage_names(pipeline_template, BASE_PARAMS)
        assert names[0] == "Source"
        assert "Build" in names


class TestPromoteEnabledWithApprovalRequired:
    """Req 3.2, 3.3 / Correctness Property 2: PromoteTargetStageId set and
    PromoteApprovalRequired=true => both ApproveToPromote and Promote appear,
    in that order."""

    @pytest.fixture
    def params(self):
        p = dict(BASE_PARAMS)
        p["PromoteTargetStageId"] = "beta"
        p["PromoteApprovalRequired"] = "true"
        return p

    def test_both_stages_present(self, pipeline_template, params):
        names = _stage_names(pipeline_template, params)
        assert "ApproveToPromote" in names, f"ApproveToPromote should be present, got: {names}"
        assert "Promote" in names, f"Promote should be present, got: {names}"

    def test_approve_to_promote_precedes_promote(self, pipeline_template, params):
        names = _stage_names(pipeline_template, params)
        assert names.index("ApproveToPromote") < names.index("Promote"), (
            f"ApproveToPromote must precede Promote, got order: {names}"
        )


class TestPromoteEnabledWithoutApprovalRequired:
    """Req 3.4 / Correctness Property 2: PromoteApprovalRequired=false =>
    only the Promote stage is present (no ApproveToPromote gate)."""

    @pytest.fixture
    def params(self):
        p = dict(BASE_PARAMS)
        p["PromoteTargetStageId"] = "beta"
        p["PromoteApprovalRequired"] = "false"
        return p

    def test_promote_stage_present(self, pipeline_template, params):
        names = _stage_names(pipeline_template, params)
        assert "Promote" in names, f"Promote should be present, got: {names}"

    def test_approve_to_promote_absent(self, pipeline_template, params):
        names = _stage_names(pipeline_template, params)
        assert "ApproveToPromote" not in names, (
            f"ApproveToPromote should be absent when PromoteApprovalRequired=false, got: {names}"
        )


class TestStageOrderPerTemplateType:
    """Req 3.5, 3.6: verify overall stage order for each origin template
    family with promotion enabled and approval required."""

    @pytest.fixture
    def params(self):
        p = dict(BASE_PARAMS)
        p["PromoteTargetStageId"] = "beta"
        p["PromoteApprovalRequired"] = "true"
        return p

    def test_build_only_stage_order(self, params):
        """template-pipeline-build-only.yml: Source -> Build -> ApproveToPromote -> Promote."""
        template = load_template(TEMPLATE_DIR / "template-pipeline-build-only.yml")
        names = _stage_names(template, params)
        assert names == ["Source", "Build", "ApproveToPromote", "Promote"]

    @pytest.mark.parametrize(
        "template_file",
        ["template-pipeline.yml", "template-pipeline-github.yml"],
    )
    def test_full_deploy_stage_order(self, template_file, params):
        """Full pipelines: Source -> Build -> Deploy -> [PostDeploy] -> ApproveToPromote -> Promote."""
        template = load_template(TEMPLATE_DIR / template_file)
        names = _stage_names(template, params)
        assert names == ["Source", "Build", "Deploy", "ApproveToPromote", "Promote"]

    @pytest.mark.parametrize(
        "template_file",
        ["template-pipeline.yml", "template-pipeline-github.yml"],
    )
    def test_full_deploy_stage_order_with_postdeploy(self, template_file, params):
        """With PostDeploy enabled: Source -> Build -> Deploy -> PostDeploy -> ApproveToPromote -> Promote."""
        template = load_template(TEMPLATE_DIR / template_file)
        p = dict(params)
        p["PostDeployStageEnabled"] = "true"
        names = _stage_names(template, p)
        assert names == ["Source", "Build", "Deploy", "PostDeploy", "ApproveToPromote", "Promote"]
