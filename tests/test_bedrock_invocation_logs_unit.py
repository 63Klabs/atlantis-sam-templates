"""
Unit tests for the Bedrock model invocation logging feature added to:
  - templates/v2/account/account-wide-infrastructure.yml  (Tasks 7.1)
  - templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml  (Task 7.2)
  - templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml  (Task 7.3)

Also covers:
  - Cross-module log-group path consistency  (Task 7.4)
  - Module hygiene (no shorthand intrinsics, contract comments)  (Task 7.5)
  - Admin-ops documentation existence checks  (Task 7.5)

Validates: Requirements 1, 2, 3, 4, 5, 6, 7, 8, 9, 10.13, 12, 15
"""

import json
import re
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent

PARENT_TEMPLATE = PROJECT_ROOT / "templates" / "v2" / "account" / "account-wide-infrastructure.yml"
LOG_GROUP_MODULE = PROJECT_ROOT / "templates" / "v2" / "modules" / "account-wide" / "bedrock-cloudwatch-log-group.yml"
ROLE_MODULE = PROJECT_ROOT / "templates" / "v2" / "modules" / "account-wide" / "bedrock-cloudwatch-role.yml"

ADMIN_OPS_DOC = PROJECT_ROOT / "docs" / "admin-ops" / "bedrock-model-invocation-logging.md"
ACCOUNT_MGMT_DOC = PROJECT_ROOT / "docs" / "admin-ops" / "account-management.md"

# Exact 22-value set that CloudWatch Logs RetentionInDays accepts.
CW_LOGS_RETENTION_VALUES = [
    1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180,
    365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653,
]

# Shorthand intrinsic tags that must NOT appear in module files.
SHORTHAND_TAGS = ["!Sub", "!Ref", "!GetAtt", "!If", "!Join", "!Not", "!Equals"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def parent():
    return load_template(PARENT_TEMPLATE)


@pytest.fixture(scope="module")
def log_group_module():
    return load_template(LOG_GROUP_MODULE)


@pytest.fixture(scope="module")
def role_module():
    return load_template(ROLE_MODULE)


@pytest.fixture(scope="module")
def parent_raw():
    return PARENT_TEMPLATE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def log_group_module_raw():
    return LOG_GROUP_MODULE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def role_module_raw():
    return ROLE_MODULE.read_text(encoding="utf-8")


# ===========================================================================
# TASK 7.1 — Parent template assertions
# ===========================================================================

class TestParentTemplateVersion:
    """Req 12.1, 12.3 — version line is v2.1.0 (bumped for v0.0.44 media logging)."""

    def test_version_line_is_v2_1_0(self, parent_raw):
        assert "# Version: v2.1.0/" in parent_raw, (
            "Header '# Version:' line must read v2.1.0/..."
        )


class TestEnableBedrockInvocationLogsParameter:
    """Req 1.1, 1.2, 1.3 — EnableBedrockInvocationLogs parameter."""

    @pytest.fixture
    def param(self, parent):
        params = parent.get("Parameters", {})
        assert "EnableBedrockInvocationLogs" in params, (
            "EnableBedrockInvocationLogs parameter must exist"
        )
        return params["EnableBedrockInvocationLogs"]

    def test_type_is_string(self, param):
        assert param["Type"] == "String"

    def test_default_is_false(self, param):
        # v0.0.44 (spec 0-0-44-bedrock-invocation-logs-default-off, R1.1) flipped the
        # default from "true" to "false" so the Bedrock logging infrastructure is opt-in.
        assert param["Default"] == "false"

    def test_allowed_values_are_true_false(self, param):
        assert param["AllowedValues"] == ["true", "false"]

    def test_constraint_description_present(self, param):
        assert "ConstraintDescription" in param
        assert param["ConstraintDescription"]

    def test_description_mentions_post_deploy_step(self, param):
        desc = param.get("Description", "")
        assert "post" in desc.lower() or "manual" in desc.lower() or "cli" in desc.lower() or "activation" in desc.lower(), (
            "Description must mention the post-deployment activation requirement"
        )


class TestBedrockInvocationLogExpirationInDaysParameter:
    """Req 2.1, 2.2, 2.3, 2.4, 2.5 — BedrockInvocationLogExpirationInDays parameter."""

    @pytest.fixture
    def param(self, parent):
        params = parent.get("Parameters", {})
        assert "BedrockInvocationLogExpirationInDays" in params
        return params["BedrockInvocationLogExpirationInDays"]

    def test_type_is_number(self, param):
        assert param["Type"] == "Number"

    def test_default_is_180(self, param):
        assert param["Default"] == 180

    def test_allowed_values_equals_cw_enumeration(self, param):
        assert "AllowedValues" in param, "Must use AllowedValues (not MinValue/MaxValue)"
        assert param["AllowedValues"] == CW_LOGS_RETENTION_VALUES

    def test_no_min_value_key(self, param):
        assert "MinValue" not in param, "Must use AllowedValues, not MinValue"

    def test_no_max_value_key(self, param):
        assert "MaxValue" not in param, "Must use AllowedValues, not MaxValue"

    def test_default_is_member_of_allowed_values(self, param):
        assert param["Default"] in param["AllowedValues"], (
            "Default (180) must be a member of AllowedValues"
        )

    def test_constraint_description_present(self, param):
        assert "ConstraintDescription" in param
        assert param["ConstraintDescription"]


class TestBedrockInvocationLogKmsKeyArnParameter:
    """Req 3.1, 3.2, 3.6, 3.7 — BedrockInvocationLogKmsKeyArn parameter."""

    @pytest.fixture
    def param(self, parent):
        params = parent.get("Parameters", {})
        assert "BedrockInvocationLogKmsKeyArn" in params
        return params["BedrockInvocationLogKmsKeyArn"]

    def test_type_is_string(self, param):
        assert param["Type"] == "String"

    def test_default_is_empty_string(self, param):
        assert param["Default"] == ""

    def test_max_length_is_256(self, param):
        assert param.get("MaxLength") == 256

    def test_no_min_length_key(self, param):
        assert "MinLength" not in param, (
            "MinLength must be omitted so the empty default validates"
        )

    def test_allowed_pattern_accepts_empty(self, param):
        pattern = param.get("AllowedPattern", "")
        assert "|^$" in pattern or pattern.endswith("|^$"), (
            "AllowedPattern must include |^$ alternative to accept empty string"
        )

    def test_description_mentions_symmetric_key(self, param):
        desc = param.get("Description", "")
        assert "symmetric" in desc.lower()

    def test_description_mentions_logs_service_principal(self, param):
        desc = param.get("Description", "")
        assert "logs." in desc


class TestParentTemplateConditions:
    """Req 1.4, 3.3 — two new conditions exist."""

    @pytest.fixture
    def conditions(self, parent):
        return parent.get("Conditions", {})

    def test_enable_bedrock_invocation_logs_condition_exists(self, conditions):
        assert "EnableBedrockInvocationLogs" in conditions

    def test_has_bedrock_kms_key_condition_exists(self, conditions):
        assert "HasBedrockInvocationLogKmsKey" in conditions

    def test_enable_bedrock_condition_checks_parameter(self, conditions):
        cond = conditions["EnableBedrockInvocationLogs"]
        cond_str = str(cond)
        assert "EnableBedrockInvocationLogs" in cond_str
        assert "true" in cond_str

    def test_kms_key_condition_checks_kms_param(self, conditions):
        cond = conditions["HasBedrockInvocationLogKmsKey"]
        cond_str = str(cond)
        assert "BedrockInvocationLogKmsKeyArn" in cond_str


class TestParentMetadataGroup:
    """Req 4.1, 4.2, 4.3, 4.4 — metadata parameter group."""

    @pytest.fixture
    def groups(self, parent):
        return (
            parent.get("Metadata", {})
            .get("AWS::CloudFormation::Interface", {})
            .get("ParameterGroups", [])
        )

    def _get_group_labels(self, groups):
        return [g.get("Label", {}).get("default", "") for g in groups]

    def test_bedrock_group_exists(self, groups):
        labels = self._get_group_labels(groups)
        assert "Bedrock Model Invocation Logs" in labels

    def test_bedrock_group_parameters(self, groups):
        for g in groups:
            if g.get("Label", {}).get("default") == "Bedrock Model Invocation Logs":
                params = g.get("Parameters", [])
                assert params == [
                    "EnableBedrockInvocationLogs",
                    "BedrockInvocationLogExpirationInDays",
                    "BedrockInvocationLogKmsKeyArn",
                ], f"Unexpected parameter order in Bedrock group: {params}"
                return
        pytest.fail("Bedrock parameter group not found")

    def test_bedrock_group_after_s3_access_log_group(self, groups):
        labels = self._get_group_labels(groups)
        assert "S3 Access Log Bucket" in labels
        assert "Bedrock Model Invocation Logs" in labels
        s3_idx = labels.index("S3 Access Log Bucket")
        bedrock_idx = labels.index("Bedrock Model Invocation Logs")
        assert bedrock_idx == s3_idx + 1, (
            "Bedrock group must immediately follow the S3 Access Log Bucket group"
        )

    def test_bedrock_group_before_promotion_group(self, groups):
        labels = self._get_group_labels(groups)
        assert "Promotion" in labels
        assert "Bedrock Model Invocation Logs" in labels
        bedrock_idx = labels.index("Bedrock Model Invocation Logs")
        promotion_idx = labels.index("Promotion")
        assert bedrock_idx < promotion_idx

    def test_each_new_parameter_in_exactly_one_group(self, groups):
        for param_name in [
            "EnableBedrockInvocationLogs",
            "BedrockInvocationLogExpirationInDays",
            "BedrockInvocationLogKmsKeyArn",
        ]:
            count = sum(
                1 for g in groups if param_name in g.get("Parameters", [])
            )
            assert count == 1, (
                f"Parameter '{param_name}' must appear in exactly one group, found in {count}"
            )


class TestParentTemplateResources:
    """Req 7.1, 7.2, 7.3 — two new AWS::Include resources exist."""

    @pytest.fixture
    def resources(self, parent):
        return parent.get("Resources", {})

    def test_bedrock_log_group_resource_exists(self, resources):
        assert "BedrockModelInvocationLogGroup" in resources

    def test_bedrock_role_resource_exists(self, resources):
        assert "BedrockCloudWatchLogsRole" in resources

    def test_log_group_resource_is_include_transform(self, resources):
        r = resources["BedrockModelInvocationLogGroup"]
        transform = r.get("Fn::Transform", {})
        assert transform.get("Name") == "AWS::Include"

    def test_role_resource_is_include_transform(self, resources):
        r = resources["BedrockCloudWatchLogsRole"]
        transform = r.get("Fn::Transform", {})
        assert transform.get("Name") == "AWS::Include"

    def test_log_group_module_path_in_location(self, resources):
        r = resources["BedrockModelInvocationLogGroup"]
        location = r["Fn::Transform"]["Parameters"]["Location"]
        assert "bedrock-cloudwatch-log-group.yml" in str(location)

    def test_role_module_path_in_location(self, resources):
        r = resources["BedrockCloudWatchLogsRole"]
        location = r["Fn::Transform"]["Parameters"]["Location"]
        assert "bedrock-cloudwatch-role.yml" in str(location)

    def test_role_resource_has_no_depends_on(self, resources):
        r = resources["BedrockCloudWatchLogsRole"]
        assert "DependsOn" not in r, (
            "BedrockCloudWatchLogsRole must not have DependsOn; "
            "the ARN is constructed, not referenced via Fn::GetAtt"
        )


class TestParentTemplateOutputs:
    """Req 8.1–8.6 — five new conditional outputs."""

    @pytest.fixture
    def outputs(self, parent):
        return parent.get("Outputs", {})

    BEDROCK_CONDITION = "EnableBedrockInvocationLogs"

    def _assert_condition(self, output):
        assert output.get("Condition") == self.BEDROCK_CONDITION, (
            f"Output must carry Condition: {self.BEDROCK_CONDITION}"
        )

    def test_log_group_name_output_exists(self, outputs):
        assert "BedrockModelInvocationLogGroupName" in outputs

    def test_log_group_name_output_condition(self, outputs):
        self._assert_condition(outputs["BedrockModelInvocationLogGroupName"])

    def test_log_group_name_output_export(self, outputs):
        export = outputs["BedrockModelInvocationLogGroupName"].get("Export", {}).get("Name", "")
        assert "Bedrock-CloudWatch-LogGroup-Name" in str(export)

    def test_log_group_arn_output_exists(self, outputs):
        assert "BedrockModelInvocationLogGroupArn" in outputs

    def test_log_group_arn_output_condition(self, outputs):
        self._assert_condition(outputs["BedrockModelInvocationLogGroupArn"])

    def test_log_group_arn_output_export(self, outputs):
        export = outputs["BedrockModelInvocationLogGroupArn"].get("Export", {}).get("Name", "")
        assert "Bedrock-CloudWatch-LogGroup-Arn" in str(export)

    def test_role_arn_output_exists(self, outputs):
        assert "BedrockCloudWatchLogsRoleArn" in outputs

    def test_role_arn_output_condition(self, outputs):
        self._assert_condition(outputs["BedrockCloudWatchLogsRoleArn"])

    def test_role_arn_output_export(self, outputs):
        export = outputs["BedrockCloudWatchLogsRoleArn"].get("Export", {}).get("Name", "")
        assert "Bedrock-CloudWatch-Role-Arn" in str(export)

    def test_enable_command_output_exists(self, outputs):
        assert "BedrockModelInvocationLoggingEnableCommand" in outputs

    def test_enable_command_output_condition(self, outputs):
        self._assert_condition(outputs["BedrockModelInvocationLoggingEnableCommand"])

    def test_enable_command_output_not_exported(self, outputs):
        assert "Export" not in outputs["BedrockModelInvocationLoggingEnableCommand"]

    def test_console_link_output_exists(self, outputs):
        assert "BedrockModelInvocationLogGroupConsole" in outputs

    def test_console_link_output_condition(self, outputs):
        self._assert_condition(outputs["BedrockModelInvocationLogGroupConsole"])

    def test_console_link_output_not_exported(self, outputs):
        assert "Export" not in outputs["BedrockModelInvocationLogGroupConsole"]

    @staticmethod
    def _sub_template_to_json(sub_value):
        """Extract the JSON template string from a !Sub value (either a bare
        string or a [template, mapping] list), sanitise ${...} placeholders,
        and parse it as JSON."""
        if isinstance(sub_value, dict) and "!Sub" in sub_value:
            inner = sub_value["!Sub"]
        else:
            inner = sub_value
        if isinstance(inner, list):
            json_template = inner[0]
        elif isinstance(inner, str):
            json_template = inner
        else:
            pytest.fail(f"Unexpected !Sub inner type: {type(inner)}: {inner!r}")
        sanitised = re.sub(r'"\$\{[^}]+\}"', '"placeholder"', json_template)
        sanitised = re.sub(r"\$\{[^}]+\}", "placeholder", sanitised)
        try:
            return json.loads(sanitised)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"enable-command Value is not valid JSON after placeholder substitution: {exc}\n"
                f"Sanitised string: {sanitised}"
            )

    def test_enable_command_json_structure(self, outputs):
        """The Value of BedrockModelInvocationLoggingEnableCommand is an Fn::If
        keyed on EnableBedrockLargeObjectLogging (v0.0.44). Both branches must be
        valid JSON: the media-OFF (else) branch keeps image/video disabled and
        matches the v0.0.43 payload; the media-ON branch enables image/video and
        adds cloudWatchConfig.largeDataDeliveryS3Config.
        """
        value = outputs["BedrockModelInvocationLoggingEnableCommand"].get("Value", "")
        assert isinstance(value, dict) and "!If" in value, (
            "Enable-command Value must be an Fn::If keyed on EnableBedrockLargeObjectLogging"
        )
        cond, media_on, media_off = value["!If"]
        assert cond == "EnableBedrockLargeObjectLogging"

        # Media-OFF branch (default): parity with v0.0.43
        off_payload = self._sub_template_to_json(media_off)
        assert off_payload.get("textDataDeliveryEnabled") is True
        assert off_payload.get("embeddingDataDeliveryEnabled") is True
        assert off_payload.get("imageDataDeliveryEnabled") is False
        assert off_payload.get("videoDataDeliveryEnabled") is False
        assert "cloudWatchConfig" in off_payload
        assert "largeDataDeliveryS3Config" not in off_payload["cloudWatchConfig"]

        # Media-ON branch: image/video enabled + large data delivery target
        on_payload = self._sub_template_to_json(media_on)
        assert on_payload.get("textDataDeliveryEnabled") is True
        assert on_payload.get("embeddingDataDeliveryEnabled") is True
        assert on_payload.get("imageDataDeliveryEnabled") is True
        assert on_payload.get("videoDataDeliveryEnabled") is True
        assert "cloudWatchConfig" in on_payload
        large = on_payload["cloudWatchConfig"].get("largeDataDeliveryS3Config", {})
        assert large.get("keyPrefix") == "bedrock"
        assert "bucketName" in large


class TestParentHeaderComment:
    """Req 9.1–9.6 — header comment contains activation documentation."""

    def test_header_mentions_bedrock_feature(self, parent_raw):
        assert "Bedrock" in parent_raw

    def test_header_contains_manual_activation_warning(self, parent_raw):
        assert "MANUAL ACTIVATION REQUIRED" in parent_raw or "does NOT" in parent_raw

    def test_header_contains_put_model_invocation_logging_configuration(self, parent_raw):
        assert "put-model-invocation-logging-configuration" in parent_raw

    def test_header_references_admin_ops_doc(self, parent_raw):
        assert "bedrock-model-invocation-logging" in parent_raw

    def test_header_references_aws_docs_url(self, parent_raw):
        assert "docs.aws.amazon.com/bedrock" in parent_raw


# ===========================================================================
# TASK 7.2 — Log group module assertions
# ===========================================================================

class TestLogGroupModuleStructure:
    """Req 5.1, 5.2 — single resource body, no logical ID, no Resources wrapper."""

    def test_no_resources_key_at_top_level(self, log_group_module):
        assert "Resources" not in log_group_module, (
            "Module must not have a Resources: wrapper"
        )

    def test_top_level_keys_are_resource_attribute_keys(self, log_group_module):
        allowed_keys = {"Type", "Condition", "DeletionPolicy", "UpdateReplacePolicy",
                        "Properties", "DependsOn", "Metadata"}
        actual_keys = set(log_group_module.keys())
        unexpected = actual_keys - allowed_keys
        assert not unexpected, (
            f"Module top-level keys contain unexpected keys (possible logical ID wrapper): {unexpected}"
        )

    def test_type_is_log_group(self, log_group_module):
        assert log_group_module.get("Type") == "AWS::Logs::LogGroup"

    def test_condition_is_enable_bedrock_invocation_logs(self, log_group_module):
        assert log_group_module.get("Condition") == "EnableBedrockInvocationLogs"

    def test_deletion_policy_is_retain(self, log_group_module):
        assert log_group_module.get("DeletionPolicy") == "Retain"

    def test_update_replace_policy_is_retain(self, log_group_module):
        assert log_group_module.get("UpdateReplacePolicy") == "Retain"


class TestLogGroupModuleProperties:
    """Req 5.3, 5.4, 5.5, 5.6, 5.7, 5.8 — properties are correct."""

    @pytest.fixture
    def props(self, log_group_module):
        return log_group_module.get("Properties", {})

    def test_log_group_name_uses_fn_sub(self, props):
        name = props.get("LogGroupName")
        assert isinstance(name, dict) and "Fn::Sub" in name, (
            "LogGroupName must use Fn::Sub"
        )

    def test_log_group_name_pattern(self, props):
        sub_val = props["LogGroupName"]["Fn::Sub"]
        assert "/aws/bedrock/${OrgPrefix}-ModelInvocations" == sub_val

    def test_retention_in_days_is_ref(self, props):
        ret = props.get("RetentionInDays")
        assert isinstance(ret, dict) and "Ref" in ret, (
            "RetentionInDays must use Ref"
        )
        assert ret["Ref"] == "BedrockInvocationLogExpirationInDays"

    def test_kms_key_id_is_fn_if(self, props):
        kms = props.get("KmsKeyId")
        assert isinstance(kms, dict) and "Fn::If" in kms, (
            "KmsKeyId must use Fn::If for optional KMS key"
        )

    def test_kms_key_fn_if_condition(self, props):
        fn_if = props["KmsKeyId"]["Fn::If"]
        assert fn_if[0] == "HasBedrockInvocationLogKmsKey"

    def test_kms_key_fn_if_true_branch_refs_param(self, props):
        fn_if = props["KmsKeyId"]["Fn::If"]
        true_branch = fn_if[1]
        assert isinstance(true_branch, dict) and true_branch.get("Ref") == "BedrockInvocationLogKmsKeyArn"

    def test_kms_key_fn_if_false_branch_is_no_value(self, props):
        fn_if = props["KmsKeyId"]["Fn::If"]
        false_branch = fn_if[2]
        assert isinstance(false_branch, dict) and false_branch.get("Ref") == "AWS::NoValue"


# ===========================================================================
# TASK 7.3 — Role module assertions
# ===========================================================================

class TestRoleModuleStructure:
    """Req 6.1, 6.2 — single resource body, no logical ID, no Resources wrapper."""

    def test_no_resources_key_at_top_level(self, role_module):
        assert "Resources" not in role_module

    def test_top_level_keys_are_resource_attribute_keys(self, role_module):
        allowed_keys = {"Type", "Condition", "DeletionPolicy", "UpdateReplacePolicy",
                        "Properties", "DependsOn", "Metadata"}
        actual_keys = set(role_module.keys())
        unexpected = actual_keys - allowed_keys
        assert not unexpected, (
            f"Module top-level keys contain unexpected keys: {unexpected}"
        )

    def test_type_is_iam_role(self, role_module):
        assert role_module.get("Type") == "AWS::IAM::Role"

    def test_condition_is_enable_bedrock_invocation_logs(self, role_module):
        assert role_module.get("Condition") == "EnableBedrockInvocationLogs"


class TestRoleModuleProperties:
    """Req 6.3–6.12 — role properties are correct."""

    @pytest.fixture
    def props(self, role_module):
        return role_module.get("Properties", {})

    @pytest.fixture
    def trust_statement(self, props):
        stmts = props["AssumeRolePolicyDocument"]["Statement"]
        assert len(stmts) == 1
        return stmts[0]

    @pytest.fixture
    def inline_policy(self, props):
        policies = props.get("Policies", [])
        assert len(policies) == 1
        return policies[0]

    @pytest.fixture
    def inline_statement(self, inline_policy):
        stmts = inline_policy["PolicyDocument"]["Statement"]
        assert len(stmts) == 1
        return stmts[0]

    def test_role_name_uses_fn_sub(self, props):
        name = props.get("RoleName")
        assert isinstance(name, dict) and "Fn::Sub" in name

    def test_role_name_pattern(self, props):
        assert props["RoleName"]["Fn::Sub"] == "${OrgPrefix}-Bedrock-CloudWatch-Role"

    def test_path_refs_role_path_param(self, props):
        path = props.get("Path")
        assert isinstance(path, dict) and path.get("Ref") == "RolePath"

    def test_no_managed_policy_arns(self, props):
        assert "ManagedPolicyArns" not in props, (
            "Role must use an inline policy, not a managed policy ARN"
        )

    # Trust policy

    def test_trust_principal_is_bedrock(self, trust_statement):
        principal = trust_statement.get("Principal", {})
        assert principal.get("Service") == "bedrock.amazonaws.com"

    def test_trust_action_is_assume_role(self, trust_statement):
        assert trust_statement.get("Action") == "sts:AssumeRole"

    def test_trust_effect_is_allow(self, trust_statement):
        assert trust_statement.get("Effect") == "Allow"

    def test_trust_has_source_account_condition(self, trust_statement):
        condition = trust_statement.get("Condition", {})
        assert "StringEquals" in condition
        assert "aws:SourceAccount" in condition["StringEquals"]

    def test_trust_source_account_refs_account_id(self, trust_statement):
        source_account = (
            trust_statement["Condition"]["StringEquals"]["aws:SourceAccount"]
        )
        assert isinstance(source_account, dict)
        assert source_account.get("Ref") == "AWS::AccountId"

    def test_trust_has_source_arn_condition(self, trust_statement):
        condition = trust_statement.get("Condition", {})
        assert "ArnLike" in condition
        assert "aws:SourceArn" in condition["ArnLike"]

    def test_trust_source_arn_uses_partition_region_account(self, trust_statement):
        source_arn = trust_statement["Condition"]["ArnLike"]["aws:SourceArn"]
        assert isinstance(source_arn, dict) and "Fn::Sub" in source_arn
        sub_val = source_arn["Fn::Sub"]
        assert "${AWS::Partition}" in sub_val
        assert "${AWS::Region}" in sub_val
        assert "${AWS::AccountId}" in sub_val
        assert "bedrock" in sub_val

    # Inline policy

    def test_inline_policy_name(self, inline_policy):
        assert inline_policy.get("PolicyName") == "BedrockModelInvocationLogsWrite"

    def test_inline_policy_actions_exactly_two(self, inline_statement):
        actions = inline_statement.get("Action", [])
        assert isinstance(actions, list)
        assert set(actions) == {"logs:CreateLogStream", "logs:PutLogEvents"}, (
            f"Inline policy must grant exactly logs:CreateLogStream and logs:PutLogEvents, got: {actions}"
        )

    def test_inline_policy_no_wildcard_action(self, inline_statement):
        actions = inline_statement.get("Action", [])
        assert "logs:*" not in actions
        assert "*" not in actions

    def test_inline_policy_resource_is_single_arn(self, inline_statement):
        resource = inline_statement.get("Resource")
        # Resource must be a single Fn::Sub string, not a list or wildcard
        assert isinstance(resource, dict) and "Fn::Sub" in resource, (
            "Resource must be a single Fn::Sub string"
        )

    def test_inline_policy_resource_no_wildcard(self, inline_statement):
        resource_str = str(inline_statement.get("Resource", ""))
        assert resource_str != "*"
        assert resource_str != '"*"'

    def test_inline_policy_resource_scoped_to_log_stream(self, inline_statement):
        sub_val = inline_statement["Resource"]["Fn::Sub"]
        assert ":log-stream:aws/bedrock/modelinvocations" in sub_val

    def test_inline_policy_resource_uses_partition(self, inline_statement):
        sub_val = inline_statement["Resource"]["Fn::Sub"]
        assert "${AWS::Partition}" in sub_val

    def test_inline_policy_resource_scoped_to_log_group_path(self, inline_statement):
        sub_val = inline_statement["Resource"]["Fn::Sub"]
        assert "/aws/bedrock/" in sub_val
        assert "${OrgPrefix}-ModelInvocations" in sub_val


# ===========================================================================
# TASK 7.4 — Cross-module log-group path consistency
# ===========================================================================

class TestCrossModuleLogGroupPathConsistency:
    """Correctness Property 5: the log group path must match between modules."""

    def test_log_group_name_matches_policy_resource_path(self, log_group_module, role_module):
        """
        The LogGroupName in the log group module and the log-group segment of
        the role's inline policy Resource ARN must resolve to the same
        /aws/bedrock/${OrgPrefix}-ModelInvocations path for any OrgPrefix.
        """
        lg_name = log_group_module["Properties"]["LogGroupName"]["Fn::Sub"]

        role_resource_sub = (
            role_module["Properties"]["Policies"][0]["PolicyDocument"]
            ["Statement"][0]["Resource"]["Fn::Sub"]
        )

        # Extract the log-group path from the role's resource ARN.
        # Format: arn:${AWS::Partition}:logs:...:log-group:<path>:log-stream:...
        match = re.search(r":log-group:([^:]+):", role_resource_sub)
        assert match, (
            f"Could not parse log-group path from role resource ARN: {role_resource_sub}"
        )
        role_log_group_path = match.group(1)

        assert lg_name == role_log_group_path, (
            f"Log group path mismatch between modules!\n"
            f"  bedrock-cloudwatch-log-group.yml LogGroupName: {lg_name!r}\n"
            f"  bedrock-cloudwatch-role.yml policy Resource path: {role_log_group_path!r}"
        )


# ===========================================================================
# TASK 7.5 — Module hygiene + documentation assertions
# ===========================================================================

class TestLogGroupModuleHygiene:
    """Req 5.8, 5.9 — no shorthand tags; contract comment present."""

    def test_no_shorthand_intrinsic_tags(self, log_group_module_raw):
        """Shorthand tags must not appear in non-comment lines."""
        non_comment_lines = [
            line for line in log_group_module_raw.splitlines()
            if not line.lstrip().startswith("#")
        ]
        non_comment_text = "\n".join(non_comment_lines)
        for tag in SHORTHAND_TAGS:
            assert tag not in non_comment_text, (
                f"Module must not contain shorthand intrinsic tag '{tag}' in YAML content "
                f"(AWS::Include does not support shorthand syntax). "
                f"Found outside comment lines."
            )

    def test_contract_comment_declares_org_prefix_param(self, log_group_module_raw):
        assert "OrgPrefix" in log_group_module_raw

    def test_contract_comment_declares_expiration_param(self, log_group_module_raw):
        assert "BedrockInvocationLogExpirationInDays" in log_group_module_raw

    def test_contract_comment_declares_kms_param(self, log_group_module_raw):
        assert "BedrockInvocationLogKmsKeyArn" in log_group_module_raw

    def test_contract_comment_declares_enable_condition(self, log_group_module_raw):
        assert "EnableBedrockInvocationLogs" in log_group_module_raw

    def test_contract_comment_declares_kms_condition(self, log_group_module_raw):
        assert "HasBedrockInvocationLogKmsKey" in log_group_module_raw

    def test_aws_include_note_present(self, log_group_module_raw):
        assert "AWS::Include" in log_group_module_raw

    def test_aws_docs_url_present(self, log_group_module_raw):
        assert "docs.aws.amazon.com/bedrock" in log_group_module_raw

    def test_keep_in_sync_note_present(self, log_group_module_raw):
        assert "KEEP IN SYNC" in log_group_module_raw


class TestRoleModuleHygiene:
    """Req 6.10, 6.11, 6.12 — no shorthand tags; contract comment present."""

    def test_no_shorthand_intrinsic_tags(self, role_module_raw):
        """Shorthand tags must not appear in non-comment lines."""
        non_comment_lines = [
            line for line in role_module_raw.splitlines()
            if not line.lstrip().startswith("#")
        ]
        non_comment_text = "\n".join(non_comment_lines)
        for tag in SHORTHAND_TAGS:
            assert tag not in non_comment_text, (
                f"Module must not contain shorthand intrinsic tag '{tag}' in YAML content "
                f"(AWS::Include does not support shorthand syntax). "
                f"Found outside comment lines."
            )

    def test_contract_comment_declares_org_prefix_param(self, role_module_raw):
        assert "OrgPrefix" in role_module_raw

    def test_contract_comment_declares_role_path_param(self, role_module_raw):
        assert "RolePath" in role_module_raw

    def test_contract_comment_declares_enable_condition(self, role_module_raw):
        assert "EnableBedrockInvocationLogs" in role_module_raw

    def test_aws_include_note_present(self, role_module_raw):
        assert "AWS::Include" in role_module_raw

    def test_aws_docs_url_present(self, role_module_raw):
        assert "docs.aws.amazon.com/bedrock" in role_module_raw

    def test_keep_in_sync_note_present(self, role_module_raw):
        assert "KEEP IN SYNC" in role_module_raw

    def test_no_depends_on_rationale_mentioned(self, role_module_raw):
        assert "DependsOn" in role_module_raw  # the 'no DependsOn' note must exist


class TestAdminOpsDocumentation:
    """Req 10.1, 10.2, 10.12, 10.13 — admin-ops docs exist and contain key content."""

    # NOTE: the "copy-over note" blockquote naming the external atlantis-platform-admin
    # repository was intentionally removed from the admin-ops doc by the maintainer, so the
    # assertion that previously required that repo name here has been dropped. The doc's
    # current blockquotes (default/opt-in, data sensitivity, media-logging notes) are the
    # authoritative content. Do not re-add a copy-over-note assertion.

    def test_admin_ops_doc_exists(self):
        assert ADMIN_OPS_DOC.exists(), (
            f"Admin-ops doc not found at {ADMIN_OPS_DOC}"
        )

    def test_admin_ops_doc_contains_activation_command(self):
        text = ADMIN_OPS_DOC.read_text(encoding="utf-8")
        assert "put-model-invocation-logging-configuration" in text

    def test_admin_ops_doc_contains_verification_command(self):
        text = ADMIN_OPS_DOC.read_text(encoding="utf-8")
        assert "get-model-invocation-logging-configuration" in text

    def test_admin_ops_doc_contains_disable_command(self):
        text = ADMIN_OPS_DOC.read_text(encoding="utf-8")
        assert "delete-model-invocation-logging-configuration" in text

    def test_account_management_doc_links_to_bedrock_doc(self):
        text = ACCOUNT_MGMT_DOC.read_text(encoding="utf-8")
        assert "bedrock-model-invocation-logging" in text
