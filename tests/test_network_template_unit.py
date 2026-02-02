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
