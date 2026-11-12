"""
Unit tests for the Secrets Manager read managed policies (spec 0-0-47-secrets-read-managed-policy).

Sections:
  1. Shared data and helpers
  2. Module tests (task 3.1): the three modules in
     templates/v2/modules/pipeline-policies/secrets-read-*.yml
  3. Template wiring tests (task 3.2): templates/v2/account/account-wide-infrastructure.yml
     (to be added below the marked placeholder; reuse LEVELS and the helpers above)

The tests are fast example-based unit tests, parametrized over the three levels.
They check design Properties 1-5 (modules); 6-7 (template) come with task 3.2.

Validates: Requirements 2.1-2.6, 3.3-3.5, 4.1-4.7, 5.1-5.3, 5.8, 5.9, 6.1-6.5, 8.1-8.6, 8.10
"""
import re
import sys
import os
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# 1. Shared data and helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
MODULE_DIR = PROJECT_ROOT / "templates" / "v2" / "modules" / "pipeline-policies"
PARENT_TEMPLATE = PROJECT_ROOT / "templates" / "v2" / "account" / "account-wide-infrastructure.yml"

LEVELS = {
    "deployment": dict(
        file="secrets-read-deployment.yml",
        tag="atlantis:ApplicationDeploymentId",
        value_format="<Prefix>-<ProjectId>-<StageId>",
        policy="SecretsReadDeployment",
        logical_id="SecretsReadDeploymentPolicy",
    ),
    "application": dict(
        file="secrets-read-application.yml",
        tag="atlantis:Application",
        value_format="<Prefix>-<ProjectId>",
        policy="SecretsReadApplication",
        logical_id="SecretsReadApplicationPolicy",
    ),
    "prefix": dict(
        file="secrets-read-prefix.yml",
        tag="atlantis:Prefix",
        value_format="<Prefix>",
        policy="SecretsReadPrefix",
        logical_id="SecretsReadPrefixPolicy",
    ),
}

EXPECTED_ACTIONS = {"secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"}
EXPECTED_RESOURCE = "arn:${AWS::Partition}:secretsmanager:*:${AWS::AccountId}:secret:*"
PRINCIPAL_VAR = "${aws:PrincipalTag/%s}"

# Actions that must never be allowed (Requirement 4.3, 4.4, 4.5). DescribeSecret is intentionally absent.
FORBIDDEN_ACTIONS = {
    "secretsmanager:ListSecrets",
    "secretsmanager:BatchGetSecretValue",
    "secretsmanager:CreateSecret",
    "secretsmanager:UpdateSecret",
    "secretsmanager:UpdateSecretVersionStage",
    "secretsmanager:PutSecretValue",
    "secretsmanager:DeleteSecret",
    "secretsmanager:RotateSecret",
    "secretsmanager:CancelRotateSecret",
    "secretsmanager:RestoreSecret",
    "secretsmanager:ReplicateSecretToRegions",
    "secretsmanager:RemoveRegionsFromReplication",
    "secretsmanager:StopReplicationToReplica",
    "secretsmanager:TagResource",
    "secretsmanager:UntagResource",
    "secretsmanager:PutResourcePolicy",
    "secretsmanager:DeleteResourcePolicy",
    "secretsmanager:ValidateResourcePolicy",
    "secretsmanager:GetResourcePolicy",
}

SHORTHAND_TAG_RE = re.compile(r"!(Sub|Ref|GetAtt|If|Join|Select)\b")
ATLANTIS_KEY_RE = re.compile(r"atlantis:\w+")


def read_module_text(level):
    return (MODULE_DIR / LEVELS[level]["file"]).read_text()


def comment_lines(text):
    return [line for line in text.splitlines() if line.lstrip().startswith("#")]


def code_text(text):
    """Raw text with comment-only lines removed (header comments mention shorthand syntax)."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def as_list(value):
    return value if isinstance(value, list) else [value]


def allow_statements(module):
    statements = as_list(module["Properties"]["PolicyDocument"]["Statement"])
    return [s for s in statements if s.get("Effect") == "Allow"]


@pytest.fixture(scope="module", params=list(LEVELS))
def level(request):
    return request.param


@pytest.fixture(scope="module")
def module_text(level):
    return read_module_text(level)


@pytest.fixture(scope="module")
def module(module_text):
    # safe_load raises on shorthand tags such as !Sub, which doubles as a long-form check.
    return yaml.safe_load(module_text)


# ---------------------------------------------------------------------------
# 2. Module tests (task 3.1)
# ---------------------------------------------------------------------------


class TestModuleStructure:
    """Property 5: module standards (Requirements 6.1, 6.2, 6.3, 6.5, 8.2)."""

    def test_module_file_exists(self, level):
        assert (MODULE_DIR / LEVELS[level]["file"]).is_file()

    def test_type_is_managed_policy(self, module):
        assert module["Type"] == "AWS::IAM::ManagedPolicy"

    def test_top_level_keys_are_type_and_properties_only(self, module):
        assert set(module.keys()) == {"Type", "Properties"}

    def test_no_resources_block(self, module_text):
        assert not re.search(r"^Resources\s*:", code_text(module_text), re.MULTILINE)

    def test_no_shorthand_intrinsic_tags(self, module_text):
        assert SHORTHAND_TAG_RE.search(code_text(module_text)) is None

    def test_header_comment_declares_contract(self, level, module_text):
        header = "\n".join(comment_lines(module_text))
        info = LEVELS[level]
        assert "OrgPrefix" in header
        assert "RolePath" in header
        assert info["tag"] in header
        assert info["value_format"] in header
        assert "fail closed" in header.lower()


class TestModuleNaming:
    """Property 5: names, path, description, Sids (Requirements 5.1-5.3, 5.8, 5.9, 6.4, 8.3)."""

    def test_managed_policy_name(self, level, module):
        expected = "${OrgPrefix}-ManagedPolicyForPipeline-" + LEVELS[level]["policy"]
        assert module["Properties"]["ManagedPolicyName"] == {"Fn::Sub": expected}

    def test_path_is_ref_role_path(self, module):
        assert module["Properties"]["Path"] == {"Ref": "RolePath"}

    def test_description_states_read_only_and_tag_key(self, level, module):
        description = module["Properties"]["Description"]
        assert "read-only" in description.lower()
        assert LEVELS[level]["tag"] in description

    def test_sids_are_unique_and_non_empty(self, module):
        statements = as_list(module["Properties"]["PolicyDocument"]["Statement"])
        sids = [s.get("Sid") for s in statements]
        assert all(isinstance(s, str) and s for s in sids)
        assert len(sids) == len(set(sids))

    def test_single_statement_sid(self, level, module):
        statements = as_list(module["Properties"]["PolicyDocument"]["Statement"])
        assert len(statements) == 1
        assert statements[0]["Sid"] == LEVELS[level]["policy"] + "ReadSecretTagMatch"


class TestTagConditions:
    """Property 1: every Allow statement is tag-guarded (Requirements 2.4, 3.3, 3.4, 3.5, 8.4)."""

    def test_at_least_one_allow_statement(self, module):
        assert allow_statements(module)

    def test_string_equals_matches_resource_tag_to_principal_tag(self, level, module):
        tag = LEVELS[level]["tag"]
        for stmt in allow_statements(module):
            assert stmt["Condition"]["StringEquals"] == {"aws:ResourceTag/" + tag: PRINCIPAL_VAR % tag}

    def test_null_false_on_principal_and_resource_tag(self, level, module):
        tag = LEVELS[level]["tag"]
        for stmt in allow_statements(module):
            assert stmt["Condition"]["Null"] == {
                "aws:PrincipalTag/" + tag: "false",
                "aws:ResourceTag/" + tag: "false",
            }

    def test_only_expected_condition_operators(self, module):
        for stmt in allow_statements(module):
            assert set(stmt["Condition"].keys()) == {"StringEquals", "Null"}

    def test_policy_variable_not_wrapped_in_fn_sub(self, level, module):
        # ${aws:PrincipalTag/...} must stay a plain string so CloudFormation does not resolve it.
        for stmt in allow_statements(module):
            value = stmt["Condition"]["StringEquals"]["aws:ResourceTag/" + LEVELS[level]["tag"]]
            assert isinstance(value, str)


class TestSingleTag:
    """Property 2: exactly one tag key, no literal values (Requirements 2.1, 2.2, 2.3, 2.5, 2.6)."""

    def test_module_references_exactly_one_atlantis_key(self, level, module_text):
        keys = set(ATLANTIS_KEY_RE.findall(code_text(module_text)))
        assert keys == {LEVELS[level]["tag"]}

    def test_no_literal_prefix_projectid_stageid_in_condition_values(self, level, module):
        tag = LEVELS[level]["tag"]
        for stmt in allow_statements(module):
            for operator, mapping in stmt["Condition"].items():
                for key, value in mapping.items():
                    # Remove the policy variable (it legitimately contains the tag key text).
                    residue = str(value).replace(PRINCIPAL_VAR % tag, "")
                    for literal in ("Prefix", "ProjectId", "StageId"):
                        assert literal not in residue, f"{operator} {key}: {value}"


class TestActions:
    """Property 3: only GetSecretValue and DescribeSecret (Requirements 4.1-4.5, 4.7, 8.5)."""

    def test_union_of_actions_equals_expected(self, module):
        actions = set()
        for stmt in allow_statements(module):
            actions.update(as_list(stmt["Action"]))
        assert actions == EXPECTED_ACTIONS

    def test_both_actions_in_same_single_allow_statement(self, module):
        statements = allow_statements(module)
        assert len(statements) == 1
        assert set(as_list(statements[0]["Action"])) == EXPECTED_ACTIONS

    def test_no_wildcard_actions(self, module):
        for stmt in allow_statements(module):
            for action in as_list(stmt["Action"]):
                assert "*" not in action

    def test_no_forbidden_actions(self, module):
        for stmt in allow_statements(module):
            assert FORBIDDEN_ACTIONS.isdisjoint(as_list(stmt["Action"]))

    def test_describe_secret_is_not_in_forbidden_list(self):
        assert "secretsmanager:DescribeSecret" not in FORBIDDEN_ACTIONS


class TestResource:
    """Property 4: account-scoped secret ARNs only (Requirements 4.6, 8.6)."""

    def test_resource_is_account_scoped_secret_arn(self, module):
        for stmt in allow_statements(module):
            assert as_list(stmt["Resource"]) == [{"Fn::Sub": EXPECTED_RESOURCE}]


# ---------------------------------------------------------------------------
# 3. Template wiring tests (task 3.2) -- add below this line
# ---------------------------------------------------------------------------
# Reuse PARENT_TEMPLATE, LEVELS, and the helpers above.

import datetime

from tests.cfn_test_utils import load_template

MODULE_LOCATION_SUFFIX = "/templates/v2/modules/pipeline-policies/"
RELEASE_DATE_V0_0_46 = datetime.date(2026, 11, 9)

# Names that existed before this feature and must remain (Requirement 5.10, 8.8).
EXISTING_RESOURCES = {"CloudFormationCodeBuildPolicy", "CloudFormationCognitoPolicy"}
EXISTING_OUTPUTS = {
    "CodeBuildCrudPolicyArn": "${OrgPrefix}-ProjectPipeline-CodeBuildCrud-Arn",
    "CodeBuildCrudPolicyName": None,
    "CognitoCrudPolicyArn": "${OrgPrefix}-ProjectPipeline-CognitoCrud-Arn",
    "CognitoCrudPolicyName": None,
}
EXISTING_PARAMETERS = {"OrgPrefix", "RolePath"}


def sub_value(node):
    """Return the string inside a short-form (!Sub) or long-form (Fn::Sub) node."""
    assert isinstance(node, dict), node
    for key in ("!Sub", "Fn::Sub"):
        if key in node:
            return node[key]
    raise AssertionError(f"Not a Sub node: {node!r}")


def ref_value(node):
    assert isinstance(node, dict), node
    for key in ("!Ref", "Ref"):
        if key in node:
            return node[key]
    raise AssertionError(f"Not a Ref node: {node!r}")


@pytest.fixture(scope="module")
def parent():
    return load_template(PARENT_TEMPLATE)


@pytest.fixture(scope="module")
def parent_raw():
    return PARENT_TEMPLATE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parent_header(parent_raw):
    """Leading comment block, up to the first top-level section key after the Description."""
    match = re.search(r"^(Metadata|Parameters|Rules|Conditions|Resources):", parent_raw, re.MULTILINE)
    assert match, "Parent template has no top-level sections"
    return parent_raw[: match.start()]


class TestTemplateWiring:
    """Property 6: wiring (Requirements 1.1, 1.5, 1.6, 8.7)."""

    def test_include_resource_per_level(self, level, parent):
        info = LEVELS[level]
        resource = parent["Resources"][info["logical_id"]]
        assert set(resource.keys()) == {"Fn::Transform"}
        transform = resource["Fn::Transform"]
        assert transform["Name"] == "AWS::Include"
        location = sub_value(transform["Parameters"]["Location"])
        assert location.endswith(MODULE_LOCATION_SUFFIX + info["file"])
        assert location.startswith("s3://${S3ModuleLocation}/${S3ModuleNamespace}/")

    def test_no_condition_on_resources(self, level, parent):
        assert "Condition" not in parent["Resources"][LEVELS[level]["logical_id"]]

    def test_exactly_three_secrets_read_resources(self, parent):
        found = {name for name in parent["Resources"] if name.startswith("SecretsRead")}
        assert found == {info["logical_id"] for info in LEVELS.values()}

    def test_module_files_exist_for_locations(self, level):
        assert (MODULE_DIR / LEVELS[level]["file"]).is_file()


class TestTemplateOutputs:
    """Property 6: outputs (Requirements 5.4-5.7, 8.7)."""

    def test_arn_output(self, level, parent):
        info = LEVELS[level]
        output = parent["Outputs"][info["logical_id"] + "Arn"]
        assert ref_value(output["Value"]) == info["logical_id"]
        assert sub_value(output["Export"]["Name"]) == f"${{OrgPrefix}}-ProjectPipeline-{info['policy']}-Arn"
        assert "SvcRoleIncludeManagedPolicyArns" in output["Description"]

    def test_name_output_matches_policy_name_and_has_no_export(self, level, parent):
        info = LEVELS[level]
        output = parent["Outputs"][info["logical_id"].removesuffix("Policy") + "PolicyName"]
        assert sub_value(output["Value"]) == f"${{OrgPrefix}}-ManagedPolicyForPipeline-{info['policy']}"
        assert "Export" not in output

    def test_name_output_equals_module_policy_name(self, level, parent):
        info = LEVELS[level]
        module = yaml.safe_load(read_module_text(level))
        module_name = module["Properties"]["ManagedPolicyName"]["Fn::Sub"]
        output = parent["Outputs"][info["policy"] + "PolicyName"]
        assert sub_value(output["Value"]) == module_name

    def test_exactly_six_new_outputs(self, parent):
        found = {name for name in parent["Outputs"] if name.startswith("SecretsRead")}
        assert len(found) == 6


class TestExistingContentPreserved:
    """Property 7: existing names remain (Requirements 5.10, 8.8)."""

    def test_existing_resources_present(self, parent):
        assert EXISTING_RESOURCES <= set(parent["Resources"])

    def test_existing_outputs_present(self, parent):
        assert set(EXISTING_OUTPUTS) <= set(parent["Outputs"])

    def test_existing_export_names_unchanged(self, parent):
        for name, export in EXISTING_OUTPUTS.items():
            if export is not None:
                assert sub_value(parent["Outputs"][name]["Export"]["Name"]) == export

    def test_existing_parameters_present(self, parent):
        assert EXISTING_PARAMETERS <= set(parent["Parameters"])

    def test_existing_resources_still_use_original_modules(self, parent):
        codebuild = sub_value(parent["Resources"]["CloudFormationCodeBuildPolicy"]["Fn::Transform"]["Parameters"]["Location"])
        cognito = sub_value(parent["Resources"]["CloudFormationCognitoPolicy"]["Fn::Transform"]["Parameters"]["Location"])
        assert codebuild.endswith(MODULE_LOCATION_SUFFIX + "codebuild-crud.yml")
        assert cognito.endswith(MODULE_LOCATION_SUFFIX + "cognito-crud.yml")


class TestTemplateHeader:
    """Property 7: header version/date and listing (Requirements 9.1, 9.2, 9.3, 8.9)."""

    def test_version_line_is_v2_1_0_with_valid_recent_date(self, parent_raw):
        match = re.search(r"^# Version: (v\d+\.\d+\.\d+)/(\d{4}-\d{2}-\d{2})\s*$", parent_raw, re.MULTILINE)
        assert match, "Header '# Version: vX.Y.Z/YYYY-MM-DD' line not found"
        assert match.group(1) == "v2.1.0"
        date = datetime.date.fromisoformat(match.group(2))  # raises on an invalid date
        assert date >= RELEASE_DATE_V0_0_46

    def test_header_lists_secrets_read_policies(self, parent_header):
        assert "Secrets Manager read managed policies" in parent_header
        for tag in ("atlantis:ApplicationDeploymentId", "atlantis:Application", "atlantis:Prefix"):
            assert tag in parent_header
