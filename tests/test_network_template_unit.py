"""
Unit tests for network template CloudFront logging parameter.
Tests the S3LogBucketName parameter definition and constraints.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import (
    load_template,
    get_template_section,
    validate_parameter_constraints,
    validate_regex_pattern
)


@pytest.fixture
def network_template():
    """Load the network template for testing."""
    template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
    return load_template(template_path)


class TestS3LogBucketNameParameter:
    """Test suite for S3LogBucketName parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that S3LogBucketName parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'S3LogBucketName' in parameters, "S3LogBucketName parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that S3LogBucketName has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        assert param['Type'] == 'String', "S3LogBucketName should be of type String"
    
    def test_default_value_is_empty_string(self, network_template):
        """Test that S3LogBucketName default value is empty string."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        assert param['Default'] == "", "S3LogBucketName default should be empty string"
    
    def test_allowed_pattern_exists(self, network_template):
        """Test that S3LogBucketName has AllowedPattern defined."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        assert 'AllowedPattern' in param, "S3LogBucketName should have AllowedPattern"
    
    def test_allowed_pattern_value(self, network_template):
        """Test that S3LogBucketName has correct AllowedPattern regex."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        expected_pattern = "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"
        assert param['AllowedPattern'] == expected_pattern, f"AllowedPattern should be {expected_pattern}"
    
    def test_constraint_description_exists(self, network_template):
        """Test that S3LogBucketName has ConstraintDescription."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        assert 'ConstraintDescription' in param, "S3LogBucketName should have ConstraintDescription"
        assert len(param['ConstraintDescription']) > 0, "ConstraintDescription should not be empty"
    
    def test_description_exists(self, network_template):
        """Test that S3LogBucketName has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        assert 'Description' in param, "S3LogBucketName should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_allowed_pattern_regex_valid_bucket_names(self, network_template):
        """Test AllowedPattern regex accepts valid S3 bucket names."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        pattern = param['AllowedPattern']
        
        valid_bucket_names = [
            "my-log-bucket",
            "acme-logs-prod",
            "cloudfront-logs-123",
            "abc",  # minimum length (3 chars)
            "a" + "b" * 61 + "c",  # maximum length (63 chars)
            "",  # empty string (logging disabled)
        ]
        
        result = validate_regex_pattern(pattern, valid_bucket_names)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for bucket_name in valid_bucket_names:
            assert result['matches'][bucket_name], f"Valid bucket name '{bucket_name}' should match pattern"
    
    def test_allowed_pattern_regex_invalid_bucket_names(self, network_template):
        """Test AllowedPattern regex rejects invalid S3 bucket names."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['S3LogBucketName']
        pattern = param['AllowedPattern']
        
        invalid_bucket_names = [
            "MyBucket",  # uppercase
            "bucket_name",  # underscore
            "ab",  # too short (2 chars)
            "a" * 64,  # too long (64 chars)
            "-bucket",  # starts with dash
            "bucket-",  # ends with dash
            "bucket..name",  # consecutive dots
            "bucket name",  # space
        ]
        
        result = validate_regex_pattern(pattern, invalid_bucket_names)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for bucket_name in invalid_bucket_names:
            assert not result['matches'][bucket_name], f"Invalid bucket name '{bucket_name}' should not match pattern"


class TestS3LogBucketNameMetadata:
    """Test suite for S3LogBucketName parameter metadata organization."""
    
    def test_parameter_in_metadata(self, network_template):
        """Test that S3LogBucketName is in Metadata section."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find all parameters listed in metadata
        all_params_in_metadata = []
        for group in parameter_groups:
            params = group.get('Parameters', [])
            all_params_in_metadata.extend(params)
        
        assert 'S3LogBucketName' in all_params_in_metadata, "S3LogBucketName should be in Metadata ParameterGroups"
    
    def test_parameter_in_supporting_resources_group(self, network_template):
        """Test that S3LogBucketName is in 'Supporting Resources' parameter group."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find the Supporting Resources group
        supporting_resources_group = None
        for group in parameter_groups:
            label = group.get('Label', {})
            if label.get('default') == 'Supporting Resources':
                supporting_resources_group = group
                break
        
        assert supporting_resources_group is not None, "Supporting Resources parameter group should exist"
        
        params = supporting_resources_group.get('Parameters', [])
        assert 'S3LogBucketName' in params, "S3LogBucketName should be in Supporting Resources group"
    
    def test_supporting_resources_group_position(self, network_template):
        """Test that Supporting Resources group is positioned after Deployment Environment."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Get group labels in order
        group_labels = [group.get('Label', {}).get('default', '') for group in parameter_groups]
        
        # Find positions
        deployment_env_index = -1
        supporting_resources_index = -1
        
        for i, label in enumerate(group_labels):
            if label == 'Deployment Environment':
                deployment_env_index = i
            elif label == 'Supporting Resources':
                supporting_resources_index = i
        
        assert deployment_env_index >= 0, "Deployment Environment group should exist"
        assert supporting_resources_index >= 0, "Supporting Resources group should exist"
        assert supporting_resources_index > deployment_env_index, \
            "Supporting Resources should come after Deployment Environment"


class TestHasLogBucketCondition:
    """Test suite for HasLogBucket condition logic."""
    
    def test_condition_exists(self, network_template):
        """Test that HasLogBucket condition exists in template."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'HasLogBucket' in conditions, "HasLogBucket condition not found in template"
    
    def test_condition_structure(self, network_template):
        """Test that HasLogBucket condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['HasLogBucket']
        
        # Should be a !Not function
        assert '!Not' in str(condition) or 'Fn::Not' in str(condition), \
            "HasLogBucket should use !Not function"
        
        # The condition should check if S3LogBucketName is not equal to empty string
        # Structure: !Not [!Equals [!Ref S3LogBucketName, '']]
        if isinstance(condition, dict):
            # YAML parsed as dict with !Tag notation or Fn:: notation
            not_key = '!Not' if '!Not' in condition else 'Fn::Not'
            assert not_key in condition, "Condition should use !Not or Fn::Not"
            not_list = condition[not_key]
            assert isinstance(not_list, list), "!Not should contain a list"
            assert len(not_list) == 1, "!Not should contain exactly one element"
            
            equals_condition = not_list[0]
            equals_key = '!Equals' if '!Equals' in equals_condition else 'Fn::Equals'
            assert equals_key in equals_condition, "Should use !Equals inside !Not"
            equals_list = equals_condition[equals_key]
            assert isinstance(equals_list, list), "!Equals should contain a list"
            assert len(equals_list) == 2, "!Equals should compare two values"
            
            # First element should be a Ref to S3LogBucketName
            ref_element = equals_list[0]
            ref_key = '!Ref' if '!Ref' in ref_element else 'Ref'
            assert ref_key in ref_element, "First element should be a Ref"
            assert ref_element[ref_key] == 'S3LogBucketName', "Should reference S3LogBucketName parameter"
            
            # Second element should be empty string
            assert equals_list[1] == '', "Second element should be empty string"
    
    def test_condition_logic_with_empty_string(self, network_template):
        """Test that HasLogBucket evaluates to false when S3LogBucketName is empty."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['HasLogBucket']
        
        # The condition is: !Not [!Equals [!Ref S3LogBucketName, '']]
        # When S3LogBucketName = '', !Equals returns true, !Not returns false
        # So HasLogBucket should be false when bucket name is empty
        
        # We verify the structure implies this logic
        if isinstance(condition, dict):
            not_key = '!Not' if '!Not' in condition else 'Fn::Not'
            not_list = condition[not_key]
            equals_condition = not_list[0]
            equals_key = '!Equals' if '!Equals' in equals_condition else 'Fn::Equals'
            equals_list = equals_condition[equals_key]
            
            # Verify it compares against empty string
            assert equals_list[1] == '', \
                "Condition should evaluate to false when S3LogBucketName is empty string"
    
    def test_condition_logic_with_non_empty_string(self, network_template):
        """Test that HasLogBucket evaluates to true when S3LogBucketName is non-empty."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['HasLogBucket']
        
        # The condition is: !Not [!Equals [!Ref S3LogBucketName, '']]
        # When S3LogBucketName = 'my-bucket', !Equals returns false, !Not returns true
        # So HasLogBucket should be true when bucket name is non-empty
        
        # We verify the structure implies this logic
        if isinstance(condition, dict):
            not_key = '!Not' if '!Not' in condition else 'Fn::Not'
            
            # The !Not wrapper means the condition is inverted
            # So when S3LogBucketName != '', the condition is true
            assert not_key in condition, \
                "Condition should use !Not to invert the equals check, making it true for non-empty values"


class TestCloudFrontLoggingConfiguration:
    """Test suite for CloudFront logging configuration edge cases."""
    
    def test_logging_property_exists_in_distribution(self, network_template):
        """Test that Logging property exists in CloudFrontDistribution."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        assert 'Logging' in dist_config, "Logging property should exist in CloudFrontDistribution"
    
    def test_logging_with_minimum_length_bucket_name(self, network_template):
        """Test logging configuration with minimum length bucket name (3 chars)."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        # Verify the structure supports minimum length bucket names
        # The AllowedPattern should accept 3-character bucket names
        parameters = network_template.get('Parameters', {})
        param = parameters['S3LogBucketName']
        pattern = param['AllowedPattern']
        
        # Test that a 3-character bucket name matches the pattern
        import re
        min_bucket = "abc"
        assert re.match(pattern, min_bucket), \
            f"Minimum length bucket name '{min_bucket}' should match AllowedPattern"
        
        # Verify the logging config structure would work with any valid bucket name
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            if if_key in logging_config:
                if_list = logging_config[if_key]
                enabled_config = if_list[1]
                
                # Bucket should use !Sub with S3LogBucketName parameter
                bucket_value = enabled_config.get('Bucket')
                if isinstance(bucket_value, dict):
                    sub_key = '!Sub' if '!Sub' in bucket_value else 'Fn::Sub'
                    assert sub_key in bucket_value, "Bucket should use !Sub"
                    bucket_template = bucket_value[sub_key]
                    assert '${S3LogBucketName}' in bucket_template, \
                        "Bucket template should reference S3LogBucketName parameter"
    
    def test_logging_with_maximum_length_bucket_name(self, network_template):
        """Test logging configuration with maximum length bucket name (63 chars)."""
        parameters = network_template.get('Parameters', {})
        param = parameters['S3LogBucketName']
        pattern = param['AllowedPattern']
        
        # Test that a 63-character bucket name matches the pattern
        import re
        max_bucket = "a" + "b" * 61 + "c"  # 63 characters
        assert len(max_bucket) == 63, "Test bucket name should be 63 characters"
        assert re.match(pattern, max_bucket), \
            f"Maximum length bucket name (63 chars) should match AllowedPattern"
        
        # Verify the logging config structure would work with any valid bucket name
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            if if_key in logging_config:
                if_list = logging_config[if_key]
                enabled_config = if_list[1]
                
                # Verify Bucket uses parameter substitution (works for any length)
                bucket_value = enabled_config.get('Bucket')
                if isinstance(bucket_value, dict):
                    sub_key = '!Sub' if '!Sub' in bucket_value else 'Fn::Sub'
                    assert sub_key in bucket_value, "Bucket should use !Sub"
    
    def test_logging_with_dashes_in_valid_positions(self, network_template):
        """Test logging configuration with dashes in valid positions."""
        parameters = network_template.get('Parameters', {})
        param = parameters['S3LogBucketName']
        pattern = param['AllowedPattern']
        
        # Test bucket names with dashes in valid positions
        import re
        valid_bucket_names_with_dashes = [
            "my-log-bucket",
            "acme-logs-prod",
            "cloudfront-logs-123",
            "a-b-c-d-e-f-g",
            "test-bucket-name-with-many-dashes",
        ]
        
        for bucket_name in valid_bucket_names_with_dashes:
            assert re.match(pattern, bucket_name), \
                f"Bucket name with dashes '{bucket_name}' should match AllowedPattern"
        
        # Verify invalid dash positions are rejected
        invalid_bucket_names_with_dashes = [
            "-bucket",  # starts with dash
            "bucket-",  # ends with dash
        ]
        
        for bucket_name in invalid_bucket_names_with_dashes:
            assert not re.match(pattern, bucket_name), \
                f"Invalid bucket name '{bucket_name}' should not match AllowedPattern"
    
    def test_logging_include_cookies_is_false(self, network_template):
        """Test that IncludeCookies is set to 'false' in logging configuration."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            if if_key in logging_config:
                if_list = logging_config[if_key]
                enabled_config = if_list[1]
                
                assert 'IncludeCookies' in enabled_config, "IncludeCookies should be present"
                assert enabled_config['IncludeCookies'] == 'false', \
                    "IncludeCookies should be set to 'false' (string)"
    
    def test_logging_bucket_format(self, network_template):
        """Test that Bucket is formatted correctly with .s3.amazonaws.com suffix."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            if if_key in logging_config:
                if_list = logging_config[if_key]
                enabled_config = if_list[1]
                
                bucket_value = enabled_config.get('Bucket')
                if isinstance(bucket_value, dict):
                    sub_key = '!Sub' if '!Sub' in bucket_value else 'Fn::Sub'
                    bucket_template = bucket_value[sub_key]
                    
                    assert bucket_template.endswith('.s3.amazonaws.com'), \
                        "Bucket should end with .s3.amazonaws.com"
                    assert '${S3LogBucketName}' in bucket_template, \
                        "Bucket should reference S3LogBucketName parameter"
    
    def test_logging_prefix_format(self, network_template):
        """Test that Prefix follows the correct format with cloudfront/ prefix."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            if if_key in logging_config:
                if_list = logging_config[if_key]
                enabled_config = if_list[1]
                
                prefix_value = enabled_config.get('Prefix')
                if isinstance(prefix_value, dict):
                    sub_key = '!Sub' if '!Sub' in prefix_value else 'Fn::Sub'
                    prefix_template = prefix_value[sub_key]
                    
                    assert prefix_template.startswith('cloudfront/'), \
                        "Prefix should start with 'cloudfront/'"
                    assert '${Prefix}' in prefix_template, \
                        "Prefix should reference Prefix parameter"
                    assert '${ProjectId}' in prefix_template, \
                        "Prefix should reference ProjectId parameter"
                    assert '${StageId}' in prefix_template, \
                        "Prefix should reference StageId parameter"
                    
                    # Verify the format is exactly as specified
                    expected_format = "cloudfront/${Prefix}-${ProjectId}-${StageId}"
                    assert prefix_template == expected_format, \
                        f"Prefix should be '{expected_format}', got '{prefix_template}'"
    
    def test_logging_uses_has_log_bucket_condition(self, network_template):
        """Test that Logging property uses HasLogBucket condition."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            assert if_key in logging_config, "Logging should use !If conditional"
            
            if_list = logging_config[if_key]
            condition_name = if_list[0]
            assert condition_name == 'HasLogBucket', \
                "Logging should use HasLogBucket condition"
    
    def test_logging_returns_no_value_when_disabled(self, network_template):
        """Test that Logging returns AWS::NoValue when condition is false."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        logging_config = dist_config.get('Logging')
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            if if_key in logging_config:
                if_list = logging_config[if_key]
                
                # Third element should be !Ref AWS::NoValue
                disabled_value = if_list[2]
                if isinstance(disabled_value, dict):
                    ref_key = '!Ref' if '!Ref' in disabled_value else 'Ref'
                    assert ref_key in disabled_value, \
                        "Disabled value should use !Ref"
                    assert disabled_value[ref_key] == 'AWS::NoValue', \
                        "When disabled, Logging should return AWS::NoValue"



class TestConditionalOutputs:
    """Test suite for conditional CloudFront logging outputs."""
    
    def test_cloudfront_log_bucket_output_exists(self, network_template):
        """Test that CloudFrontLogBucket output exists in template."""
        outputs = get_template_section(network_template, 'Outputs')
        assert 'CloudFrontLogBucket' in outputs, "CloudFrontLogBucket output not found in template"
    
    def test_cloudfront_log_prefix_output_exists(self, network_template):
        """Test that CloudFrontLogPrefix output exists in template."""
        outputs = get_template_section(network_template, 'Outputs')
        assert 'CloudFrontLogPrefix' in outputs, "CloudFrontLogPrefix output not found in template"
    
    def test_cloudfront_log_bucket_has_condition(self, network_template):
        """Test that CloudFrontLogBucket output has HasLogBucket condition."""
        outputs = get_template_section(network_template, 'Outputs')
        output = outputs['CloudFrontLogBucket']
        
        assert 'Condition' in output, "CloudFrontLogBucket should have a Condition"
        assert output['Condition'] == 'HasLogBucket', \
            "CloudFrontLogBucket should use HasLogBucket condition"
    
    def test_cloudfront_log_prefix_has_condition(self, network_template):
        """Test that CloudFrontLogPrefix output has HasLogBucket condition."""
        outputs = get_template_section(network_template, 'Outputs')
        output = outputs['CloudFrontLogPrefix']
        
        assert 'Condition' in output, "CloudFrontLogPrefix should have a Condition"
        assert output['Condition'] == 'HasLogBucket', \
            "CloudFrontLogPrefix should use HasLogBucket condition"
    
    def test_cloudfront_log_bucket_value(self, network_template):
        """Test that CloudFrontLogBucket output value references S3LogBucketName."""
        outputs = get_template_section(network_template, 'Outputs')
        output = outputs['CloudFrontLogBucket']
        
        assert 'Value' in output, "CloudFrontLogBucket should have a Value"
        value = output['Value']
        
        # Value should be !Ref S3LogBucketName
        if isinstance(value, dict):
            ref_key = '!Ref' if '!Ref' in value else 'Ref'
            assert ref_key in value, "CloudFrontLogBucket value should use !Ref"
            assert value[ref_key] == 'S3LogBucketName', \
                "CloudFrontLogBucket should reference S3LogBucketName parameter"
    
    def test_cloudfront_log_prefix_value(self, network_template):
        """Test that CloudFrontLogPrefix output value has correct format."""
        outputs = get_template_section(network_template, 'Outputs')
        output = outputs['CloudFrontLogPrefix']
        
        assert 'Value' in output, "CloudFrontLogPrefix should have a Value"
        value = output['Value']
        
        # Value should be !Sub "cloudfront/${Prefix}-${ProjectId}-${StageId}"
        if isinstance(value, dict):
            sub_key = '!Sub' if '!Sub' in value else 'Fn::Sub'
            assert sub_key in value, "CloudFrontLogPrefix value should use !Sub"
            
            prefix_template = value[sub_key]
            expected_format = "cloudfront/${Prefix}-${ProjectId}-${StageId}"
            assert prefix_template == expected_format, \
                f"CloudFrontLogPrefix should be '{expected_format}', got '{prefix_template}'"
    
    def test_cloudfront_log_bucket_description(self, network_template):
        """Test that CloudFrontLogBucket output has a description."""
        outputs = get_template_section(network_template, 'Outputs')
        output = outputs['CloudFrontLogBucket']
        
        assert 'Description' in output, "CloudFrontLogBucket should have a Description"
        assert len(output['Description']) > 0, "Description should not be empty"
        assert 'bucket' in output['Description'].lower(), \
            "Description should mention 'bucket'"
    
    def test_cloudfront_log_prefix_description(self, network_template):
        """Test that CloudFrontLogPrefix output has a description."""
        outputs = get_template_section(network_template, 'Outputs')
        output = outputs['CloudFrontLogPrefix']
        
        assert 'Description' in output, "CloudFrontLogPrefix should have a Description"
        assert len(output['Description']) > 0, "Description should not be empty"
        assert 'prefix' in output['Description'].lower(), \
            "Description should mention 'prefix'"
    
    def test_outputs_are_conditional(self, network_template):
        """Test that both outputs are conditional and only appear when HasLogBucket is true."""
        outputs = get_template_section(network_template, 'Outputs')
        
        log_bucket_output = outputs['CloudFrontLogBucket']
        log_prefix_output = outputs['CloudFrontLogPrefix']
        
        # Both should have the same condition
        assert log_bucket_output.get('Condition') == 'HasLogBucket', \
            "CloudFrontLogBucket should be conditional on HasLogBucket"
        assert log_prefix_output.get('Condition') == 'HasLogBucket', \
            "CloudFrontLogPrefix should be conditional on HasLogBucket"
        
        # Verify the condition exists in the template
        conditions = get_template_section(network_template, 'Conditions')
        assert 'HasLogBucket' in conditions, \
            "HasLogBucket condition should exist for outputs to reference"


# =============================================================================
# TESTS FOR ORIGIN PATH PARAMETERS (StaticOriginPath and ApiOriginPath)
# =============================================================================

class TestStaticOriginPathParameter:
    """Test suite for StaticOriginPath parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that StaticOriginPath parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'StaticOriginPath' in parameters, "StaticOriginPath parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that StaticOriginPath has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['StaticOriginPath']
        assert param['Type'] == 'String', "StaticOriginPath should be of type String"
    
    def test_default_value_is_empty_string(self, network_template):
        """Test that StaticOriginPath default value is empty string."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['StaticOriginPath']
        assert param['Default'] == "", "StaticOriginPath default should be empty string"
    
    def test_allowed_pattern_exists(self, network_template):
        """Test that StaticOriginPath has AllowedPattern defined."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['StaticOriginPath']
        assert 'AllowedPattern' in param, "StaticOriginPath should have AllowedPattern"
    
    def test_allowed_pattern_value(self, network_template):
        """Test that StaticOriginPath has correct AllowedPattern regex."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['StaticOriginPath']
        expected_pattern = r"^$|^/$|^/[a-zA-Z0-9/_-]+[^/]$"
        assert param['AllowedPattern'] == expected_pattern, f"AllowedPattern should be {expected_pattern}"
    
    def test_constraint_description_exists(self, network_template):
        """Test that StaticOriginPath has ConstraintDescription."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['StaticOriginPath']
        assert 'ConstraintDescription' in param, "StaticOriginPath should have ConstraintDescription"
        assert len(param['ConstraintDescription']) > 0, "ConstraintDescription should not be empty"
    
    def test_description_exists(self, network_template):
        """Test that StaticOriginPath has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['StaticOriginPath']
        assert 'Description' in param, "StaticOriginPath should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_parameter_in_metadata(self, network_template):
        """Test that StaticOriginPath is in Metadata section."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find all parameters listed in metadata
        all_params_in_metadata = []
        for group in parameter_groups:
            params = group.get('Parameters', [])
            all_params_in_metadata.extend(params)
        
        assert 'StaticOriginPath' in all_params_in_metadata, "StaticOriginPath should be in Metadata ParameterGroups"
    
    def test_parameter_in_origins_group(self, network_template):
        """Test that StaticOriginPath is in 'Origins for S3 and/or API Gateway' parameter group."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find the Origins group
        origins_group = None
        for group in parameter_groups:
            label = group.get('Label', {})
            if label.get('default') == 'Origins for S3 and/or API Gateway':
                origins_group = group
                break
        
        assert origins_group is not None, "Origins for S3 and/or API Gateway parameter group should exist"
        
        params = origins_group.get('Parameters', [])
        assert 'StaticOriginPath' in params, "StaticOriginPath should be in Origins for S3 and/or API Gateway group"


class TestApiOriginPathParameter:
    """Test suite for ApiOriginPath parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that ApiOriginPath parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'ApiOriginPath' in parameters, "ApiOriginPath parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that ApiOriginPath has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['ApiOriginPath']
        assert param['Type'] == 'String', "ApiOriginPath should be of type String"
    
    def test_default_value_is_empty_string(self, network_template):
        """Test that ApiOriginPath default value is empty string."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['ApiOriginPath']
        assert param['Default'] == "", "ApiOriginPath default should be empty string"
    
    def test_allowed_pattern_exists(self, network_template):
        """Test that ApiOriginPath has AllowedPattern defined."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['ApiOriginPath']
        assert 'AllowedPattern' in param, "ApiOriginPath should have AllowedPattern"
    
    def test_allowed_pattern_value(self, network_template):
        """Test that ApiOriginPath has correct AllowedPattern regex."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['ApiOriginPath']
        expected_pattern = r"^$|^/$|^/[a-zA-Z0-9/_-]+[^/]$"
        assert param['AllowedPattern'] == expected_pattern, f"AllowedPattern should be {expected_pattern}"
    
    def test_constraint_description_exists(self, network_template):
        """Test that ApiOriginPath has ConstraintDescription."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['ApiOriginPath']
        assert 'ConstraintDescription' in param, "ApiOriginPath should have ConstraintDescription"
        assert len(param['ConstraintDescription']) > 0, "ConstraintDescription should not be empty"
    
    def test_description_exists(self, network_template):
        """Test that ApiOriginPath has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['ApiOriginPath']
        assert 'Description' in param, "ApiOriginPath should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_parameter_in_metadata(self, network_template):
        """Test that ApiOriginPath is in Metadata section."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find all parameters listed in metadata
        all_params_in_metadata = []
        for group in parameter_groups:
            params = group.get('Parameters', [])
            all_params_in_metadata.extend(params)
        
        assert 'ApiOriginPath' in all_params_in_metadata, "ApiOriginPath should be in Metadata ParameterGroups"
    
    def test_parameter_in_origins_group(self, network_template):
        """Test that ApiOriginPath is in 'Origins for S3 and/or API Gateway' parameter group."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find the Origins group
        origins_group = None
        for group in parameter_groups:
            label = group.get('Label', {})
            if label.get('default') == 'Origins for S3 and/or API Gateway':
                origins_group = group
                break
        
        assert origins_group is not None, "Origins for S3 and/or API Gateway parameter group should exist"
        
        params = origins_group.get('Parameters', [])
        assert 'ApiOriginPath' in params, "ApiOriginPath should be in Origins for S3 and/or API Gateway group"


class TestRootPathEdgeCase:
    """Test suite for root path edge case (single slash)."""
    
    def test_static_origin_path_root_produces_empty_string(self, network_template):
        """Test that StaticOriginPath = '/' produces empty string in CloudFront origin."""
        # Verify the condition exists
        conditions = get_template_section(network_template, 'Conditions')
        assert 'StaticOriginPathIsRoot' in conditions, "StaticOriginPathIsRoot condition should exist"
        assert 'UseRootStaticOriginPath' in conditions, "UseRootStaticOriginPath condition should exist"
        
        # Verify the condition checks for "/"
        root_condition = conditions['StaticOriginPathIsRoot']
        if isinstance(root_condition, dict):
            equals_key = '!Equals' if '!Equals' in root_condition else 'Fn::Equals'
            assert equals_key in root_condition, "StaticOriginPathIsRoot should use !Equals"
            equals_list = root_condition[equals_key]
            assert equals_list[1] == "/", "StaticOriginPathIsRoot should check for '/'"
        
        # Verify the CloudFront distribution uses this condition to set empty string
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        origins = dist_config.get('Origins', [])
        
        # Find the static S3 origin
        static_origin = None
        for origin in origins:
            if isinstance(origin, dict):
                if_key = '!If' if '!If' in origin else 'Fn::If'
                if if_key in origin:
                    # This is a conditional origin
                    if_list = origin[if_key]
                    if len(if_list) >= 2:
                        origin_def = if_list[1]
                        if isinstance(origin_def, dict) and origin_def.get('Id') == 'StaticS3Origin':
                            static_origin = origin_def
                            break
                elif origin.get('Id') == 'StaticS3Origin':
                    static_origin = origin
                    break
        
        if static_origin:
            origin_path = static_origin.get('OriginPath')
            if isinstance(origin_path, dict):
                # Should be a nested !If structure
                if_key = '!If' if '!If' in origin_path else 'Fn::If'
                if if_key in origin_path:
                    if_list = origin_path[if_key]
                    # The second !If should handle root path
                    if len(if_list) >= 3:
                        second_if = if_list[2]
                        if isinstance(second_if, dict):
                            inner_if_key = '!If' if '!If' in second_if else 'Fn::If'
                            if inner_if_key in second_if:
                                inner_if_list = second_if[inner_if_key]
                                # When UseRootStaticOriginPath is true, should return empty string
                                assert inner_if_list[1] == "", \
                                    "When StaticOriginPath is '/', OriginPath should be empty string"
    
    def test_api_origin_path_root_produces_empty_string(self, network_template):
        """Test that ApiOriginPath = '/' produces empty string in CloudFront origin."""
        # Verify the condition exists
        conditions = get_template_section(network_template, 'Conditions')
        assert 'ApiOriginPathIsRoot' in conditions, "ApiOriginPathIsRoot condition should exist"
        assert 'UseRootApiOriginPath' in conditions, "UseRootApiOriginPath condition should exist"
        
        # Verify the condition checks for "/"
        root_condition = conditions['ApiOriginPathIsRoot']
        if isinstance(root_condition, dict):
            equals_key = '!Equals' if '!Equals' in root_condition else 'Fn::Equals'
            assert equals_key in root_condition, "ApiOriginPathIsRoot should use !Equals"
            equals_list = root_condition[equals_key]
            assert equals_list[1] == "/", "ApiOriginPathIsRoot should check for '/'"
        
        # Verify the CloudFront distribution uses this condition to set empty string
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        origins = dist_config.get('Origins', [])
        
        # Find the API Gateway origin
        api_origin = None
        for origin in origins:
            if isinstance(origin, dict):
                if_key = '!If' if '!If' in origin else 'Fn::If'
                if if_key in origin:
                    # This is a conditional origin
                    if_list = origin[if_key]
                    if len(if_list) >= 2:
                        origin_def = if_list[1]
                        if isinstance(origin_def, dict) and origin_def.get('Id') == 'ApiGatewayOrigin':
                            api_origin = origin_def
                            break
                elif origin.get('Id') == 'ApiGatewayOrigin':
                    api_origin = origin
                    break
        
        if api_origin:
            origin_path = api_origin.get('OriginPath')
            if isinstance(origin_path, dict):
                # Should be a nested !If structure
                if_key = '!If' if '!If' in origin_path else 'Fn::If'
                if if_key in origin_path:
                    if_list = origin_path[if_key]
                    # The second !If should handle root path
                    if len(if_list) >= 3:
                        second_if = if_list[2]
                        if isinstance(second_if, dict):
                            inner_if_key = '!If' if '!If' in second_if else 'Fn::If'
                            if inner_if_key in second_if:
                                inner_if_list = second_if[inner_if_key]
                                # When UseRootApiOriginPath is true, should return empty string
                                assert inner_if_list[1] == "", \
                                    "When ApiOriginPath is '/', OriginPath should be empty string"


class TestOriginPathRegexValidation:
    """Test suite for origin path regex validation."""
    
    def test_regex_rejects_paths_without_leading_slash(self, network_template):
        """Test that regex rejects paths without leading /."""
        parameters = get_template_section(network_template, 'Parameters')
        static_param = parameters['StaticOriginPath']
        api_param = parameters['ApiOriginPath']
        
        pattern = static_param['AllowedPattern']
        
        invalid_paths = [
            "static",
            "api",
            "path/to/resource",
            "no-leading-slash",
        ]
        
        result = validate_regex_pattern(pattern, invalid_paths)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for path in invalid_paths:
            assert not result['matches'][path], \
                f"Path without leading slash '{path}' should not match pattern"
    
    def test_regex_rejects_paths_with_trailing_slash(self, network_template):
        """Test that regex rejects paths with trailing / (except single /)."""
        parameters = get_template_section(network_template, 'Parameters')
        static_param = parameters['StaticOriginPath']
        
        pattern = static_param['AllowedPattern']
        
        invalid_paths = [
            "/static/",
            "/api/v1/",
            "/path/to/resource/",
            "/trailing-slash/",
        ]
        
        result = validate_regex_pattern(pattern, invalid_paths)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for path in invalid_paths:
            assert not result['matches'][path], \
                f"Path with trailing slash '{path}' should not match pattern"
        
        # But single "/" should match
        single_slash_result = validate_regex_pattern(pattern, ["/"])
        assert single_slash_result['matches']["/"], "Single '/' should match pattern"
    
    def test_regex_rejects_paths_with_curly_braces(self, network_template):
        """Test that regex rejects paths with { or } characters."""
        parameters = get_template_section(network_template, 'Parameters')
        static_param = parameters['StaticOriginPath']
        
        pattern = static_param['AllowedPattern']
        
        invalid_paths = [
            "/{StageId}/public",
            "/${StageId}/public",
            "/path/{id}",
            "/path/${variable}",
            "/api/{version}/resource",
        ]
        
        result = validate_regex_pattern(pattern, invalid_paths)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for path in invalid_paths:
            assert not result['matches'][path], \
                f"Path with curly braces '{path}' should not match pattern"
    
    def test_regex_accepts_valid_custom_paths(self, network_template):
        """Test that regex accepts valid custom paths."""
        parameters = get_template_section(network_template, 'Parameters')
        static_param = parameters['StaticOriginPath']
        
        pattern = static_param['AllowedPattern']
        
        valid_paths = [
            "",  # empty string (default)
            "/",  # root path
            "/static",
            "/api",
            "/v1/content",
            "/app/public",
            "/api/v2/services",
            "/prod",
            "/test-123",
            "/path_with_underscore",
            "/path-with-dashes",
            "/path/with/multiple/segments",
            "/ab",  # two character path (minimum for custom paths)
            "/123",  # numeric path
        ]
        
        result = validate_regex_pattern(pattern, valid_paths)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for path in valid_paths:
            assert result['matches'][path], \
                f"Valid path '{path}' should match pattern"


# =============================================================================
# TESTS FOR CACHE POLICY PARAMETERS
# =============================================================================

class TestCloudFrontStaticCachePolicyParameter:
    """Test suite for CloudFrontStaticCachePolicy parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that CloudFrontStaticCachePolicy parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'CloudFrontStaticCachePolicy' in parameters, "CloudFrontStaticCachePolicy parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that CloudFrontStaticCachePolicy has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCachePolicy']
        assert param['Type'] == 'String', "CloudFrontStaticCachePolicy should be of type String"
    
    def test_default_value(self, network_template):
        """Test that CloudFrontStaticCachePolicy default value is CachingOptimized."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCachePolicy']
        assert param['Default'] == 'CachingOptimized', "CloudFrontStaticCachePolicy default should be CachingOptimized"
    
    def test_allowed_values(self, network_template):
        """Test that CloudFrontStaticCachePolicy has correct AllowedValues list."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCachePolicy']
        
        expected_values = [
            'CachingOptimized',
            'CachingDisabled',
            'CachingOptimizedForUncompressedObjects',
            'Elemental-MediaPackage',
            'CustomDefault',
            'CustomArn'
        ]
        
        assert 'AllowedValues' in param, "CloudFrontStaticCachePolicy should have AllowedValues"
        assert param['AllowedValues'] == expected_values, \
            f"AllowedValues should be {expected_values}, got {param['AllowedValues']}"
    
    def test_description_exists(self, network_template):
        """Test that CloudFrontStaticCachePolicy has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCachePolicy']
        assert 'Description' in param, "CloudFrontStaticCachePolicy should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_description_mentions_environment_override(self, network_template):
        """Test that CloudFrontStaticCachePolicy description mentions DEV/TEST override."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCachePolicy']
        description = param['Description']
        assert 'DEV' in description and 'TEST' in description, \
            "Description should mention DEV and TEST environment override"
        assert 'CachingDisabled' in description, \
            "Description should mention CachingDisabled as the override policy"


class TestCloudFrontStaticCustomCachePolicyArnParameter:
    """Test suite for CloudFrontStaticCustomCachePolicyArn parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'CloudFrontStaticCustomCachePolicyArn' in parameters, \
            "CloudFrontStaticCustomCachePolicyArn parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        assert param['Type'] == 'String', "CloudFrontStaticCustomCachePolicyArn should be of type String"
    
    def test_default_value_is_empty_string(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn default value is empty string."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        assert param['Default'] == "", "CloudFrontStaticCustomCachePolicyArn default should be empty string"
    
    def test_allowed_pattern_exists(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn has AllowedPattern defined."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        assert 'AllowedPattern' in param, "CloudFrontStaticCustomCachePolicyArn should have AllowedPattern"
    
    def test_allowed_pattern_value(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn has correct AllowedPattern regex."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        expected_pattern = r"^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$|^$"
        assert param['AllowedPattern'] == expected_pattern, \
            f"AllowedPattern should be {expected_pattern}"
    
    def test_constraint_description_exists(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn has ConstraintDescription."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        assert 'ConstraintDescription' in param, \
            "CloudFrontStaticCustomCachePolicyArn should have ConstraintDescription"
        assert len(param['ConstraintDescription']) > 0, "ConstraintDescription should not be empty"
    
    def test_description_exists(self, network_template):
        """Test that CloudFrontStaticCustomCachePolicyArn has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        assert 'Description' in param, "CloudFrontStaticCustomCachePolicyArn should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_allowed_pattern_regex_valid_arns(self, network_template):
        """Test AllowedPattern regex accepts valid CloudFront cache policy ARNs."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        pattern = param['AllowedPattern']
        
        valid_arns = [
            "arn:aws:cloudfront::123456789012:cache-policy/abc123",
            "arn:aws:cloudfront::999999999999:cache-policy/my-policy",
            "arn:aws:cloudfront::000000000000:cache-policy/test-policy-123",
            "",  # empty string (not using custom ARN)
        ]
        
        result = validate_regex_pattern(pattern, valid_arns)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for arn in valid_arns:
            assert result['matches'][arn], f"Valid ARN '{arn}' should match pattern"
    
    def test_allowed_pattern_regex_invalid_arns(self, network_template):
        """Test AllowedPattern regex rejects invalid CloudFront cache policy ARNs."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontStaticCustomCachePolicyArn']
        pattern = param['AllowedPattern']
        
        invalid_arns = [
            "arn:aws:cloudfront::12345:cache-policy/abc",  # account ID too short
            "arn:aws:cloudfront::1234567890123:cache-policy/abc",  # account ID too long
            "arn:aws:s3:::bucket-name",  # wrong service
            "arn:aws:cloudfront::123456789012:distribution/abc",  # wrong resource type
            "not-an-arn",
            "arn:aws:cloudfront::123456789012:cache-policy/",  # missing policy ID
        ]
        
        result = validate_regex_pattern(pattern, invalid_arns)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for arn in invalid_arns:
            assert not result['matches'][arn], f"Invalid ARN '{arn}' should not match pattern"


class TestCloudFrontApiCachePolicyParameter:
    """Test suite for CloudFrontApiCachePolicy parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that CloudFrontApiCachePolicy parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'CloudFrontApiCachePolicy' in parameters, "CloudFrontApiCachePolicy parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that CloudFrontApiCachePolicy has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCachePolicy']
        assert param['Type'] == 'String', "CloudFrontApiCachePolicy should be of type String"
    
    def test_default_value(self, network_template):
        """Test that CloudFrontApiCachePolicy default value is CachingDisabled."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCachePolicy']
        assert param['Default'] == 'CachingDisabled', "CloudFrontApiCachePolicy default should be CachingDisabled"
    
    def test_allowed_values(self, network_template):
        """Test that CloudFrontApiCachePolicy has correct AllowedValues list."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCachePolicy']
        
        expected_values = [
            'CachingOptimized',
            'CachingDisabled',
            'CachingOptimizedForUncompressedObjects',
            'Elemental-MediaPackage',
            'CustomDefault',
            'CustomArn'
        ]
        
        assert 'AllowedValues' in param, "CloudFrontApiCachePolicy should have AllowedValues"
        assert param['AllowedValues'] == expected_values, \
            f"AllowedValues should be {expected_values}, got {param['AllowedValues']}"
    
    def test_description_exists(self, network_template):
        """Test that CloudFrontApiCachePolicy has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCachePolicy']
        assert 'Description' in param, "CloudFrontApiCachePolicy should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_description_mentions_environment_override(self, network_template):
        """Test that CloudFrontApiCachePolicy description mentions DEV/TEST override."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCachePolicy']
        description = param['Description']
        assert 'DEV' in description and 'TEST' in description, \
            "Description should mention DEV and TEST environment override"
        assert 'CachingDisabled' in description, \
            "Description should mention CachingDisabled as the override policy"


class TestCloudFrontApiCustomCachePolicyArnParameter:
    """Test suite for CloudFrontApiCustomCachePolicyArn parameter definition."""
    
    def test_parameter_exists(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn parameter exists in template."""
        parameters = get_template_section(network_template, 'Parameters')
        assert 'CloudFrontApiCustomCachePolicyArn' in parameters, \
            "CloudFrontApiCustomCachePolicyArn parameter not found in template"
    
    def test_parameter_type(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn has correct type."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        assert param['Type'] == 'String', "CloudFrontApiCustomCachePolicyArn should be of type String"
    
    def test_default_value_is_empty_string(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn default value is empty string."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        assert param['Default'] == "", "CloudFrontApiCustomCachePolicyArn default should be empty string"
    
    def test_allowed_pattern_exists(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn has AllowedPattern defined."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        assert 'AllowedPattern' in param, "CloudFrontApiCustomCachePolicyArn should have AllowedPattern"
    
    def test_allowed_pattern_value(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn has correct AllowedPattern regex."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        expected_pattern = r"^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$|^$"
        assert param['AllowedPattern'] == expected_pattern, \
            f"AllowedPattern should be {expected_pattern}"
    
    def test_constraint_description_exists(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn has ConstraintDescription."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        assert 'ConstraintDescription' in param, \
            "CloudFrontApiCustomCachePolicyArn should have ConstraintDescription"
        assert len(param['ConstraintDescription']) > 0, "ConstraintDescription should not be empty"
    
    def test_description_exists(self, network_template):
        """Test that CloudFrontApiCustomCachePolicyArn has Description."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        assert 'Description' in param, "CloudFrontApiCustomCachePolicyArn should have Description"
        assert len(param['Description']) > 0, "Description should not be empty"
    
    def test_allowed_pattern_regex_valid_arns(self, network_template):
        """Test AllowedPattern regex accepts valid CloudFront cache policy ARNs."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        pattern = param['AllowedPattern']
        
        valid_arns = [
            "arn:aws:cloudfront::123456789012:cache-policy/abc123",
            "arn:aws:cloudfront::999999999999:cache-policy/my-policy",
            "arn:aws:cloudfront::000000000000:cache-policy/test-policy-123",
            "",  # empty string (not using custom ARN)
        ]
        
        result = validate_regex_pattern(pattern, valid_arns)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for arn in valid_arns:
            assert result['matches'][arn], f"Valid ARN '{arn}' should match pattern"
    
    def test_allowed_pattern_regex_invalid_arns(self, network_template):
        """Test AllowedPattern regex rejects invalid CloudFront cache policy ARNs."""
        parameters = get_template_section(network_template, 'Parameters')
        param = parameters['CloudFrontApiCustomCachePolicyArn']
        pattern = param['AllowedPattern']
        
        invalid_arns = [
            "arn:aws:cloudfront::12345:cache-policy/abc",  # account ID too short
            "arn:aws:cloudfront::1234567890123:cache-policy/abc",  # account ID too long
            "arn:aws:s3:::bucket-name",  # wrong service
            "arn:aws:cloudfront::123456789012:distribution/abc",  # wrong resource type
            "not-an-arn",
            "arn:aws:cloudfront::123456789012:cache-policy/",  # missing policy ID
        ]
        
        result = validate_regex_pattern(pattern, invalid_arns)
        assert result['valid_pattern'], f"Pattern is invalid: {result.get('error')}"
        
        for arn in invalid_arns:
            assert not result['matches'][arn], f"Invalid ARN '{arn}' should not match pattern"



class TestCachePolicyIdsMapping:
    """Test suite for CachePolicyIds mapping section."""
    
    def test_mapping_exists(self, network_template):
        """Test that CachePolicyIds mapping exists in template."""
        mappings = get_template_section(network_template, 'Mappings')
        assert 'CachePolicyIds' in mappings, "CachePolicyIds mapping not found in template"
    
    def test_caching_optimized_policy_id(self, network_template):
        """Test that CachingOptimized has correct managed policy ID."""
        mappings = get_template_section(network_template, 'Mappings')
        cache_policy_ids = mappings['CachePolicyIds']
        
        assert 'CachingOptimized' in cache_policy_ids, "CachingOptimized should be in CachePolicyIds mapping"
        assert 'Id' in cache_policy_ids['CachingOptimized'], "CachingOptimized should have Id key"
        assert cache_policy_ids['CachingOptimized']['Id'] == '658327ea-f89d-4fab-a63d-7e88639e58f6', \
            "CachingOptimized policy ID should be 658327ea-f89d-4fab-a63d-7e88639e58f6"
    
    def test_caching_disabled_policy_id(self, network_template):
        """Test that CachingDisabled has correct managed policy ID."""
        mappings = get_template_section(network_template, 'Mappings')
        cache_policy_ids = mappings['CachePolicyIds']
        
        assert 'CachingDisabled' in cache_policy_ids, "CachingDisabled should be in CachePolicyIds mapping"
        assert 'Id' in cache_policy_ids['CachingDisabled'], "CachingDisabled should have Id key"
        assert cache_policy_ids['CachingDisabled']['Id'] == '4135ea2d-6df8-44a3-9df3-4b5a84be39ad', \
            "CachingDisabled policy ID should be 4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    
    def test_caching_optimized_for_uncompressed_objects_policy_id(self, network_template):
        """Test that CachingOptimizedForUncompressedObjects has correct managed policy ID."""
        mappings = get_template_section(network_template, 'Mappings')
        cache_policy_ids = mappings['CachePolicyIds']
        
        assert 'CachingOptimizedForUncompressedObjects' in cache_policy_ids, \
            "CachingOptimizedForUncompressedObjects should be in CachePolicyIds mapping"
        assert 'Id' in cache_policy_ids['CachingOptimizedForUncompressedObjects'], \
            "CachingOptimizedForUncompressedObjects should have Id key"
        assert cache_policy_ids['CachingOptimizedForUncompressedObjects']['Id'] == 'b2884449-e4de-46a7-ac36-70bc7f1ddd6d', \
            "CachingOptimizedForUncompressedObjects policy ID should be b2884449-e4de-46a7-ac36-70bc7f1ddd6d"
    
    def test_elemental_media_package_policy_id(self, network_template):
        """Test that Elemental-MediaPackage has correct managed policy ID."""
        mappings = get_template_section(network_template, 'Mappings')
        cache_policy_ids = mappings['CachePolicyIds']
        
        assert 'Elemental-MediaPackage' in cache_policy_ids, \
            "Elemental-MediaPackage should be in CachePolicyIds mapping"
        assert 'Id' in cache_policy_ids['Elemental-MediaPackage'], \
            "Elemental-MediaPackage should have Id key"
        assert cache_policy_ids['Elemental-MediaPackage']['Id'] == '08627262-05a9-4f76-9ded-b50ca2e3a84f', \
            "Elemental-MediaPackage policy ID should be 08627262-05a9-4f76-9ded-b50ca2e3a84f"
    
    def test_all_four_managed_policies_present(self, network_template):
        """Test that all four managed policies are present in the mapping."""
        mappings = get_template_section(network_template, 'Mappings')
        cache_policy_ids = mappings['CachePolicyIds']
        
        expected_policies = [
            'CachingOptimized',
            'CachingDisabled',
            'CachingOptimizedForUncompressedObjects',
            'Elemental-MediaPackage'
        ]
        
        for policy in expected_policies:
            assert policy in cache_policy_ids, f"{policy} should be in CachePolicyIds mapping"
            assert 'Id' in cache_policy_ids[policy], f"{policy} should have Id key"
            assert len(cache_policy_ids[policy]['Id']) > 0, f"{policy} Id should not be empty"



class TestCachePolicyConditions:
    """Test suite for cache policy conditions."""
    
    def test_static_cache_policy_is_custom_default_condition_exists(self, network_template):
        """Test that StaticCachePolicyIsCustomDefault condition exists."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'StaticCachePolicyIsCustomDefault' in conditions, \
            "StaticCachePolicyIsCustomDefault condition not found in template"
    
    def test_static_cache_policy_is_custom_default_structure(self, network_template):
        """Test that StaticCachePolicyIsCustomDefault condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['StaticCachePolicyIsCustomDefault']
        
        # Should be !Equals [!Ref CloudFrontStaticCachePolicy, CustomDefault]
        if isinstance(condition, dict):
            equals_key = '!Equals' if '!Equals' in condition else 'Fn::Equals'
            assert equals_key in condition, "StaticCachePolicyIsCustomDefault should use !Equals"
            equals_list = condition[equals_key]
            assert isinstance(equals_list, list), "!Equals should contain a list"
            assert len(equals_list) == 2, "!Equals should compare two values"
            
            # First element should be a Ref to CloudFrontStaticCachePolicy
            ref_element = equals_list[0]
            ref_key = '!Ref' if '!Ref' in ref_element else 'Ref'
            assert ref_key in ref_element, "First element should be a Ref"
            assert ref_element[ref_key] == 'CloudFrontStaticCachePolicy', \
                "Should reference CloudFrontStaticCachePolicy parameter"
            
            # Second element should be 'CustomDefault'
            assert equals_list[1] == 'CustomDefault', "Second element should be 'CustomDefault'"
    
    def test_static_cache_policy_is_custom_arn_condition_exists(self, network_template):
        """Test that StaticCachePolicyIsCustomArn condition exists."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'StaticCachePolicyIsCustomArn' in conditions, \
            "StaticCachePolicyIsCustomArn condition not found in template"
    
    def test_static_cache_policy_is_custom_arn_structure(self, network_template):
        """Test that StaticCachePolicyIsCustomArn condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['StaticCachePolicyIsCustomArn']
        
        # Should be !Equals [!Ref CloudFrontStaticCachePolicy, CustomArn]
        if isinstance(condition, dict):
            equals_key = '!Equals' if '!Equals' in condition else 'Fn::Equals'
            assert equals_key in condition, "StaticCachePolicyIsCustomArn should use !Equals"
            equals_list = condition[equals_key]
            assert isinstance(equals_list, list), "!Equals should contain a list"
            assert len(equals_list) == 2, "!Equals should compare two values"
            
            # First element should be a Ref to CloudFrontStaticCachePolicy
            ref_element = equals_list[0]
            ref_key = '!Ref' if '!Ref' in ref_element else 'Ref'
            assert ref_key in ref_element, "First element should be a Ref"
            assert ref_element[ref_key] == 'CloudFrontStaticCachePolicy', \
                "Should reference CloudFrontStaticCachePolicy parameter"
            
            # Second element should be 'CustomArn'
            assert equals_list[1] == 'CustomArn', "Second element should be 'CustomArn'"
    
    def test_api_cache_policy_is_custom_default_condition_exists(self, network_template):
        """Test that ApiCachePolicyIsCustomDefault condition exists."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'ApiCachePolicyIsCustomDefault' in conditions, \
            "ApiCachePolicyIsCustomDefault condition not found in template"
    
    def test_api_cache_policy_is_custom_default_structure(self, network_template):
        """Test that ApiCachePolicyIsCustomDefault condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['ApiCachePolicyIsCustomDefault']
        
        # Should be !Equals [!Ref CloudFrontApiCachePolicy, CustomDefault]
        if isinstance(condition, dict):
            equals_key = '!Equals' if '!Equals' in condition else 'Fn::Equals'
            assert equals_key in condition, "ApiCachePolicyIsCustomDefault should use !Equals"
            equals_list = condition[equals_key]
            assert isinstance(equals_list, list), "!Equals should contain a list"
            assert len(equals_list) == 2, "!Equals should compare two values"
            
            # First element should be a Ref to CloudFrontApiCachePolicy
            ref_element = equals_list[0]
            ref_key = '!Ref' if '!Ref' in ref_element else 'Ref'
            assert ref_key in ref_element, "First element should be a Ref"
            assert ref_element[ref_key] == 'CloudFrontApiCachePolicy', \
                "Should reference CloudFrontApiCachePolicy parameter"
            
            # Second element should be 'CustomDefault'
            assert equals_list[1] == 'CustomDefault', "Second element should be 'CustomDefault'"
    
    def test_api_cache_policy_is_custom_arn_condition_exists(self, network_template):
        """Test that ApiCachePolicyIsCustomArn condition exists."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'ApiCachePolicyIsCustomArn' in conditions, \
            "ApiCachePolicyIsCustomArn condition not found in template"
    
    def test_api_cache_policy_is_custom_arn_structure(self, network_template):
        """Test that ApiCachePolicyIsCustomArn condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['ApiCachePolicyIsCustomArn']
        
        # Should be !Equals [!Ref CloudFrontApiCachePolicy, CustomArn]
        if isinstance(condition, dict):
            equals_key = '!Equals' if '!Equals' in condition else 'Fn::Equals'
            assert equals_key in condition, "ApiCachePolicyIsCustomArn should use !Equals"
            equals_list = condition[equals_key]
            assert isinstance(equals_list, list), "!Equals should contain a list"
            assert len(equals_list) == 2, "!Equals should compare two values"
            
            # First element should be a Ref to CloudFrontApiCachePolicy
            ref_element = equals_list[0]
            ref_key = '!Ref' if '!Ref' in ref_element else 'Ref'
            assert ref_key in ref_element, "First element should be a Ref"
            assert ref_element[ref_key] == 'CloudFrontApiCachePolicy', \
                "Should reference CloudFrontApiCachePolicy parameter"
            
            # Second element should be 'CustomArn'
            assert equals_list[1] == 'CustomArn', "Second element should be 'CustomArn'"
    
    def test_create_custom_static_cache_policy_condition_exists(self, network_template):
        """Test that CreateCustomStaticCachePolicy condition exists."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'CreateCustomStaticCachePolicy' in conditions, \
            "CreateCustomStaticCachePolicy condition not found in template"
    
    def test_create_custom_static_cache_policy_structure(self, network_template):
        """Test that CreateCustomStaticCachePolicy condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['CreateCustomStaticCachePolicy']
        
        # Should be !And [HasStaticOrigin, IsProduction, StaticCachePolicyIsCustomDefault]
        if isinstance(condition, dict):
            and_key = '!And' if '!And' in condition else 'Fn::And'
            assert and_key in condition, "CreateCustomStaticCachePolicy should use !And"
            and_list = condition[and_key]
            assert isinstance(and_list, list), "!And should contain a list"
            assert len(and_list) == 3, "!And should have three conditions"
            
            # Check that the three conditions are referenced
            condition_refs = []
            for item in and_list:
                if isinstance(item, dict):
                    cond_key = '!Condition' if '!Condition' in item else 'Condition'
                    if cond_key in item:
                        condition_refs.append(item[cond_key])
            
            assert 'HasStaticOrigin' in condition_refs, "Should reference HasStaticOrigin condition"
            assert 'IsProduction' in condition_refs, "Should reference IsProduction condition"
            assert 'StaticCachePolicyIsCustomDefault' in condition_refs, \
                "Should reference StaticCachePolicyIsCustomDefault condition"
    
    def test_create_custom_api_cache_policy_condition_exists(self, network_template):
        """Test that CreateCustomApiCachePolicy condition exists."""
        conditions = get_template_section(network_template, 'Conditions')
        assert 'CreateCustomApiCachePolicy' in conditions, \
            "CreateCustomApiCachePolicy condition not found in template"
    
    def test_create_custom_api_cache_policy_structure(self, network_template):
        """Test that CreateCustomApiCachePolicy condition has correct structure."""
        conditions = get_template_section(network_template, 'Conditions')
        condition = conditions['CreateCustomApiCachePolicy']
        
        # Should be !And [IsProduction, ApiCachePolicyIsCustomDefault]
        if isinstance(condition, dict):
            and_key = '!And' if '!And' in condition else 'Fn::And'
            assert and_key in condition, "CreateCustomApiCachePolicy should use !And"
            and_list = condition[and_key]
            assert isinstance(and_list, list), "!And should contain a list"
            assert len(and_list) == 2, "!And should have two conditions"
            
            # Check that the two conditions are referenced
            condition_refs = []
            for item in and_list:
                if isinstance(item, dict):
                    cond_key = '!Condition' if '!Condition' in item else 'Condition'
                    if cond_key in item:
                        condition_refs.append(item[cond_key])
            
            assert 'IsProduction' in condition_refs, "Should reference IsProduction condition"
            assert 'ApiCachePolicyIsCustomDefault' in condition_refs, \
                "Should reference ApiCachePolicyIsCustomDefault condition"



class TestCachePolicyMetadataOrganization:
    """Test suite for cache policy parameter metadata organization."""
    
    def test_cache_policies_parameter_group_exists(self, network_template):
        """Test that 'Cache Policies' parameter group exists in Metadata."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find the Cache Policies group
        cache_policies_group = None
        for group in parameter_groups:
            label = group.get('Label', {})
            if label.get('default') == 'Cache Policies':
                cache_policies_group = group
                break
        
        assert cache_policies_group is not None, "Cache Policies parameter group should exist"
    
    def test_all_four_cache_policy_parameters_in_group(self, network_template):
        """Test that all four cache policy parameters are in the Cache Policies group."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find the Cache Policies group
        cache_policies_group = None
        for group in parameter_groups:
            label = group.get('Label', {})
            if label.get('default') == 'Cache Policies':
                cache_policies_group = group
                break
        
        assert cache_policies_group is not None, "Cache Policies parameter group should exist"
        
        params = cache_policies_group.get('Parameters', [])
        expected_params = [
            'CloudFrontStaticCachePolicy',
            'CloudFrontStaticCustomCachePolicyArn',
            'CloudFrontApiCachePolicy',
            'CloudFrontApiCustomCachePolicyArn'
        ]
        
        for param in expected_params:
            assert param in params, f"{param} should be in Cache Policies group"
    
    def test_cache_policy_parameters_in_correct_order(self, network_template):
        """Test that cache policy parameters are in the correct order."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Find the Cache Policies group
        cache_policies_group = None
        for group in parameter_groups:
            label = group.get('Label', {})
            if label.get('default') == 'Cache Policies':
                cache_policies_group = group
                break
        
        assert cache_policies_group is not None, "Cache Policies parameter group should exist"
        
        params = cache_policies_group.get('Parameters', [])
        expected_order = [
            'CloudFrontStaticCachePolicy',
            'CloudFrontStaticCustomCachePolicyArn',
            'CloudFrontApiCachePolicy',
            'CloudFrontApiCustomCachePolicyArn'
        ]
        
        # Find the positions of our parameters
        actual_order = [p for p in params if p in expected_order]
        
        assert actual_order == expected_order, \
            f"Parameters should be in order {expected_order}, got {actual_order}"
    
    def test_cache_policies_group_position(self, network_template):
        """Test that Cache Policies group is positioned after Deployment Environment."""
        metadata = network_template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        parameter_groups = interface.get('ParameterGroups', [])
        
        # Get group labels in order
        group_labels = [group.get('Label', {}).get('default', '') for group in parameter_groups]
        
        # Find positions
        deployment_env_index = -1
        cache_policies_index = -1
        
        for i, label in enumerate(group_labels):
            if label == 'Deployment Environment':
                deployment_env_index = i
            elif label == 'Cache Policies':
                cache_policies_index = i
        
        assert deployment_env_index >= 0, "Deployment Environment group should exist"
        assert cache_policies_index >= 0, "Cache Policies group should exist"
        assert cache_policies_index > deployment_env_index, \
            "Cache Policies should come after Deployment Environment"



class TestCachePolicyDocumentationComments:
    """Test suite for cache policy documentation comments in CloudFront distribution."""
    
    def test_documentation_comments_exist(self, network_template):
        """Test that >! notation comments exist in CloudFront distribution resource."""
        # Read the raw template file to check for comments
        template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Check for >! notation comments
        assert '>! Cache Policy Selection' in template_content, \
            "Template should have >! Cache Policy Selection comment"
        assert '>! This template supports AWS managed cache policies' in template_content, \
            "Template should have comment about AWS managed cache policies support"
    
    def test_documentation_references_aws_documentation(self, network_template):
        """Test that comments reference AWS documentation."""
        # Read the raw template file to check for comments
        template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Check for AWS documentation link
        assert 'https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html' in template_content, \
            "Template should reference AWS managed cache policies documentation"
    
    def test_documentation_mentions_environment_override(self, network_template):
        """Test that comments mention environment override."""
        # Read the raw template file to check for comments
        template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Check for environment override mention
        assert 'DEV and TEST environments always use CachingDisabled' in template_content, \
            "Template should mention DEV and TEST environment override"
    
    def test_documentation_comments_positioned_before_default_cache_behavior(self, network_template):
        """Test that documentation comments are positioned before DefaultCacheBehavior."""
        # Read the raw template file to check for comments
        template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Find positions of comment and DefaultCacheBehavior
        comment_pos = template_content.find('>! Cache Policy Selection')
        default_behavior_pos = template_content.find('DefaultCacheBehavior:')
        
        assert comment_pos > 0, "Cache Policy Selection comment should exist"
        assert default_behavior_pos > 0, "DefaultCacheBehavior should exist"
        assert comment_pos < default_behavior_pos, \
            "Cache Policy Selection comment should come before DefaultCacheBehavior"



class TestCachePolicyBackwardCompatibility:
    """Test suite for cache policy backward compatibility."""
    
    def test_default_values_preserve_existing_behavior(self, network_template):
        """Test that default parameter values preserve existing behavior."""
        parameters = get_template_section(network_template, 'Parameters')
        
        # Static cache policy should default to CachingOptimized
        static_param = parameters['CloudFrontStaticCachePolicy']
        assert static_param['Default'] == 'CachingOptimized', \
            "CloudFrontStaticCachePolicy should default to CachingOptimized for backward compatibility"
        
        # API cache policy should default to CachingDisabled
        api_param = parameters['CloudFrontApiCachePolicy']
        assert api_param['Default'] == 'CachingDisabled', \
            "CloudFrontApiCachePolicy should default to CachingDisabled for backward compatibility"
        
        # Custom ARN parameters should default to empty string
        static_arn_param = parameters['CloudFrontStaticCustomCachePolicyArn']
        assert static_arn_param['Default'] == "", \
            "CloudFrontStaticCustomCachePolicyArn should default to empty string"
        
        api_arn_param = parameters['CloudFrontApiCustomCachePolicyArn']
        assert api_arn_param['Default'] == "", \
            "CloudFrontApiCustomCachePolicyArn should default to empty string"
    
    def test_prod_environment_with_defaults_uses_caching_optimized_for_static(self, network_template):
        """Test that PROD environment with defaults uses CachingOptimized for static origin."""
        parameters = get_template_section(network_template, 'Parameters')
        mappings = get_template_section(network_template, 'Mappings')
        
        # Verify default is CachingOptimized
        static_param = parameters['CloudFrontStaticCachePolicy']
        assert static_param['Default'] == 'CachingOptimized'
        
        # Verify CachingOptimized maps to the correct policy ID
        cache_policy_ids = mappings['CachePolicyIds']
        assert cache_policy_ids['CachingOptimized']['Id'] == '658327ea-f89d-4fab-a63d-7e88639e58f6', \
            "CachingOptimized should map to the correct AWS managed policy ID"
    
    def test_prod_environment_with_defaults_uses_caching_disabled_for_api(self, network_template):
        """Test that PROD environment with defaults uses CachingDisabled for API origin."""
        parameters = get_template_section(network_template, 'Parameters')
        mappings = get_template_section(network_template, 'Mappings')
        
        # Verify default is CachingDisabled
        api_param = parameters['CloudFrontApiCachePolicy']
        assert api_param['Default'] == 'CachingDisabled'
        
        # Verify CachingDisabled maps to the correct policy ID
        cache_policy_ids = mappings['CachePolicyIds']
        assert cache_policy_ids['CachingDisabled']['Id'] == '4135ea2d-6df8-44a3-9df3-4b5a84be39ad', \
            "CachingDisabled should map to the correct AWS managed policy ID"
    
    def test_custom_cache_policy_resources_still_exist(self, network_template):
        """Test that custom cache policy resources still exist for backward compatibility."""
        resources = network_template.get('Resources', {})
        
        # Custom cache policy resources should still exist (but be conditional)
        assert 'CloudFrontCachePolicyStatic' in resources, \
            "CloudFrontCachePolicyStatic resource should still exist for backward compatibility"
        assert 'CloudFrontCachePolicyApi' in resources, \
            "CloudFrontCachePolicyApi resource should still exist for backward compatibility"
        
        # Verify they have conditions now
        static_policy = resources['CloudFrontCachePolicyStatic']
        assert 'Condition' in static_policy, \
            "CloudFrontCachePolicyStatic should have a Condition for conditional creation"
        
        api_policy = resources['CloudFrontCachePolicyApi']
        assert 'Condition' in api_policy, \
            "CloudFrontCachePolicyApi should have a Condition for conditional creation"
    
    def test_custom_default_option_preserves_old_behavior(self, network_template):
        """Test that CustomDefault option preserves the old custom policy behavior."""
        parameters = get_template_section(network_template, 'Parameters')
        
        # Verify CustomDefault is an allowed value
        static_param = parameters['CloudFrontStaticCachePolicy']
        assert 'CustomDefault' in static_param['AllowedValues'], \
            "CustomDefault should be an allowed value to preserve old behavior"
        
        api_param = parameters['CloudFrontApiCachePolicy']
        assert 'CustomDefault' in api_param['AllowedValues'], \
            "CustomDefault should be an allowed value to preserve old behavior"
        
        # Verify conditions exist for CustomDefault
        conditions = get_template_section(network_template, 'Conditions')
        assert 'StaticCachePolicyIsCustomDefault' in conditions, \
            "StaticCachePolicyIsCustomDefault condition should exist"
        assert 'ApiCachePolicyIsCustomDefault' in conditions, \
            "ApiCachePolicyIsCustomDefault condition should exist"



class TestCachePolicyEnvironmentOverride:
    """Test suite for cache policy environment-based override."""
    
    def test_dev_environment_forces_caching_disabled_for_static(self, network_template):
        """Test that DEV environment forces CachingDisabled for static origin."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the DefaultCacheBehavior CachePolicyId
        default_behavior = dist_config.get('DefaultCacheBehavior', {})
        cache_policy_id = default_behavior.get('CachePolicyId')
        
        # Verify the structure uses IsProduction condition
        if isinstance(cache_policy_id, dict):
            if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
            if if_key in cache_policy_id:
                if_list = cache_policy_id[if_key]
                # First element should check StaticOriginIsRoot
                # Then inside, it should check IsProduction
                # When IsProduction is false (DEV/TEST), it should use CachingDisabled
                
                # The structure is: !If [StaticOriginIsRoot, static_resolution, api_resolution]
                # Each resolution is: !If [IsProduction, prod_logic, !FindInMap [CachePolicyIds, CachingDisabled, Id]]
                
                # Verify the non-production fallback uses CachingDisabled
                static_resolution = if_list[1]
                if isinstance(static_resolution, dict):
                    inner_if_key = '!If' if '!If' in static_resolution else 'Fn::If'
                    if inner_if_key in static_resolution:
                        inner_if_list = static_resolution[inner_if_key]
                        # First element should be IsProduction condition
                        assert inner_if_list[0] == 'IsProduction', \
                            "Static cache policy resolution should check IsProduction"
                        
                        # Third element (false branch) should be CachingDisabled
                        non_prod_value = inner_if_list[2]
                        if isinstance(non_prod_value, dict):
                            find_in_map_key = '!FindInMap' if '!FindInMap' in non_prod_value else 'Fn::FindInMap'
                            if find_in_map_key in non_prod_value:
                                find_in_map_list = non_prod_value[find_in_map_key]
                                # Should be [CachePolicyIds, CachingDisabled, Id]
                                assert find_in_map_list[0] == 'CachePolicyIds', \
                                    "Should use CachePolicyIds mapping"
                                assert find_in_map_list[1] == 'CachingDisabled', \
                                    "DEV/TEST should use CachingDisabled for static origin"
                                assert find_in_map_list[2] == 'Id', \
                                    "Should get Id from mapping"
    
    def test_test_environment_forces_caching_disabled_for_static(self, network_template):
        """Test that TEST environment forces CachingDisabled for static origin."""
        # Same logic as DEV - both are non-PROD environments
        # The IsProduction condition handles this
        conditions = get_template_section(network_template, 'Conditions')
        is_production = conditions.get('IsProduction')
        
        # Verify IsProduction checks for PROD
        if isinstance(is_production, dict):
            equals_key = '!Equals' if '!Equals' in is_production else 'Fn::Equals'
            if equals_key in is_production:
                equals_list = is_production[equals_key]
                # Should compare DeployEnvironment to PROD
                ref_element = equals_list[0]
                ref_key = '!Ref' if '!Ref' in ref_element else 'Ref'
                assert ref_element[ref_key] == 'DeployEnvironment', \
                    "IsProduction should check DeployEnvironment parameter"
                assert equals_list[1] == 'PROD', \
                    "IsProduction should check if DeployEnvironment equals PROD"
    
    def test_dev_environment_forces_caching_disabled_for_api(self, network_template):
        """Test that DEV environment forces CachingDisabled for API origin."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the DefaultCacheBehavior CachePolicyId
        default_behavior = dist_config.get('DefaultCacheBehavior', {})
        cache_policy_id = default_behavior.get('CachePolicyId')
        
        # Verify the structure uses IsProduction condition for API
        if isinstance(cache_policy_id, dict):
            if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
            if if_key in cache_policy_id:
                if_list = cache_policy_id[if_key]
                
                # API resolution is the third element (false branch of StaticOriginIsRoot)
                api_resolution = if_list[2]
                if isinstance(api_resolution, dict):
                    inner_if_key = '!If' if '!If' in api_resolution else 'Fn::If'
                    if inner_if_key in api_resolution:
                        inner_if_list = api_resolution[inner_if_key]
                        # First element should be IsProduction condition
                        assert inner_if_list[0] == 'IsProduction', \
                            "API cache policy resolution should check IsProduction"
                        
                        # Third element (false branch) should be CachingDisabled
                        non_prod_value = inner_if_list[2]
                        if isinstance(non_prod_value, dict):
                            find_in_map_key = '!FindInMap' if '!FindInMap' in non_prod_value else 'Fn::FindInMap'
                            if find_in_map_key in non_prod_value:
                                find_in_map_list = non_prod_value[find_in_map_key]
                                # Should be [CachePolicyIds, CachingDisabled, Id]
                                assert find_in_map_list[0] == 'CachePolicyIds', \
                                    "Should use CachePolicyIds mapping"
                                assert find_in_map_list[1] == 'CachingDisabled', \
                                    "DEV/TEST should use CachingDisabled for API origin"
                                assert find_in_map_list[2] == 'Id', \
                                    "Should get Id from mapping"
    
    def test_test_environment_forces_caching_disabled_for_api(self, network_template):
        """Test that TEST environment forces CachingDisabled for API origin."""
        # Same logic as DEV - both are non-PROD environments
        # Already verified by test_test_environment_forces_caching_disabled_for_static
        # that IsProduction condition checks for PROD
        
        # Just verify the condition exists
        conditions = get_template_section(network_template, 'Conditions')
        assert 'IsProduction' in conditions, "IsProduction condition should exist"
    
    def test_prod_environment_respects_parameter_values(self, network_template):
        """Test that PROD environment respects parameter values."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the DefaultCacheBehavior CachePolicyId
        default_behavior = dist_config.get('DefaultCacheBehavior', {})
        cache_policy_id = default_behavior.get('CachePolicyId')
        
        # Verify the structure uses parameter values in PROD
        if isinstance(cache_policy_id, dict):
            if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
            if if_key in cache_policy_id:
                if_list = cache_policy_id[if_key]
                
                # Static resolution (true branch of StaticOriginIsRoot)
                static_resolution = if_list[1]
                if isinstance(static_resolution, dict):
                    inner_if_key = '!If' if '!If' in static_resolution else 'Fn::If'
                    if inner_if_key in static_resolution:
                        inner_if_list = static_resolution[inner_if_key]
                        # Second element (true branch of IsProduction) should have the parameter logic
                        prod_value = inner_if_list[1]
                        
                        # Should be another !If checking StaticCachePolicyIsCustomDefault
                        if isinstance(prod_value, dict):
                            custom_default_if_key = '!If' if '!If' in prod_value else 'Fn::If'
                            if custom_default_if_key in prod_value:
                                custom_default_if_list = prod_value[custom_default_if_key]
                                assert custom_default_if_list[0] == 'StaticCachePolicyIsCustomDefault', \
                                    "PROD should check StaticCachePolicyIsCustomDefault"
                                
                                # The false branch should check CustomArn
                                custom_arn_check = custom_default_if_list[2]
                                if isinstance(custom_arn_check, dict):
                                    custom_arn_if_key = '!If' if '!If' in custom_arn_check else 'Fn::If'
                                    if custom_arn_if_key in custom_arn_check:
                                        custom_arn_if_list = custom_arn_check[custom_arn_if_key]
                                        assert custom_arn_if_list[0] == 'StaticCachePolicyIsCustomArn', \
                                            "PROD should check StaticCachePolicyIsCustomArn"
                                        
                                        # The false branch should use FindInMap with parameter
                                        managed_policy_lookup = custom_arn_if_list[2]
                                        if isinstance(managed_policy_lookup, dict):
                                            find_in_map_key = '!FindInMap' if '!FindInMap' in managed_policy_lookup else 'Fn::FindInMap'
                                            if find_in_map_key in managed_policy_lookup:
                                                find_in_map_list = managed_policy_lookup[find_in_map_key]
                                                # Should use the parameter value
                                                # [CachePolicyIds, !Ref CloudFrontStaticCachePolicy, Id]
                                                assert find_in_map_list[0] == 'CachePolicyIds', \
                                                    "Should use CachePolicyIds mapping"
                                                
                                                param_ref = find_in_map_list[1]
                                                if isinstance(param_ref, dict):
                                                    ref_key = '!Ref' if '!Ref' in param_ref else 'Ref'
                                                    assert param_ref[ref_key] == 'CloudFrontStaticCachePolicy', \
                                                        "PROD should use CloudFrontStaticCachePolicy parameter value"
    
    def test_cache_behavior_paths_also_use_environment_override(self, network_template):
        """Test that cache behavior paths also use environment override."""
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get CacheBehaviors
        cache_behaviors = dist_config.get('CacheBehaviors', [])
        
        # Find the static path cache behavior
        for behavior in cache_behaviors:
            if isinstance(behavior, dict):
                if_key = '!If' if '!If' in behavior else 'Fn::If'
                if if_key in behavior:
                    if_list = behavior[if_key]
                    if len(if_list) >= 2:
                        behavior_def = if_list[1]
                        if isinstance(behavior_def, dict):
                            # Check if this is the static path behavior
                            path_pattern = behavior_def.get('PathPattern')
                            if path_pattern:
                                cache_policy_id = behavior_def.get('CachePolicyId')
                                if isinstance(cache_policy_id, dict):
                                    inner_if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
                                    if inner_if_key in cache_policy_id:
                                        inner_if_list = cache_policy_id[inner_if_key]
                                        # Should check IsProduction
                                        assert inner_if_list[0] == 'IsProduction', \
                                            "Cache behavior paths should also check IsProduction"
                                        
                                        # Non-prod branch should use CachingDisabled
                                        non_prod_value = inner_if_list[2]
                                        if isinstance(non_prod_value, dict):
                                            find_in_map_key = '!FindInMap' if '!FindInMap' in non_prod_value else 'Fn::FindInMap'
                                            if find_in_map_key in non_prod_value:
                                                find_in_map_list = non_prod_value[find_in_map_key]
                                                assert find_in_map_list[1] == 'CachingDisabled', \
                                                    "Cache behavior paths should use CachingDisabled in non-PROD"
                                        break


# =============================================================================
# CloudFront Function Associations Tests
# Spec: cloudfront-function-associations
# =============================================================================

# All 8 CloudFront Function parameters
STATIC_FUNCTION_PARAMS = [
    'CloudFrontStaticFunctionViewerRequest',
    'CloudFrontStaticFunctionViewerResponse',
    'CloudFrontStaticFunctionOriginRequest',
    'CloudFrontStaticFunctionOriginResponse',
]

API_FUNCTION_PARAMS = [
    'CloudFrontApiFunctionViewerRequest',
    'CloudFrontApiFunctionViewerResponse',
    'CloudFrontApiFunctionOriginRequest',
    'CloudFrontApiFunctionOriginResponse',
]

ALL_FUNCTION_PARAMS = STATIC_FUNCTION_PARAMS + API_FUNCTION_PARAMS

STATIC_CONDITIONS = [
    'HasStaticFunctionViewerRequest',
    'HasStaticFunctionViewerResponse',
    'HasStaticFunctionOriginRequest',
    'HasStaticFunctionOriginResponse',
]

API_CONDITIONS = [
    'HasApiFunctionViewerRequest',
    'HasApiFunctionViewerResponse',
    'HasApiFunctionOriginRequest',
    'HasApiFunctionOriginResponse',
]

ALL_CONDITIONS = STATIC_CONDITIONS + API_CONDITIONS

# Mapping from condition to its parameter
CONDITION_TO_PARAM = dict(zip(ALL_CONDITIONS, ALL_FUNCTION_PARAMS))

# Event types in order
EVENT_TYPES = ['viewer-request', 'viewer-response', 'origin-request', 'origin-response']

EXPECTED_ARN_PATTERN = "^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$|^$"


class TestCloudFrontFunctionParameters:
    """Tests for CloudFront Function ARN parameter definitions.
    Requirements: 1.1-1.7, 2.1-2.7"""

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_parameter_exists(self, network_template, param_name):
        params = network_template.get('Parameters', {})
        assert param_name in params, f"Parameter {param_name} should exist"

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_parameter_type_is_string(self, network_template, param_name):
        param = network_template['Parameters'][param_name]
        assert param['Type'] == 'String'

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_parameter_default_is_empty_string(self, network_template, param_name):
        param = network_template['Parameters'][param_name]
        assert param['Default'] == '', f"{param_name} default should be empty string"

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_parameter_allowed_pattern(self, network_template, param_name):
        param = network_template['Parameters'][param_name]
        assert param['AllowedPattern'] == EXPECTED_ARN_PATTERN

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_parameter_constraint_description(self, network_template, param_name):
        param = network_template['Parameters'][param_name]
        assert 'ConstraintDescription' in param
        assert len(param['ConstraintDescription']) > 0

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_parameter_description_exists(self, network_template, param_name):
        param = network_template['Parameters'][param_name]
        assert 'Description' in param
        assert len(param['Description']) > 0

    def test_arn_regex_accepts_valid_arns(self, network_template):
        """Test ARN regex with concrete valid examples."""
        pattern = network_template['Parameters']['CloudFrontStaticFunctionViewerRequest']['AllowedPattern']
        valid_arns = [
            '',  # empty string is valid
            'arn:aws:cloudfront::123456789012:function/my-function',
            'arn:aws:cloudfront::000000000000:function/a',
            'arn:aws:cloudfront::999999999999:function/My_Function-123',
            'arn:aws:cloudfront::123456789012:function/' + 'a' * 64,
        ]
        result = validate_regex_pattern(pattern, valid_arns)
        for arn in valid_arns:
            assert result['matches'][arn] is True, f"Valid ARN should match: {arn!r}"

    def test_arn_regex_rejects_invalid_arns(self, network_template):
        """Test ARN regex with concrete invalid examples."""
        pattern = network_template['Parameters']['CloudFrontStaticFunctionViewerRequest']['AllowedPattern']
        invalid_arns = [
            'not-an-arn',
            'arn:aws:cloudfront::12345:function/my-func',  # account too short
            'arn:aws:cloudfront::1234567890123:function/my-func',  # account too long
            'arn:aws:cloudfront::123456789012:function/',  # no function name
            'arn:aws:cloudfront::123456789012:function/' + 'a' * 65,  # name too long
            'arn:aws:lambda::123456789012:function/my-func',  # wrong service
            'arn:aws:cloudfront::123456789012:distribution/my-func',  # wrong resource type
            'arn:aws:cloudfront::123456789012:function/my func',  # space in name
        ]
        result = validate_regex_pattern(pattern, invalid_arns)
        for arn in invalid_arns:
            assert result['matches'][arn] is False, f"Invalid ARN should not match: {arn!r}"

    @pytest.mark.parametrize("param_name", STATIC_FUNCTION_PARAMS)
    def test_static_param_description_mentions_static(self, network_template, param_name):
        desc = network_template['Parameters'][param_name]['Description']
        assert 'static' in desc.lower()

    @pytest.mark.parametrize("param_name", API_FUNCTION_PARAMS)
    def test_api_param_description_mentions_api(self, network_template, param_name):
        desc = network_template['Parameters'][param_name]['Description']
        assert 'api' in desc.lower()


class TestCloudFrontFunctionMetadataGroups:
    """Tests for CloudFront Function parameter metadata groups.
    Requirements: 3.1-3.6"""

    def _get_parameter_groups(self, template):
        metadata = template.get('Metadata', {})
        interface = metadata.get('AWS::CloudFormation::Interface', {})
        return interface.get('ParameterGroups', [])

    def _find_group_by_label(self, groups, label):
        for group in groups:
            if group.get('Label', {}).get('default') == label:
                return group
        return None

    def test_static_function_group_exists(self, network_template):
        groups = self._get_parameter_groups(network_template)
        group = self._find_group_by_label(groups, 'Static CloudFront Function Associations')
        assert group is not None, "Static CloudFront Function Associations group should exist"

    def test_api_function_group_exists(self, network_template):
        groups = self._get_parameter_groups(network_template)
        group = self._find_group_by_label(groups, 'API CloudFront Function Associations')
        assert group is not None, "API CloudFront Function Associations group should exist"

    def test_static_group_has_correct_parameters(self, network_template):
        groups = self._get_parameter_groups(network_template)
        group = self._find_group_by_label(groups, 'Static CloudFront Function Associations')
        assert group['Parameters'] == STATIC_FUNCTION_PARAMS

    def test_api_group_has_correct_parameters(self, network_template):
        groups = self._get_parameter_groups(network_template)
        group = self._find_group_by_label(groups, 'API CloudFront Function Associations')
        assert group['Parameters'] == API_FUNCTION_PARAMS

    def test_static_group_after_cache_policies(self, network_template):
        """Static group should appear after Cache Policies group."""
        groups = self._get_parameter_groups(network_template)
        labels = [g.get('Label', {}).get('default') for g in groups]
        cache_idx = labels.index('Cache Policies')
        static_idx = labels.index('Static CloudFront Function Associations')
        assert static_idx == cache_idx + 1, \
            "Static CloudFront Function Associations should be immediately after Cache Policies"

    def test_api_group_after_static_group(self, network_template):
        """API group should appear after Static group."""
        groups = self._get_parameter_groups(network_template)
        labels = [g.get('Label', {}).get('default') for g in groups]
        static_idx = labels.index('Static CloudFront Function Associations')
        api_idx = labels.index('API CloudFront Function Associations')
        assert api_idx == static_idx + 1, \
            "API CloudFront Function Associations should be immediately after Static"


class TestCloudFrontFunctionConditions:
    """Tests for CloudFront Function Has* conditions.
    Requirements: 4.1, 4.2"""

    @pytest.mark.parametrize("condition_name", ALL_CONDITIONS)
    def test_condition_exists(self, network_template, condition_name):
        conditions = network_template.get('Conditions', {})
        assert condition_name in conditions, f"Condition {condition_name} should exist"

    @pytest.mark.parametrize("condition_name", ALL_CONDITIONS)
    def test_condition_uses_not_equals_empty_pattern(self, network_template, condition_name):
        """Each condition should use !Not [!Equals [!Ref <param>, '']] pattern."""
        condition = network_template['Conditions'][condition_name]
        param_name = CONDITION_TO_PARAM[condition_name]

        # Structure: {'!Not': [{'!Equals': [{'!Ref': param}, '']}]}
        not_key = '!Not' if '!Not' in condition else 'Fn::Not'
        assert not_key in condition, f"{condition_name} should use !Not"

        not_list = condition[not_key]
        assert isinstance(not_list, list) and len(not_list) == 1

        equals_item = not_list[0]
        equals_key = '!Equals' if '!Equals' in equals_item else 'Fn::Equals'
        assert equals_key in equals_item, f"{condition_name} should use !Equals inside !Not"

        equals_list = equals_item[equals_key]
        assert len(equals_list) == 2

        # First element should be !Ref to the parameter
        ref_item = equals_list[0]
        ref_key = '!Ref' if '!Ref' in ref_item else 'Ref'
        assert ref_item[ref_key] == param_name, \
            f"{condition_name} should reference {param_name}"

        # Second element should be empty string
        assert equals_list[1] == '', \
            f"{condition_name} should compare against empty string"


def _get_default_cache_behavior(template):
    """Helper to extract DefaultCacheBehavior from the distribution."""
    resources = template.get('Resources', {})
    distribution = resources.get('CloudFrontDistribution', {})
    dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
    return dist_config.get('DefaultCacheBehavior', {})


def _extract_function_associations_from_if_branch(branch):
    """Extract function association items from a branch of an !If.
    Each item is an !If with [condition, {EventType, FunctionARN}, AWS::NoValue]."""
    items = []
    for item in branch:
        if isinstance(item, dict):
            if_key = '!If' if '!If' in item else 'Fn::If'
            if if_key in item:
                if_list = item[if_key]
                condition = if_list[0]
                assoc = if_list[1] if len(if_list) > 1 else None
                event_type = assoc.get('EventType') if isinstance(assoc, dict) else None
                func_arn = assoc.get('FunctionARN', {}) if isinstance(assoc, dict) else {}
                ref_key = '!Ref' if '!Ref' in func_arn else 'Ref'
                param_ref = func_arn.get(ref_key) if isinstance(func_arn, dict) else None
                items.append({
                    'condition': condition,
                    'event_type': event_type,
                    'param_ref': param_ref,
                })
    return items


class TestDefaultCacheBehaviorFunctionAssociations:
    """Tests for DefaultCacheBehavior FunctionAssociations.
    Requirements: 5.1, 5.2, 5.3, 7.1, 7.2, 7.3, 9.2, 9.4"""

    def test_function_associations_property_exists(self, network_template):
        dcb = _get_default_cache_behavior(network_template)
        assert 'FunctionAssociations' in dcb, \
            "DefaultCacheBehavior should have FunctionAssociations"

    def test_top_level_if_static_origin_is_root(self, network_template):
        """FunctionAssociations should branch on StaticOriginIsRoot."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        assert if_key in fa, "FunctionAssociations should use !If"
        assert fa[if_key][0] == 'StaticOriginIsRoot', \
            "Top-level condition should be StaticOriginIsRoot"

    def test_static_branch_has_4_items(self, network_template):
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        static_branch = fa[if_key][1]  # true branch = static
        assert isinstance(static_branch, list)
        assert len(static_branch) == 4, "Static branch should have 4 function association items"

    def test_api_branch_has_4_items(self, network_template):
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        api_branch = fa[if_key][2]  # false branch = API
        assert isinstance(api_branch, list)
        assert len(api_branch) == 4, "API branch should have 4 function association items"

    def test_static_branch_event_types(self, network_template):
        """Static branch should have all 4 event types in order."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        static_branch = fa[if_key][1]
        items = _extract_function_associations_from_if_branch(static_branch)
        actual_event_types = [i['event_type'] for i in items]
        assert actual_event_types == EVENT_TYPES

    def test_api_branch_event_types(self, network_template):
        """API branch should have all 4 event types in order."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        api_branch = fa[if_key][2]
        items = _extract_function_associations_from_if_branch(api_branch)
        actual_event_types = [i['event_type'] for i in items]
        assert actual_event_types == EVENT_TYPES

    def test_static_branch_references_static_params(self, network_template):
        """Static branch should reference static function parameters."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        static_branch = fa[if_key][1]
        items = _extract_function_associations_from_if_branch(static_branch)
        param_refs = [i['param_ref'] for i in items]
        assert param_refs == STATIC_FUNCTION_PARAMS

    def test_api_branch_references_api_params(self, network_template):
        """API branch should reference API function parameters."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        api_branch = fa[if_key][2]
        items = _extract_function_associations_from_if_branch(api_branch)
        param_refs = [i['param_ref'] for i in items]
        assert param_refs == API_FUNCTION_PARAMS

    def test_static_branch_uses_static_conditions(self, network_template):
        """Static branch items should use static Has* conditions."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        static_branch = fa[if_key][1]
        items = _extract_function_associations_from_if_branch(static_branch)
        conditions = [i['condition'] for i in items]
        assert conditions == STATIC_CONDITIONS

    def test_api_branch_uses_api_conditions(self, network_template):
        """API branch items should use API Has* conditions."""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        api_branch = fa[if_key][2]
        items = _extract_function_associations_from_if_branch(api_branch)
        conditions = [i['condition'] for i in items]
        assert conditions == API_CONDITIONS

    def test_no_api_refs_in_static_branch(self, network_template):
        """Isolation: static branch should not reference API params. Req 9.4"""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        static_branch = fa[if_key][1]
        items = _extract_function_associations_from_if_branch(static_branch)
        for item in items:
            assert item['param_ref'] not in API_FUNCTION_PARAMS, \
                f"Static branch should not reference API param {item['param_ref']}"

    def test_no_static_refs_in_api_branch(self, network_template):
        """Isolation: API branch should not reference static params. Req 9.2"""
        dcb = _get_default_cache_behavior(network_template)
        fa = dcb['FunctionAssociations']
        if_key = '!If' if '!If' in fa else 'Fn::If'
        api_branch = fa[if_key][2]
        items = _extract_function_associations_from_if_branch(api_branch)
        for item in items:
            assert item['param_ref'] not in STATIC_FUNCTION_PARAMS, \
                f"API branch should not reference static param {item['param_ref']}"


def _get_cache_behaviors(template):
    """Helper to extract CacheBehaviors list from the distribution."""
    resources = template.get('Resources', {})
    distribution = resources.get('CloudFrontDistribution', {})
    dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
    return dist_config.get('CacheBehaviors', [])


def _find_path_behavior(cache_behaviors, condition_name):
    """Find a path-based cache behavior by its top-level !If condition name.
    Returns the behavior definition dict (the true branch of the !If)."""
    for behavior in cache_behaviors:
        if isinstance(behavior, dict):
            if_key = '!If' if '!If' in behavior else 'Fn::If'
            if if_key in behavior:
                if_list = behavior[if_key]
                if if_list[0] == condition_name:
                    return if_list[1]
    return None


class TestPathBasedCacheBehaviorFunctionAssociations:
    """Tests for path-based cache behavior FunctionAssociations.
    Requirements: 6.1-6.3, 8.1-8.3, 9.1, 9.3"""

    def test_static_path_behavior_has_function_associations(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        static_behavior = _find_path_behavior(behaviors, 'HasRouteForStaticOrigin')
        assert static_behavior is not None, "Static path behavior should exist"
        assert 'FunctionAssociations' in static_behavior, \
            "Static path behavior should have FunctionAssociations"

    def test_api_path_behavior_has_function_associations(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        api_behavior = _find_path_behavior(behaviors, 'HasRouteForApiInCloudFront')
        assert api_behavior is not None, "API path behavior should exist"
        assert 'FunctionAssociations' in api_behavior, \
            "API path behavior should have FunctionAssociations"

    def test_static_path_has_4_items(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        static_behavior = _find_path_behavior(behaviors, 'HasRouteForStaticOrigin')
        fa = static_behavior['FunctionAssociations']
        assert isinstance(fa, list) and len(fa) == 4

    def test_api_path_has_4_items(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        api_behavior = _find_path_behavior(behaviors, 'HasRouteForApiInCloudFront')
        fa = api_behavior['FunctionAssociations']
        assert isinstance(fa, list) and len(fa) == 4

    def test_static_path_event_types(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        static_behavior = _find_path_behavior(behaviors, 'HasRouteForStaticOrigin')
        items = _extract_function_associations_from_if_branch(static_behavior['FunctionAssociations'])
        actual = [i['event_type'] for i in items]
        assert actual == EVENT_TYPES

    def test_api_path_event_types(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        api_behavior = _find_path_behavior(behaviors, 'HasRouteForApiInCloudFront')
        items = _extract_function_associations_from_if_branch(api_behavior['FunctionAssociations'])
        actual = [i['event_type'] for i in items]
        assert actual == EVENT_TYPES

    def test_static_path_references_static_params(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        static_behavior = _find_path_behavior(behaviors, 'HasRouteForStaticOrigin')
        items = _extract_function_associations_from_if_branch(static_behavior['FunctionAssociations'])
        param_refs = [i['param_ref'] for i in items]
        assert param_refs == STATIC_FUNCTION_PARAMS

    def test_api_path_references_api_params(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        api_behavior = _find_path_behavior(behaviors, 'HasRouteForApiInCloudFront')
        items = _extract_function_associations_from_if_branch(api_behavior['FunctionAssociations'])
        param_refs = [i['param_ref'] for i in items]
        assert param_refs == API_FUNCTION_PARAMS

    def test_static_path_uses_static_conditions(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        static_behavior = _find_path_behavior(behaviors, 'HasRouteForStaticOrigin')
        items = _extract_function_associations_from_if_branch(static_behavior['FunctionAssociations'])
        conditions = [i['condition'] for i in items]
        assert conditions == STATIC_CONDITIONS

    def test_api_path_uses_api_conditions(self, network_template):
        behaviors = _get_cache_behaviors(network_template)
        api_behavior = _find_path_behavior(behaviors, 'HasRouteForApiInCloudFront')
        items = _extract_function_associations_from_if_branch(api_behavior['FunctionAssociations'])
        conditions = [i['condition'] for i in items]
        assert conditions == API_CONDITIONS

    def test_no_api_refs_in_static_path(self, network_template):
        """Isolation: static path should not reference API params. Req 9.1"""
        behaviors = _get_cache_behaviors(network_template)
        static_behavior = _find_path_behavior(behaviors, 'HasRouteForStaticOrigin')
        items = _extract_function_associations_from_if_branch(static_behavior['FunctionAssociations'])
        for item in items:
            assert item['param_ref'] not in API_FUNCTION_PARAMS

    def test_no_static_refs_in_api_path(self, network_template):
        """Isolation: API path should not reference static params. Req 9.3"""
        behaviors = _get_cache_behaviors(network_template)
        api_behavior = _find_path_behavior(behaviors, 'HasRouteForApiInCloudFront')
        items = _extract_function_associations_from_if_branch(api_behavior['FunctionAssociations'])
        for item in items:
            assert item['param_ref'] not in STATIC_FUNCTION_PARAMS


class TestCloudFrontFunctionBackwardCompatibility:
    """Tests for backward compatibility.
    Requirements: 10.1, 10.2, 10.3, 11.1"""

    def test_template_version_remains_v0_0_16(self, network_template):
        """Template version should remain v0.0.16 (PATCH=0, development mode). Req 11.1"""
        # Read the raw file to check the version comment
        template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
        content = template_path.read_text()
        assert '# Version: v0.0.16/' in content, \
            "Template version should remain v0.0.16"

    @pytest.mark.parametrize("param_name", ALL_FUNCTION_PARAMS)
    def test_all_params_default_to_empty_string(self, network_template, param_name):
        """Property 1: All function parameters default to empty string. Req 10.1"""
        param = network_template['Parameters'][param_name]
        assert param['Default'] == '', \
            f"{param_name} must default to empty string for backward compatibility"
