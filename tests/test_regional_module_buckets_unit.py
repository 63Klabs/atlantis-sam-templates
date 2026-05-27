"""
Unit tests for regional module bucket resolution across all 6 templates.
Tests S3ModuleLocation parameter, S3ModuleNamespace parameter, RegionalModuleBuckets mapping,
HasS3ModuleLocation condition, AWS::Include Location patterns, and Metadata parameter groups.

Validates: Requirements 1.1–1.5, 2.1–2.5, 3.1–3.6, 4.1–4.2, 5.5, 5.6, 7.1, 7.2
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template, get_template_section


# =============================================================================
# FIXTURES
# =============================================================================

TEMPLATE_PATHS = [
    "templates/v2/account/account-wide-infrastructure.yml",
    "templates/v2/account/prefix-based-infrastructure.yml",
    "templates/v2/service-role/template-service-role-pipeline.yml",
    "templates/v2/service-role/template-service-role-network-cloudfront.yml",
    "templates/v2/service-role/template-service-role-network-full.yml",
    "templates/v2/service-role/template-service-role-storage.yml",
]

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(params=TEMPLATE_PATHS, ids=[Path(p).stem for p in TEMPLATE_PATHS])
def template(request):
    """Load each of the 6 templates as a parameterized fixture."""
    template_path = PROJECT_ROOT / request.param
    return load_template(template_path)


# =============================================================================
# S3ModuleLocation Parameter Tests
# Validates: Requirements 1.1, 1.2, 1.4, 1.5
# =============================================================================

class TestS3ModuleLocationParameter:
    """Test S3ModuleLocation parameter definition across all templates."""

    def test_parameter_exists(self, template):
        """S3ModuleLocation parameter must exist."""
        params = get_template_section(template, "Parameters")
        assert "S3ModuleLocation" in params

    def test_type_is_string(self, template):
        """S3ModuleLocation Type must be String."""
        param = get_template_section(template, "Parameters")["S3ModuleLocation"]
        assert param["Type"] == "String"

    def test_default_is_empty_string(self, template):
        """S3ModuleLocation Default must be empty string."""
        param = get_template_section(template, "Parameters")["S3ModuleLocation"]
        assert param["Default"] == ""

    def test_allowed_pattern(self, template):
        """S3ModuleLocation AllowedPattern must match expected regex."""
        param = get_template_section(template, "Parameters")["S3ModuleLocation"]
        expected = "^$|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
        assert param["AllowedPattern"] == expected

    def test_has_constraint_description(self, template):
        """S3ModuleLocation must have a ConstraintDescription."""
        param = get_template_section(template, "Parameters")["S3ModuleLocation"]
        assert "ConstraintDescription" in param
        assert len(param["ConstraintDescription"]) > 0


# =============================================================================
# S3ModuleNamespace Parameter Tests
# Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
# =============================================================================

class TestS3ModuleNamespaceParameter:
    """Test S3ModuleNamespace parameter definition across all templates."""

    def test_parameter_exists(self, template):
        """S3ModuleNamespace parameter must exist."""
        params = get_template_section(template, "Parameters")
        assert "S3ModuleNamespace" in params

    def test_type_is_string(self, template):
        """S3ModuleNamespace Type must be String."""
        param = get_template_section(template, "Parameters")["S3ModuleNamespace"]
        assert param["Type"] == "String"

    def test_default_is_atlantis(self, template):
        """S3ModuleNamespace Default must be 'atlantis'."""
        param = get_template_section(template, "Parameters")["S3ModuleNamespace"]
        assert param["Default"] == "atlantis"

    def test_allowed_pattern(self, template):
        """S3ModuleNamespace AllowedPattern must match expected regex."""
        param = get_template_section(template, "Parameters")["S3ModuleNamespace"]
        expected = "^[a-z0-9][a-z0-9\\-]*(\\/[a-z0-9][a-z0-9\\-]*)*$"
        assert param["AllowedPattern"] == expected

    def test_min_length(self, template):
        """S3ModuleNamespace MinLength must be 1."""
        param = get_template_section(template, "Parameters")["S3ModuleNamespace"]
        assert param["MinLength"] == 1

    def test_max_length(self, template):
        """S3ModuleNamespace MaxLength must be 128."""
        param = get_template_section(template, "Parameters")["S3ModuleNamespace"]
        assert param["MaxLength"] == 128

    def test_has_constraint_description(self, template):
        """S3ModuleNamespace must have a ConstraintDescription."""
        param = get_template_section(template, "Parameters")["S3ModuleNamespace"]
        assert "ConstraintDescription" in param
        assert len(param["ConstraintDescription"]) > 0


# =============================================================================
# RegionalModuleBuckets Mapping Tests
# Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
# =============================================================================

class TestRegionalModuleBucketsMapping:
    """Test RegionalModuleBuckets mapping across all templates."""

    EXPECTED_MAPPING = {
        "us-east-1": "63klabs-atlas-us-east-1",
        "us-east-2": "63klabs-zenith-us-east-2",
        "us-west-1": "63klabs-fabric-us-west-1",
        "us-west-2": "63klabs-orbit-us-west-2",
    }

    def test_mappings_section_exists(self, template):
        """Mappings section must exist."""
        assert "Mappings" in template

    def test_regional_module_buckets_exists(self, template):
        """RegionalModuleBuckets mapping must exist."""
        mappings = get_template_section(template, "Mappings")
        assert "RegionalModuleBuckets" in mappings

    def test_contains_exactly_4_regions(self, template):
        """RegionalModuleBuckets must contain exactly 4 regions."""
        mapping = get_template_section(template, "Mappings")["RegionalModuleBuckets"]
        assert len(mapping) == 4, f"Expected 4 regions, got {len(mapping)}: {list(mapping.keys())}"

    def test_us_east_1_bucket(self, template):
        """us-east-1 must map to 63klabs-atlas-us-east-1."""
        mapping = get_template_section(template, "Mappings")["RegionalModuleBuckets"]
        assert "us-east-1" in mapping
        assert mapping["us-east-1"]["BucketName"] == "63klabs-atlas-us-east-1"

    def test_us_east_2_bucket(self, template):
        """us-east-2 must map to 63klabs-zenith-us-east-2."""
        mapping = get_template_section(template, "Mappings")["RegionalModuleBuckets"]
        assert "us-east-2" in mapping
        assert mapping["us-east-2"]["BucketName"] == "63klabs-zenith-us-east-2"

    def test_us_west_1_bucket(self, template):
        """us-west-1 must map to 63klabs-fabric-us-west-1."""
        mapping = get_template_section(template, "Mappings")["RegionalModuleBuckets"]
        assert "us-west-1" in mapping
        assert mapping["us-west-1"]["BucketName"] == "63klabs-fabric-us-west-1"

    def test_us_west_2_bucket(self, template):
        """us-west-2 must map to 63klabs-orbit-us-west-2."""
        mapping = get_template_section(template, "Mappings")["RegionalModuleBuckets"]
        assert "us-west-2" in mapping
        assert mapping["us-west-2"]["BucketName"] == "63klabs-orbit-us-west-2"

    def test_all_entries_use_bucket_name_key(self, template):
        """All mapping entries must use 'BucketName' as the key."""
        mapping = get_template_section(template, "Mappings")["RegionalModuleBuckets"]
        for region, entry in mapping.items():
            assert "BucketName" in entry, f"Region {region} missing 'BucketName' key"


# =============================================================================
# HasS3ModuleLocation Condition Tests
# Validates: Requirements 4.1, 4.2
# =============================================================================

class TestHasS3ModuleLocationCondition:
    """Test HasS3ModuleLocation condition across all templates."""

    def test_condition_exists(self, template):
        """HasS3ModuleLocation condition must exist."""
        conditions = get_template_section(template, "Conditions")
        assert "HasS3ModuleLocation" in conditions

    def test_condition_uses_not_equals_pattern(self, template):
        """HasS3ModuleLocation must use !Not [!Equals [...]] pattern."""
        condition = get_template_section(template, "Conditions")["HasS3ModuleLocation"]
        # CFNLoader parses !Not [...] as {"!Not": [...]}
        assert isinstance(condition, dict), "Condition should be a dict"
        assert "!Not" in condition, "Condition should use !Not"

    def test_condition_not_contains_equals(self, template):
        """The !Not must wrap an !Equals comparison."""
        condition = get_template_section(template, "Conditions")["HasS3ModuleLocation"]
        not_list = condition["!Not"]
        assert isinstance(not_list, list), "!Not should contain a list"
        assert len(not_list) == 1, "!Not should contain exactly one element"
        equals_element = not_list[0]
        assert isinstance(equals_element, dict), "Inner element should be a dict"
        assert "!Equals" in equals_element, "Inner element should be !Equals"

    def test_condition_references_s3_module_location(self, template):
        """The !Equals must reference S3ModuleLocation parameter."""
        condition = get_template_section(template, "Conditions")["HasS3ModuleLocation"]
        equals_list = condition["!Not"][0]["!Equals"]
        assert isinstance(equals_list, list), "!Equals should contain a list"
        assert len(equals_list) == 2, "!Equals should compare two values"

        # First element should be !Ref S3ModuleLocation
        ref_element = equals_list[0]
        assert isinstance(ref_element, dict), "First element should be a dict"
        assert "!Ref" in ref_element, "First element should be !Ref"
        assert ref_element["!Ref"] == "S3ModuleLocation"

    def test_condition_compares_against_empty_string(self, template):
        """The !Equals must compare against empty string."""
        condition = get_template_section(template, "Conditions")["HasS3ModuleLocation"]
        equals_list = condition["!Not"][0]["!Equals"]
        assert equals_list[1] == "", "Second element should be empty string"


# =============================================================================
# AWS::Include Location Tests
# Validates: Requirements 5.5, 5.6
# =============================================================================

class TestIncludeLocationPattern:
    """Test that all AWS::Include Location values use !Sub with variable map."""

    def _find_all_includes(self, obj, includes=None):
        """Recursively find all AWS::Include transform Location values."""
        if includes is None:
            includes = []
        if isinstance(obj, dict):
            if obj.get("Name") == "AWS::Include" or "AWS::Include" in str(obj.get("Name", "")):
                params = obj.get("Parameters", {})
                if "Location" in params:
                    includes.append(params["Location"])
            for key, value in obj.items():
                if key == "Fn::Transform":
                    if isinstance(value, dict):
                        if value.get("Name") == "AWS::Include":
                            params = value.get("Parameters", {})
                            if "Location" in params:
                                includes.append(params["Location"])
                    self._find_all_includes(value, includes)
                else:
                    self._find_all_includes(value, includes)
        elif isinstance(obj, list):
            for item in obj:
                self._find_all_includes(item, includes)
        return includes

    def test_has_at_least_one_include(self, template):
        """Template must have at least one AWS::Include transform."""
        includes = self._find_all_includes(template)
        assert len(includes) > 0, "Template should have at least one AWS::Include"

    def test_all_includes_use_sub(self, template):
        """All Include Locations must use !Sub."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            assert isinstance(location, dict), f"Include {i}: Location should be a dict"
            assert "!Sub" in location, f"Include {i}: Location should use !Sub"

    def test_all_includes_have_variable_map(self, template):
        """All Include Locations must use !Sub with a variable map (list form)."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            sub_value = location["!Sub"]
            assert isinstance(sub_value, list), (
                f"Include {i}: !Sub should be a list [template_string, variable_map]"
            )
            assert len(sub_value) == 2, (
                f"Include {i}: !Sub list should have exactly 2 elements"
            )

    def test_variable_map_contains_bucket_name(self, template):
        """All Include variable maps must contain 'BucketName' key."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            variable_map = location["!Sub"][1]
            assert isinstance(variable_map, dict), f"Include {i}: variable map should be a dict"
            assert "BucketName" in variable_map, (
                f"Include {i}: variable map must contain 'BucketName'"
            )

    def test_variable_map_contains_namespace(self, template):
        """All Include variable maps must contain 'Namespace' key."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            variable_map = location["!Sub"][1]
            assert "Namespace" in variable_map, (
                f"Include {i}: variable map must contain 'Namespace'"
            )

    def test_bucket_name_uses_if_condition(self, template):
        """BucketName in variable map must use !If with HasS3ModuleLocation."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            variable_map = location["!Sub"][1]
            bucket_name = variable_map["BucketName"]
            assert isinstance(bucket_name, dict), f"Include {i}: BucketName should be a dict"
            assert "!If" in bucket_name, f"Include {i}: BucketName should use !If"
            if_list = bucket_name["!If"]
            assert if_list[0] == "HasS3ModuleLocation", (
                f"Include {i}: BucketName !If should reference HasS3ModuleLocation"
            )

    def test_namespace_references_parameter(self, template):
        """Namespace in variable map must reference S3ModuleNamespace parameter."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            variable_map = location["!Sub"][1]
            namespace = variable_map["Namespace"]
            assert isinstance(namespace, dict), f"Include {i}: Namespace should be a dict"
            assert "!Ref" in namespace, f"Include {i}: Namespace should use !Ref"
            assert namespace["!Ref"] == "S3ModuleNamespace", (
                f"Include {i}: Namespace should reference S3ModuleNamespace"
            )

    def test_location_uri_format(self, template):
        """All Include Location URIs must follow s3://${{BucketName}}/${{Namespace}}/templates/v2/modules/ pattern."""
        includes = self._find_all_includes(template)
        for i, location in enumerate(includes):
            uri_template = location["!Sub"][0]
            assert uri_template.startswith("s3://${BucketName}/${Namespace}/templates/v2/modules/"), (
                f"Include {i}: URI should start with 's3://${{BucketName}}/${{Namespace}}/templates/v2/modules/', "
                f"got: {uri_template}"
            )


# =============================================================================
# Metadata Parameter Group Tests
# Validates: Requirements 7.1, 7.2
# =============================================================================

class TestMetadataModuleSourceGroup:
    """Test Metadata 'Module Source' parameter group across all templates."""

    def _get_parameter_groups(self, template):
        """Get ParameterGroups from template Metadata."""
        metadata = template.get("Metadata", {})
        interface = metadata.get("AWS::CloudFormation::Interface", {})
        return interface.get("ParameterGroups", [])

    def _find_module_source_group(self, template):
        """Find the 'Module Source' parameter group."""
        groups = self._get_parameter_groups(template)
        for group in groups:
            label = group.get("Label", {})
            if label.get("default") == "Module Source":
                return group
        return None

    def test_module_source_group_exists(self, template):
        """'Module Source' parameter group must exist in Metadata."""
        group = self._find_module_source_group(template)
        assert group is not None, "Metadata must contain a 'Module Source' parameter group"

    def test_group_contains_s3_module_location(self, template):
        """'Module Source' group must contain S3ModuleLocation."""
        group = self._find_module_source_group(template)
        params = group.get("Parameters", [])
        assert "S3ModuleLocation" in params, (
            "'Module Source' group must contain S3ModuleLocation"
        )

    def test_group_contains_s3_module_namespace(self, template):
        """'Module Source' group must contain S3ModuleNamespace."""
        group = self._find_module_source_group(template)
        params = group.get("Parameters", [])
        assert "S3ModuleNamespace" in params, (
            "'Module Source' group must contain S3ModuleNamespace"
        )

    def test_s3_module_location_listed_first(self, template):
        """S3ModuleLocation must be listed before S3ModuleNamespace."""
        group = self._find_module_source_group(template)
        params = group.get("Parameters", [])
        loc_idx = params.index("S3ModuleLocation")
        ns_idx = params.index("S3ModuleNamespace")
        assert loc_idx < ns_idx, (
            "S3ModuleLocation must be listed before S3ModuleNamespace in the group"
        )
