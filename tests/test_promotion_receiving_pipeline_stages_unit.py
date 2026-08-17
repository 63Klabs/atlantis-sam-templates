"""
Unit tests for the receiving (promoted-artifact) pipeline template's stage
composition: template-pipeline-promoted-artifact.yml.

Fast, concrete unit tests covering the ApproveRelease and Deploy stage gates
(ReleaseApprovalRequired, DeployStageEnabled) plus the chained
ApproveToPromote/Promote stages (shared logic with the origin templates).

Validates: Requirements 5.2, 5.3, 19.2, 19.3 (design.md Correctness Property 2)
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template, get_included_stage_names


TEMPLATE_PATH = (
    Path(__file__).parent.parent
    / "templates"
    / "v2"
    / "pipeline"
    / "template-pipeline-promoted-artifact.yml"
)

BASE_PARAMS = {
    "DeployEnvironment": "PROD",
    "S3BucketNameOrgPrefix": "",
    "PermissionsBoundaryArn": "",
    "BuildSpec": "application-infrastructure/buildspec.yml",
    "ReleaseApprovalRequired": "true",
    "DeployStageEnabled": "true",
    "PostDeployStageEnabled": "false",
    "PostDeployBuildSpec": "application-infrastructure/buildspec-postdeploy.yml",
    "CodeBuildSvcRoleIncludeManagedPolicyArns": "",
    "PostDeploySvcRoleIncludeManagedPolicyArns": "",
    "CloudFormationSvcRoleIncludeManagedPolicyArns": "",
    "PromoteTargetStageId": "",
    "PromoteApprovalRequired": "true",
    "PromoteTargetAccountId": "",
    "PromoteTargetRegion": "",
    "PromoteTargetBucket": "",
}


@pytest.fixture
def template():
    """Load the receiving (promoted-artifact) pipeline template."""
    return load_template(TEMPLATE_PATH)


def _stage_names(template, params):
    stages = template["Resources"]["ProjectPipeline"]["Properties"]["Stages"]
    conditions = template["Conditions"]
    return get_included_stage_names(stages, conditions, params)


class TestDefaultsIncludeReleaseApprovalAndDeploy:
    """At documented defaults, ReleaseApprovalRequired=true and
    DeployStageEnabled=true, so ApproveRelease and Deploy are both present."""

    def test_default_stage_order(self, template):
        names = _stage_names(template, BASE_PARAMS)
        assert names == ["Source", "ApproveRelease", "Build", "Deploy"]


class TestReleaseApprovalRequiredFalse:
    """Req 5.3: ReleaseApprovalRequired=false => no ApproveRelease stage,
    Source flows directly into Build."""

    @pytest.fixture
    def params(self):
        p = dict(BASE_PARAMS)
        p["ReleaseApprovalRequired"] = "false"
        return p

    def test_approve_release_absent(self, template, params):
        names = _stage_names(template, params)
        assert "ApproveRelease" not in names, f"ApproveRelease should be absent, got: {names}"

    def test_source_directly_precedes_build(self, template, params):
        names = _stage_names(template, params)
        assert names.index("Source") == names.index("Build") - 1, (
            f"Source should directly precede Build when release approval is off, got: {names}"
        )


class TestReleaseApprovalRequiredTrue:
    """Req 5.2: ReleaseApprovalRequired=true => ApproveRelease appears
    between Source and Build."""

    def test_approve_release_present_between_source_and_build(self, template):
        names = _stage_names(template, BASE_PARAMS)
        assert names.index("Source") < names.index("ApproveRelease") < names.index("Build"), (
            f"ApproveRelease must sit strictly between Source and Build, got: {names}"
        )


class TestDeployStageEnabledFalse:
    """Req 4.4: DeployStageEnabled=false => no Deploy stage (build-only-style
    receiving workload)."""

    @pytest.fixture
    def params(self):
        p = dict(BASE_PARAMS)
        p["DeployStageEnabled"] = "false"
        return p

    def test_deploy_stage_absent(self, template, params):
        names = _stage_names(template, params)
        assert "Deploy" not in names, f"Deploy stage should be absent, got: {names}"

    def test_remaining_stages_present(self, template, params):
        names = _stage_names(template, params)
        assert names == ["Source", "ApproveRelease", "Build"]


class TestChainedPromotionStages:
    """Chained promotion (ApproveToPromote/Promote) mirrors the origin
    template logic and composes correctly with the receiving-side gates."""

    @pytest.fixture
    def params(self):
        p = dict(BASE_PARAMS)
        p["PromoteTargetStageId"] = "prod"
        p["PromoteApprovalRequired"] = "true"
        return p

    def test_chained_stages_present_and_ordered_last(self, template, params):
        names = _stage_names(template, params)
        assert names == [
            "Source",
            "ApproveRelease",
            "Build",
            "Deploy",
            "ApproveToPromote",
            "Promote",
        ]

    def test_chained_promote_without_approval(self, template, params):
        p = dict(params)
        p["PromoteApprovalRequired"] = "false"
        names = _stage_names(template, p)
        assert "ApproveToPromote" not in names
        assert names[-1] == "Promote"

    def test_fully_disabled_gates_minimal_pipeline(self, template):
        """Both release and promote approval off, deploy disabled, promotion
        disabled: only Source -> Build remain (fully ungated build-only)."""
        p = dict(BASE_PARAMS)
        p["ReleaseApprovalRequired"] = "false"
        p["DeployStageEnabled"] = "false"
        names = _stage_names(template, p)
        assert names == ["Source", "Build"]


class TestSourceStageIsS3:
    """Req 4.2, 4.7: the receiving pipeline's Source stage reads from S3
    (the shared S3ArtifactsBucket), not CodeCommit/GitHub."""

    def test_source_action_provider_is_s3(self, template):
        source_stage = template["Resources"]["ProjectPipeline"]["Properties"]["Stages"][0]
        action = source_stage["Actions"][0]
        assert action["ActionTypeId"]["Provider"] == "S3"
        assert action["ActionTypeId"]["Category"] == "Source"

    def test_source_object_key_uses_stage_id_not_promote_target(self, template):
        """The receiving pipeline watches its OWN StageId (design §5.2),
        not a PromoteTarget* parameter."""
        source_stage = template["Resources"]["ProjectPipeline"]["Properties"]["Stages"][0]
        action = source_stage["Actions"][0]
        key_sub = action["Configuration"]["S3ObjectKey"]
        key_template = key_sub.get("!Sub") or key_sub.get("Fn::Sub")
        assert key_template == "promotions/${Prefix}-${ProjectId}/${StageId}/source.zip"

    def test_artifact_store_uses_same_s3_artifacts_bucket_param(self, template):
        """Req 4.7: a single S3ArtifactsBucket parameter serves both the S3
        Source location and the CodePipeline ArtifactStore."""
        pipeline_props = template["Resources"]["ProjectPipeline"]["Properties"]
        artifact_store_location = pipeline_props["ArtifactStore"]["Location"]
        artifact_store_ref = artifact_store_location.get("!Ref") or artifact_store_location.get("Ref")
        assert artifact_store_ref == "S3ArtifactsBucket"

        source_stage = pipeline_props["Stages"][0]
        action = source_stage["Actions"][0]
        s3_bucket_ref_node = action["Configuration"]["S3Bucket"]
        s3_bucket_ref = s3_bucket_ref_node.get("!Ref") or s3_bucket_ref_node.get("Ref")
        assert s3_bucket_ref == "S3ArtifactsBucket"

        # Confirm there is no separate promotion-source bucket parameter.
        assert "PromotionSourceBucket" not in template.get("Parameters", {})
