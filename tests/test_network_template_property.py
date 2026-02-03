"""
Property-based tests for network template CloudFront logging configuration.
Tests universal properties that should hold across all valid parameter combinations.
"""

import pytest
import sys
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings
import yaml

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


def load_network_template():
    """Load the network template for testing."""
    template_path = Path(__file__).parent.parent / "templates" / "v2" / "network" / "template-network-route53-cloudfront-s3-apigw.yml"
    return load_template(template_path)


# Strategy for generating valid S3 bucket names
def valid_bucket_name_strategy():
    """Generate valid S3 bucket names (3-63 chars, lowercase alphanumeric and dashes)."""
    # Start with a letter or number
    start = st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789')
    # Middle can be letters, numbers, or dashes (1-61 chars)
    middle = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
        min_size=1,
        max_size=61
    )
    # End with a letter or number
    end = st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789')
    
    return st.builds(
        lambda s, m, e: s + m + e,
        start, middle, end
    )


# Strategy for generating valid parameter values
def valid_prefix_strategy():
    """Generate valid Prefix values (2-8 chars)."""
    start = st.sampled_from('abcdefghijklmnopqrstuvwxyz')
    middle = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
        min_size=0,
        max_size=6
    )
    end = st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789')
    
    return st.builds(
        lambda s, m, e: s + m + e if m else s + e,
        start, middle, end
    )


def valid_project_id_strategy():
    """Generate valid ProjectId values (2-26 chars)."""
    start = st.sampled_from('abcdefghijklmnopqrstuvwxyz')
    middle = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
        min_size=0,
        max_size=24
    )
    end = st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789')
    
    return st.builds(
        lambda s, m, e: s + m + e if m else s + e,
        start, middle, end
    )


def valid_stage_id_strategy():
    """Generate valid StageId values (2-8 chars)."""
    start = st.sampled_from('abcdefghijklmnopqrstuvwxyz')
    middle = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
        min_size=0,
        max_size=6
    )
    end = st.sampled_from('abcdefghijklmnopqrstuvwxyz0123456789')
    
    return st.builds(
        lambda s, m, e: s + m + e if m else s + e,
        start, middle, end
    )


class TestLoggingConfigurationFormatProperty:
    """
    Property 3: Logging configuration format when enabled
    Validates: Requirements 1.4, 3.1, 3.3
    
    For any valid S3LogBucketName (non-empty), Prefix, ProjectId, and StageId combination,
    when the template is rendered, the CloudFront distribution Logging property should have
    IncludeCookies set to false, Bucket set to {S3LogBucketName}.s3.amazonaws.com, and
    Prefix set to cloudfront/{Prefix}-{ProjectId}-{StageId}.
    """
    
    @given(
        bucket_name=valid_bucket_name_strategy(),
        prefix=valid_prefix_strategy(),
        project_id=valid_project_id_strategy(),
        stage_id=valid_stage_id_strategy()
    )
    @settings(max_examples=20)
    def test_logging_configuration_format_when_enabled(
        self, bucket_name, prefix, project_id, stage_id
    ):
        """
        Test that logging configuration has correct format when enabled.
        **Validates: Requirements 1.4, 3.1, 3.3**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Logging property (it's conditional)
        logging_config = dist_config.get('Logging')
        
        # Verify the structure is a conditional (!If)
        assert logging_config is not None, "Logging property should exist in template"
        
        # The logging config should be an !If intrinsic function
        # Structure: !If [HasLogBucket, {config}, !Ref AWS::NoValue]
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            assert if_key in logging_config, "Logging should use !If conditional"
            
            if_list = logging_config[if_key]
            assert isinstance(if_list, list), "!If should contain a list"
            assert len(if_list) == 3, "!If should have 3 elements: [condition, true_value, false_value]"
            
            # First element should be the condition name
            condition_name = if_list[0]
            assert condition_name == 'HasLogBucket', "Condition should be HasLogBucket"
            
            # Second element should be the logging configuration when enabled
            enabled_config = if_list[1]
            assert isinstance(enabled_config, dict), "Enabled config should be a dict"
            
            # Verify IncludeCookies is 'false'
            assert 'IncludeCookies' in enabled_config, "IncludeCookies should be present"
            assert enabled_config['IncludeCookies'] == 'false', "IncludeCookies should be 'false'"
            
            # Verify Bucket format
            assert 'Bucket' in enabled_config, "Bucket should be present"
            bucket_value = enabled_config['Bucket']
            
            # Bucket should be a !Sub with pattern "${S3LogBucketName}.s3.amazonaws.com"
            if isinstance(bucket_value, dict):
                sub_key = '!Sub' if '!Sub' in bucket_value else 'Fn::Sub'
                assert sub_key in bucket_value, "Bucket should use !Sub"
                bucket_template = bucket_value[sub_key]
                assert bucket_template == "${S3LogBucketName}.s3.amazonaws.com", \
                    f"Bucket template should be '${{S3LogBucketName}}.s3.amazonaws.com', got '{bucket_template}'"
            
            # Verify Prefix format
            assert 'Prefix' in enabled_config, "Prefix should be present"
            prefix_value = enabled_config['Prefix']
            
            # Prefix should be a !Sub with pattern "cloudfront/${Prefix}-${ProjectId}-${StageId}"
            if isinstance(prefix_value, dict):
                sub_key = '!Sub' if '!Sub' in prefix_value else 'Fn::Sub'
                assert sub_key in prefix_value, "Prefix should use !Sub"
                prefix_template = prefix_value[sub_key]
                assert prefix_template == "cloudfront/${Prefix}-${ProjectId}-${StageId}", \
                    f"Prefix template should be 'cloudfront/${{Prefix}}-${{ProjectId}}-${{StageId}}', got '{prefix_template}'"
            
            # Third element should be !Ref AWS::NoValue (when disabled)
            disabled_value = if_list[2]
            if isinstance(disabled_value, dict):
                ref_key = '!Ref' if '!Ref' in disabled_value else 'Ref'
                assert ref_key in disabled_value, "Disabled value should use !Ref"
                assert disabled_value[ref_key] == 'AWS::NoValue', \
                    "Disabled value should be !Ref AWS::NoValue"


class TestLoggingDisabledProperty:
    """
    Property 1: Logging disabled for empty bucket name
    Validates: Requirements 1.3, 3.4
    
    For any CloudFormation template configuration where S3LogBucketName is an empty string,
    the rendered CloudFront distribution resource should not contain a Logging property
    (or it should evaluate to AWS::NoValue).
    """
    
    @given(
        prefix=valid_prefix_strategy(),
        project_id=valid_project_id_strategy(),
        stage_id=valid_stage_id_strategy()
    )
    @settings(max_examples=20)
    def test_logging_disabled_for_empty_bucket_name(
        self, prefix, project_id, stage_id
    ):
        """
        Test that empty S3LogBucketName results in no Logging property.
        **Validates: Requirements 1.3, 3.4**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Logging property
        logging_config = dist_config.get('Logging')
        
        # Verify the structure is a conditional that returns AWS::NoValue when false
        assert logging_config is not None, "Logging property should exist in template"
        
        if isinstance(logging_config, dict):
            if_key = '!If' if '!If' in logging_config else 'Fn::If'
            assert if_key in logging_config, "Logging should use !If conditional"
            
            if_list = logging_config[if_key]
            assert len(if_list) == 3, "!If should have 3 elements"
            
            # The condition should be HasLogBucket
            condition_name = if_list[0]
            assert condition_name == 'HasLogBucket', "Condition should be HasLogBucket"
            
            # When condition is false (empty bucket name), should return AWS::NoValue
            disabled_value = if_list[2]
            if isinstance(disabled_value, dict):
                ref_key = '!Ref' if '!Ref' in disabled_value else 'Ref'
                assert ref_key in disabled_value, "Disabled value should use !Ref"
                assert disabled_value[ref_key] == 'AWS::NoValue', \
                    "When S3LogBucketName is empty, Logging should evaluate to AWS::NoValue"
        
        # Verify the HasLogBucket condition logic
        conditions = network_template.get('Conditions', {})
        has_log_bucket = conditions.get('HasLogBucket')
        
        assert has_log_bucket is not None, "HasLogBucket condition should exist"
        
        # The condition should be: !Not [!Equals [!Ref S3LogBucketName, '']]
        # This means when S3LogBucketName is '', the condition is false
        if isinstance(has_log_bucket, dict):
            not_key = '!Not' if '!Not' in has_log_bucket else 'Fn::Not'
            assert not_key in has_log_bucket, "HasLogBucket should use !Not"
            
            not_list = has_log_bucket[not_key]
            equals_condition = not_list[0]
            equals_key = '!Equals' if '!Equals' in equals_condition else 'Fn::Equals'
            equals_list = equals_condition[equals_key]
            
            # Should compare S3LogBucketName to empty string
            assert equals_list[1] == '', \
                "HasLogBucket condition should check if S3LogBucketName equals empty string"


class TestParameterConsistencyProperty:
    """
    Property 6: Parameter consistency with steering document
    Validates: Requirements 8.8
    
    For any standard parameter defined in the steering document (Prefix, ProjectId, StageId, 
    S3LogBucketName), if that parameter exists in the template, then its Type, AllowedPattern, 
    MinLength, MaxLength, and ConstraintDescription should match the definition in the 
    steering document.
    """
    
    # Standard parameter definitions from steering document
    STANDARD_PARAMS = {
        'Prefix': {
            'Type': 'String',
            'AllowedPattern': '^[a-z][a-z0-9-]{0,6}[a-z0-9]$',
            'MinLength': 2,
            'MaxLength': 8,
            'ConstraintDescription': '2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters.'
        },
        'ProjectId': {
            'Type': 'String',
            'AllowedPattern': '^[a-z][a-z0-9-]{0,24}[a-z0-9]$',
            'MinLength': 2,
            'MaxLength': 26,
            'ConstraintDescription': 'Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters.'
        },
        'StageId': {
            'Type': 'String',
            'AllowedPattern': '^[a-z][a-z0-9-]{0,6}[a-z0-9]$',
            'MinLength': 2,
            'MaxLength': 8,
            'ConstraintDescription': '2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number.'
        },
        'S3LogBucketName': {
            'Type': 'String',
            'AllowedPattern': '^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$',
            'ConstraintDescription': 'Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number.'
        }
    }
    
    @given(param_name=st.sampled_from(['Prefix', 'ProjectId', 'StageId', 'S3LogBucketName']))
    @settings(max_examples=20)
    def test_parameter_consistency_with_steering_document(self, param_name):
        """
        Test that template parameters match steering document definitions.
        **Validates: Requirements 8.8**
        """
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Verify parameter exists in template
        assert param_name in parameters, f"Parameter '{param_name}' should exist in template"
        
        template_param = parameters[param_name]
        standard_param = self.STANDARD_PARAMS[param_name]
        
        # Verify Type matches
        assert template_param.get('Type') == standard_param['Type'], \
            f"{param_name}: Type should be '{standard_param['Type']}', got '{template_param.get('Type')}'"
        
        # Verify AllowedPattern matches
        assert template_param.get('AllowedPattern') == standard_param['AllowedPattern'], \
            f"{param_name}: AllowedPattern should be '{standard_param['AllowedPattern']}', got '{template_param.get('AllowedPattern')}'"
        
        # Verify MinLength matches (if specified in standard)
        if 'MinLength' in standard_param:
            assert template_param.get('MinLength') == standard_param['MinLength'], \
                f"{param_name}: MinLength should be {standard_param['MinLength']}, got {template_param.get('MinLength')}"
        
        # Verify MaxLength matches (if specified in standard)
        if 'MaxLength' in standard_param:
            assert template_param.get('MaxLength') == standard_param['MaxLength'], \
                f"{param_name}: MaxLength should be {standard_param['MaxLength']}, got {template_param.get('MaxLength')}"
        
        # Verify ConstraintDescription matches
        assert template_param.get('ConstraintDescription') == standard_param['ConstraintDescription'], \
            f"{param_name}: ConstraintDescription should match standard definition"


class TestExistingConditionsCompatibilityProperty:
    """
    Property 5: Existing conditions compatibility
    Validates: Requirements 5.3
    
    For any existing condition in the template (IsProduction, IsProdStage, HasStaticOrigin, etc.),
    after adding the HasLogBucket condition, all existing conditions should continue to evaluate
    correctly with their original logic unchanged.
    """
    
    # All existing conditions in the template (excluding HasLogBucket which is new)
    EXISTING_CONDITIONS = [
        'IsProduction',
        'IsProdStage',
        'HasStaticOrigin',
        'HasApiGatewayOrigin',
        'HasRouteForStaticOrigin',
        'HasRouteForApi',
        'StaticOriginIsRoot',
        'ApiIsBehindCloudFront',
        'HasRouteForApiInCloudFront',
        'CreateDistribution',
        'CreateDnsRecordForCloudFront',
        'CreateDnsRecordForApiGateway',
        'HasHeadersToForwardToApi'
    ]
    
    @given(condition_name=st.sampled_from(EXISTING_CONDITIONS))
    @settings(max_examples=20)
    def test_existing_conditions_still_exist_and_unchanged(self, condition_name):
        """
        Test that all existing conditions still exist in the template after adding HasLogBucket.
        **Validates: Requirements 5.3**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        # Verify the condition still exists
        assert condition_name in conditions, \
            f"Existing condition '{condition_name}' should still exist in template"
        
        condition_value = conditions[condition_name]
        assert condition_value is not None, \
            f"Condition '{condition_name}' should have a value"
        
        # Verify it's a valid CloudFormation intrinsic function
        assert isinstance(condition_value, dict), \
            f"Condition '{condition_name}' should be a dict (intrinsic function)"
        
        # Check that it uses valid CloudFormation condition functions
        valid_condition_functions = [
            '!Equals', 'Fn::Equals',
            '!Not', 'Fn::Not',
            '!And', 'Fn::And',
            '!Or', 'Fn::Or',
            '!If', 'Fn::If'
        ]
        
        has_valid_function = any(key in condition_value for key in valid_condition_functions)
        assert has_valid_function, \
            f"Condition '{condition_name}' should use a valid CloudFormation condition function"
    
    def test_has_log_bucket_condition_exists(self):
        """
        Test that the new HasLogBucket condition exists alongside existing conditions.
        **Validates: Requirements 5.3**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        # Verify HasLogBucket exists
        assert 'HasLogBucket' in conditions, \
            "HasLogBucket condition should exist in template"
        
        # Verify all existing conditions still exist
        for condition_name in self.EXISTING_CONDITIONS:
            assert condition_name in conditions, \
                f"Existing condition '{condition_name}' should still exist after adding HasLogBucket"
    
    @given(
        deploy_env=st.sampled_from(['DEV', 'TEST', 'PROD']),
        stage_id=st.sampled_from(['dev', 'test', 'prod', 'beta', 'staging'])
    )
    @settings(max_examples=20)
    def test_is_production_condition_logic_unchanged(self, deploy_env, stage_id):
        """
        Test that IsProduction condition logic is unchanged.
        **Validates: Requirements 5.3**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        is_production = conditions.get('IsProduction')
        assert is_production is not None, "IsProduction condition should exist"
        
        # IsProduction should be: !Equals [!Ref DeployEnvironment, PROD]
        if isinstance(is_production, dict):
            equals_key = '!Equals' if '!Equals' in is_production else 'Fn::Equals'
            assert equals_key in is_production, "IsProduction should use !Equals"
            
            equals_list = is_production[equals_key]
            assert isinstance(equals_list, list), "!Equals should contain a list"
            assert len(equals_list) == 2, "!Equals should have 2 elements"
            
            # First element should reference DeployEnvironment
            first_elem = equals_list[0]
            if isinstance(first_elem, dict):
                ref_key = '!Ref' if '!Ref' in first_elem else 'Ref'
                assert ref_key in first_elem, "First element should be !Ref"
                assert first_elem[ref_key] == 'DeployEnvironment', \
                    "IsProduction should reference DeployEnvironment parameter"
            
            # Second element should be 'PROD'
            assert equals_list[1] == 'PROD', \
                "IsProduction should compare to 'PROD'"
    
    @given(stage_id=st.sampled_from(['dev', 'test', 'prod', 'beta', 'staging']))
    @settings(max_examples=20)
    def test_is_prod_stage_condition_logic_unchanged(self, stage_id):
        """
        Test that IsProdStage condition logic is unchanged.
        **Validates: Requirements 5.3**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        is_prod_stage = conditions.get('IsProdStage')
        assert is_prod_stage is not None, "IsProdStage condition should exist"
        
        # IsProdStage should be: !Equals [!Ref StageId, "prod"]
        if isinstance(is_prod_stage, dict):
            equals_key = '!Equals' if '!Equals' in is_prod_stage else 'Fn::Equals'
            assert equals_key in is_prod_stage, "IsProdStage should use !Equals"
            
            equals_list = is_prod_stage[equals_key]
            assert len(equals_list) == 2, "!Equals should have 2 elements"
            
            # First element should reference StageId
            first_elem = equals_list[0]
            if isinstance(first_elem, dict):
                ref_key = '!Ref' if '!Ref' in first_elem else 'Ref'
                assert first_elem[ref_key] == 'StageId', \
                    "IsProdStage should reference StageId parameter"
            
            # Second element should be 'prod'
            assert equals_list[1] == 'prod', \
                "IsProdStage should compare to 'prod'"
    
    @given(
        s3_origin=st.sampled_from(['', 'my-bucket.s3.amazonaws.com', 'test-bucket.s3.us-east-1.amazonaws.com']),
        api_gateway_id=st.sampled_from(['', 'abc123xyz', 'test123'])
    )
    @settings(max_examples=20)
    def test_origin_conditions_logic_unchanged(self, s3_origin, api_gateway_id):
        """
        Test that HasStaticOrigin and HasApiGatewayOrigin conditions logic is unchanged.
        **Validates: Requirements 5.3**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        # Test HasStaticOrigin
        has_static_origin = conditions.get('HasStaticOrigin')
        assert has_static_origin is not None, "HasStaticOrigin condition should exist"
        
        # HasStaticOrigin should be: !Not [!Equals [!Ref S3OriginDomainName, '']]
        if isinstance(has_static_origin, dict):
            not_key = '!Not' if '!Not' in has_static_origin else 'Fn::Not'
            assert not_key in has_static_origin, "HasStaticOrigin should use !Not"
            
            not_list = has_static_origin[not_key]
            equals_condition = not_list[0]
            equals_key = '!Equals' if '!Equals' in equals_condition else 'Fn::Equals'
            equals_list = equals_condition[equals_key]
            
            # Should reference S3OriginDomainName and compare to empty string
            first_elem = equals_list[0]
            if isinstance(first_elem, dict):
                ref_key = '!Ref' if '!Ref' in first_elem else 'Ref'
                assert first_elem[ref_key] == 'S3OriginDomainName', \
                    "HasStaticOrigin should reference S3OriginDomainName"
            assert equals_list[1] == '', \
                "HasStaticOrigin should compare to empty string"
        
        # Test HasApiGatewayOrigin
        has_api_gateway_origin = conditions.get('HasApiGatewayOrigin')
        assert has_api_gateway_origin is not None, "HasApiGatewayOrigin condition should exist"
        
        # HasApiGatewayOrigin should be: !Not [!Equals [!Ref ApiGatewayId, '']]
        if isinstance(has_api_gateway_origin, dict):
            not_key = '!Not' if '!Not' in has_api_gateway_origin else 'Fn::Not'
            assert not_key in has_api_gateway_origin, "HasApiGatewayOrigin should use !Not"
            
            not_list = has_api_gateway_origin[not_key]
            equals_condition = not_list[0]
            equals_key = '!Equals' if '!Equals' in equals_condition else 'Fn::Equals'
            equals_list = equals_condition[equals_key]
            
            # Should reference ApiGatewayId and compare to empty string
            first_elem = equals_list[0]
            if isinstance(first_elem, dict):
                ref_key = '!Ref' if '!Ref' in first_elem else 'Ref'
                assert first_elem[ref_key] == 'ApiGatewayId', \
                    "HasApiGatewayOrigin should reference ApiGatewayId"
            assert equals_list[1] == '', \
                "HasApiGatewayOrigin should compare to empty string"
    
    def test_complex_conditions_structure_unchanged(self):
        """
        Test that complex conditions (using !And, !Or) maintain their structure.
        **Validates: Requirements 5.3**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        # Test StaticOriginIsRoot (uses !And)
        static_origin_is_root = conditions.get('StaticOriginIsRoot')
        assert static_origin_is_root is not None, "StaticOriginIsRoot should exist"
        
        if isinstance(static_origin_is_root, dict):
            and_key = '!And' if '!And' in static_origin_is_root else 'Fn::And'
            assert and_key in static_origin_is_root, "StaticOriginIsRoot should use !And"
        
        # Test ApiIsBehindCloudFront (uses !And)
        api_behind_cloudfront = conditions.get('ApiIsBehindCloudFront')
        assert api_behind_cloudfront is not None, "ApiIsBehindCloudFront should exist"
        
        if isinstance(api_behind_cloudfront, dict):
            and_key = '!And' if '!And' in api_behind_cloudfront else 'Fn::And'
            assert and_key in api_behind_cloudfront, "ApiIsBehindCloudFront should use !And"
        
        # Test CreateDistribution (uses !Or)
        create_distribution = conditions.get('CreateDistribution')
        assert create_distribution is not None, "CreateDistribution should exist"
        
        if isinstance(create_distribution, dict):
            or_key = '!Or' if '!Or' in create_distribution else 'Fn::Or'
            assert or_key in create_distribution, "CreateDistribution should use !Or"


# =============================================================================
# Origin Path Property-Based Tests
# Feature: 0-0-29-network-add-origin-path-to-static-and-api
# =============================================================================


def valid_custom_path_strategy():
    """Generate valid custom origin paths (not empty, not /)."""
    # Start with /
    # Middle can be letters, numbers, dashes, underscores, or slashes (1-50 chars)
    middle = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/',
        min_size=1,
        max_size=50
    ).filter(lambda s: not s.endswith('/'))  # Must not end with /
    
    return st.builds(
        lambda m: '/' + m,
        middle
    ).filter(lambda p: p != '/')  # Exclude single /


class TestDefaultStaticOriginPathProperty:
    """
    Property 1: Default Static Origin Path
    Validates: Requirements 1.2, 4.1
    
    For any valid StageId value, when StaticOriginPath is empty (default), 
    the resulting CloudFront origin path should equal /${StageId}/public
    """
    
    @given(stage_id=valid_stage_id_strategy())
    @settings(max_examples=100)
    def test_default_static_origin_path(self, stage_id):
        """
        Test that default static origin path equals /${StageId}/public.
        **Validates: Requirements 1.2, 4.1**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Origins list
        origins = dist_config.get('Origins', [])
        assert len(origins) > 0, "Origins list should not be empty"
        
        # The first origin is wrapped in !If [HasStaticOrigin, {...}, !Ref AWS::NoValue]
        first_origin_conditional = origins[0]
        assert isinstance(first_origin_conditional, dict), "First origin should be a conditional"
        
        if_key = '!If' if '!If' in first_origin_conditional else 'Fn::If'
        assert if_key in first_origin_conditional, "First origin should use !If"
        
        if_list = first_origin_conditional[if_key]
        assert len(if_list) == 3, "!If should have 3 elements"
        assert if_list[0] == 'HasStaticOrigin', "Condition should be HasStaticOrigin"
        
        # Get the actual static origin configuration (second element when condition is true)
        static_origin = if_list[1]
        assert isinstance(static_origin, dict), "Static origin should be a dict"
        assert static_origin.get('Id') == 'StaticS3Origin', "Origin ID should be StaticS3Origin"
        
        # Get the OriginPath property
        origin_path = static_origin.get('OriginPath')
        assert origin_path is not None, "OriginPath should exist for StaticS3Origin"
        
        # OriginPath should be a conditional: !If [UseDefaultStaticOriginPath, !Sub "/${StageId}/public", ...]
        if isinstance(origin_path, dict):
            path_if_key = '!If' if '!If' in origin_path else 'Fn::If'
            assert path_if_key in origin_path, "OriginPath should use !If conditional"
            
            path_if_list = origin_path[path_if_key]
            assert len(path_if_list) == 3, "!If should have 3 elements"
            
            # First element should be UseDefaultStaticOriginPath condition
            condition_name = path_if_list[0]
            assert condition_name == 'UseDefaultStaticOriginPath', \
                "First condition should be UseDefaultStaticOriginPath"
            
            # Second element (when condition is true) should be !Sub "/${StageId}/public"
            default_path = path_if_list[1]
            if isinstance(default_path, dict):
                sub_key = '!Sub' if '!Sub' in default_path else 'Fn::Sub'
                assert sub_key in default_path, "Default path should use !Sub"
                path_template = default_path[sub_key]
                assert path_template == "/${StageId}/public", \
                    f"Default static origin path should be '/${{StageId}}/public', got '{path_template}'"


class TestDefaultApiOriginPathProperty:
    """
    Property 2: Default API Origin Path
    Validates: Requirements 2.2, 4.4
    
    For any valid ProjectId and StageId values, when ApiOriginPath is empty (default), 
    the resulting CloudFront origin path should equal /${ProjectId}-${StageId}
    """
    
    @given(
        project_id=valid_project_id_strategy(),
        stage_id=valid_stage_id_strategy()
    )
    @settings(max_examples=100)
    def test_default_api_origin_path(self, project_id, stage_id):
        """
        Test that default API origin path equals /${ProjectId}-${StageId}.
        **Validates: Requirements 2.2, 4.4**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Origins list
        origins = dist_config.get('Origins', [])
        assert len(origins) >= 2, "Origins list should have at least 2 elements"
        
        # The second origin is wrapped in !If [ApiIsBehindCloudFront, {...}, !Ref AWS::NoValue]
        second_origin_conditional = origins[1]
        assert isinstance(second_origin_conditional, dict), "Second origin should be a conditional"
        
        if_key = '!If' if '!If' in second_origin_conditional else 'Fn::If'
        assert if_key in second_origin_conditional, "Second origin should use !If"
        
        if_list = second_origin_conditional[if_key]
        assert len(if_list) == 3, "!If should have 3 elements"
        assert if_list[0] == 'ApiIsBehindCloudFront', "Condition should be ApiIsBehindCloudFront"
        
        # Get the actual API origin configuration (second element when condition is true)
        api_origin = if_list[1]
        assert isinstance(api_origin, dict), "API origin should be a dict"
        assert api_origin.get('Id') == 'ApiGatewayOrigin', "Origin ID should be ApiGatewayOrigin"
        
        # Get the OriginPath property
        origin_path = api_origin.get('OriginPath')
        assert origin_path is not None, "OriginPath should exist for ApiGatewayOrigin"
        
        # OriginPath should be a conditional: !If [UseDefaultApiOriginPath, !Sub "/${ProjectId}-${StageId}", ...]
        if isinstance(origin_path, dict):
            path_if_key = '!If' if '!If' in origin_path else 'Fn::If'
            assert path_if_key in origin_path, "OriginPath should use !If conditional"
            
            path_if_list = origin_path[path_if_key]
            assert len(path_if_list) == 3, "!If should have 3 elements"
            
            # First element should be UseDefaultApiOriginPath condition
            condition_name = path_if_list[0]
            assert condition_name == 'UseDefaultApiOriginPath', \
                "First condition should be UseDefaultApiOriginPath"
            
            # Second element (when condition is true) should be !Sub "/${ProjectId}-${StageId}"
            default_path = path_if_list[1]
            if isinstance(default_path, dict):
                sub_key = '!Sub' if '!Sub' in default_path else 'Fn::Sub'
                assert sub_key in default_path, "Default path should use !Sub"
                path_template = default_path[sub_key]
                assert path_template == "/${ProjectId}-${StageId}", \
                    f"Default API origin path should be '/${{ProjectId}}-${{StageId}}', got '{path_template}'"


class TestCustomStaticOriginPathPassthroughProperty:
    """
    Property 3: Custom Static Origin Path Passthrough
    Validates: Requirements 1.4, 4.3
    
    For any valid custom path (not empty, not /), when StaticOriginPath is set to that path, 
    the resulting CloudFront origin path should equal the input path exactly
    """
    
    @given(custom_path=valid_custom_path_strategy())
    @settings(max_examples=100)
    def test_custom_static_origin_path_passthrough(self, custom_path):
        """
        Test that custom static origin path is used as-is.
        **Validates: Requirements 1.4, 4.3**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Origins list
        origins = dist_config.get('Origins', [])
        assert len(origins) > 0, "Origins list should not be empty"
        
        # The first origin is wrapped in !If [HasStaticOrigin, {...}, !Ref AWS::NoValue]
        first_origin_conditional = origins[0]
        if_key = '!If' if '!If' in first_origin_conditional else 'Fn::If'
        if_list = first_origin_conditional[if_key]
        
        # Get the actual static origin configuration
        static_origin = if_list[1]
        assert static_origin.get('Id') == 'StaticS3Origin', "Origin ID should be StaticS3Origin"
        
        # Get the OriginPath property
        origin_path = static_origin.get('OriginPath')
        assert origin_path is not None, "OriginPath should exist for StaticS3Origin"
        
        # OriginPath should be: !If [UseDefaultStaticOriginPath, default, !If [UseRootStaticOriginPath, "", !Ref StaticOriginPath]]
        if isinstance(origin_path, dict):
            path_if_key = '!If' if '!If' in origin_path else 'Fn::If'
            assert path_if_key in origin_path, "OriginPath should use !If conditional"
            
            path_if_list = origin_path[path_if_key]
            assert len(path_if_list) == 3, "!If should have 3 elements"
            
            # Third element (when not default) should be another !If for root vs custom
            nested_if = path_if_list[2]
            if isinstance(nested_if, dict):
                nested_if_key = '!If' if '!If' in nested_if else 'Fn::If'
                assert nested_if_key in nested_if, "Nested condition should use !If"
                
                nested_if_list = nested_if[nested_if_key]
                assert len(nested_if_list) == 3, "Nested !If should have 3 elements"
                
                # First element should be UseRootStaticOriginPath
                nested_condition = nested_if_list[0]
                assert nested_condition == 'UseRootStaticOriginPath', \
                    "Nested condition should be UseRootStaticOriginPath"
                
                # Second element (when root) should be empty string
                root_value = nested_if_list[1]
                assert root_value == "", "Root path should be empty string"
                
                # Third element (when custom) should be !Ref StaticOriginPath
                custom_value = nested_if_list[2]
                if isinstance(custom_value, dict):
                    ref_key = '!Ref' if '!Ref' in custom_value else 'Ref'
                    assert ref_key in custom_value, "Custom path should use !Ref"
                    assert custom_value[ref_key] == 'StaticOriginPath', \
                        "Custom path should reference StaticOriginPath parameter"


class TestCustomApiOriginPathPassthroughProperty:
    """
    Property 4: Custom API Origin Path Passthrough
    Validates: Requirements 2.4, 4.6
    
    For any valid custom path (not empty, not /), when ApiOriginPath is set to that path, 
    the resulting CloudFront origin path should equal the input path exactly
    """
    
    @given(custom_path=valid_custom_path_strategy())
    @settings(max_examples=100)
    def test_custom_api_origin_path_passthrough(self, custom_path):
        """
        Test that custom API origin path is used as-is.
        **Validates: Requirements 2.4, 4.6**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Origins list
        origins = dist_config.get('Origins', [])
        assert len(origins) >= 2, "Origins list should have at least 2 elements"
        
        # The second origin is wrapped in !If [ApiIsBehindCloudFront, {...}, !Ref AWS::NoValue]
        second_origin_conditional = origins[1]
        if_key = '!If' if '!If' in second_origin_conditional else 'Fn::If'
        if_list = second_origin_conditional[if_key]
        
        # Get the actual API origin configuration
        api_origin = if_list[1]
        assert api_origin.get('Id') == 'ApiGatewayOrigin', "Origin ID should be ApiGatewayOrigin"
        
        # Get the OriginPath property
        origin_path = api_origin.get('OriginPath')
        assert origin_path is not None, "OriginPath should exist for ApiGatewayOrigin"
        
        # OriginPath should be: !If [UseDefaultApiOriginPath, default, !If [UseRootApiOriginPath, "", !Ref ApiOriginPath]]
        if isinstance(origin_path, dict):
            path_if_key = '!If' if '!If' in origin_path else 'Fn::If'
            assert path_if_key in origin_path, "OriginPath should use !If conditional"
            
            path_if_list = origin_path[path_if_key]
            assert len(path_if_list) == 3, "!If should have 3 elements"
            
            # Third element (when not default) should be another !If for root vs custom
            nested_if = path_if_list[2]
            if isinstance(nested_if, dict):
                nested_if_key = '!If' if '!If' in nested_if else 'Fn::If'
                assert nested_if_key in nested_if, "Nested condition should use !If"
                
                nested_if_list = nested_if[nested_if_key]
                assert len(nested_if_list) == 3, "Nested !If should have 3 elements"
                
                # First element should be UseRootApiOriginPath
                nested_condition = nested_if_list[0]
                assert nested_condition == 'UseRootApiOriginPath', \
                    "Nested condition should be UseRootApiOriginPath"
                
                # Second element (when root) should be empty string
                root_value = nested_if_list[1]
                assert root_value == "", "Root path should be empty string"
                
                # Third element (when custom) should be !Ref ApiOriginPath
                custom_value = nested_if_list[2]
                if isinstance(custom_value, dict):
                    ref_key = '!Ref' if '!Ref' in custom_value else 'Ref'
                    assert ref_key in custom_value, "Custom path should use !Ref"
                    assert custom_value[ref_key] == 'ApiOriginPath', \
                        "Custom path should reference ApiOriginPath parameter"


class TestPathValidationRejectsInvalidFormatsProperty:
    """
    Property 5: Path Validation Rejects Invalid Formats
    Validates: Requirements 1.5, 1.6, 1.7, 2.5, 2.6, 2.7, 3.2, 3.3, 3.4
    
    For any path that does not match the validation rules (doesn't start with /, 
    ends with / except single /, or contains { or } characters), the template 
    parameter validation should reject the value
    """
    
    def invalid_path_strategy():
        """Generate invalid origin paths."""
        return st.one_of(
            # Paths without leading /
            st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',
                min_size=1,
                max_size=20
            ).filter(lambda s: not s.startswith('/')),
            
            # Paths with trailing / (but not single /)
            st.builds(
                lambda s: '/' + s + '/',
                st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_',
                    min_size=1,
                    max_size=20
                )
            )
        )
    
    @given(invalid_path=invalid_path_strategy())
    @settings(max_examples=100, deadline=None)
    def test_path_validation_rejects_invalid_formats(self, invalid_path):
        """
        Test that invalid paths are rejected by AllowedPattern regex.
        **Validates: Requirements 1.5, 1.6, 1.7, 2.5, 2.6, 2.7, 3.2, 3.3, 3.4**
        """
        import re
        
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Get StaticOriginPath parameter
        static_origin_path_param = parameters.get('StaticOriginPath')
        assert static_origin_path_param is not None, "StaticOriginPath parameter should exist"
        
        # Get the AllowedPattern
        allowed_pattern = static_origin_path_param.get('AllowedPattern')
        assert allowed_pattern is not None, "StaticOriginPath should have AllowedPattern"
        
        # Test that the invalid path does NOT match the pattern
        # The pattern should be: ^$|^\/$|^\/[a-zA-Z0-9\/_-]+[^\/]$
        pattern_match = re.match(allowed_pattern, invalid_path)
        
        # Invalid paths should NOT match the pattern
        assert pattern_match is None, \
            f"Invalid path '{invalid_path}' should be rejected by AllowedPattern '{allowed_pattern}'"
        
        # Also test ApiOriginPath parameter
        api_origin_path_param = parameters.get('ApiOriginPath')
        assert api_origin_path_param is not None, "ApiOriginPath parameter should exist"
        
        api_allowed_pattern = api_origin_path_param.get('AllowedPattern')
        assert api_allowed_pattern is not None, "ApiOriginPath should have AllowedPattern"
        
        # Test that the invalid path does NOT match the API pattern
        api_pattern_match = re.match(api_allowed_pattern, invalid_path)
        
        assert api_pattern_match is None, \
            f"Invalid path '{invalid_path}' should be rejected by ApiOriginPath AllowedPattern '{api_allowed_pattern}'"
    
    def test_path_validation_rejects_curly_braces(self):
        """
        Test that paths with curly braces are rejected.
        **Validates: Requirements 1.7, 2.7, 3.4**
        """
        import re
        
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Get StaticOriginPath parameter
        static_origin_path_param = parameters.get('StaticOriginPath')
        allowed_pattern = static_origin_path_param.get('AllowedPattern')
        
        # Test paths with curly braces
        invalid_paths_with_braces = [
            '/{StageId}',
            '/path/{id}',
            '/${StageId}/public',
            '/api/{version}',
            '/test/{param}/value'
        ]
        
        for invalid_path in invalid_paths_with_braces:
            pattern_match = re.match(allowed_pattern, invalid_path)
            assert pattern_match is None, \
                f"Path with curly braces '{invalid_path}' should be rejected by AllowedPattern"


class TestBackwardCompatibilityProperty:
    """
    Property 6: Backward Compatibility
    Validates: Requirements 5.1
    
    For any valid ProjectId and StageId values, when both StaticOriginPath and 
    ApiOriginPath are empty (default), the resulting origin paths should match 
    the previous template version's hardcoded values
    """
    
    @given(
        project_id=valid_project_id_strategy(),
        stage_id=valid_stage_id_strategy()
    )
    @settings(max_examples=100)
    def test_backward_compatibility(self, project_id, stage_id):
        """
        Test that empty origin paths produce the same result as previous version.
        **Validates: Requirements 5.1**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the Origins list
        origins = dist_config.get('Origins', [])
        assert len(origins) >= 2, "Origins list should have at least 2 elements"
        
        # Test Static Origin backward compatibility
        first_origin_conditional = origins[0]
        if_key = '!If' if '!If' in first_origin_conditional else 'Fn::If'
        if_list = first_origin_conditional[if_key]
        static_origin = if_list[1]
        
        if static_origin:
            origin_path = static_origin.get('OriginPath')
            assert origin_path is not None, "OriginPath should exist for StaticS3Origin"
            
            # When StaticOriginPath is empty (default), should use /${StageId}/public
            if isinstance(origin_path, dict):
                path_if_key = '!If' if '!If' in origin_path else 'Fn::If'
                path_if_list = origin_path[path_if_key]
                
                # The default path (second element) should be !Sub "/${StageId}/public"
                default_path = path_if_list[1]
                if isinstance(default_path, dict):
                    sub_key = '!Sub' if '!Sub' in default_path else 'Fn::Sub'
                    path_template = default_path[sub_key]
                    assert path_template == "/${StageId}/public", \
                        "Default static origin path should match previous version: /${StageId}/public"
        
        # Test API Origin backward compatibility
        second_origin_conditional = origins[1]
        api_if_key = '!If' if '!If' in second_origin_conditional else 'Fn::If'
        api_if_list = second_origin_conditional[api_if_key]
        api_origin = api_if_list[1]
        
        if api_origin:
            origin_path = api_origin.get('OriginPath')
            assert origin_path is not None, "OriginPath should exist for ApiGatewayOrigin"
            
            # When ApiOriginPath is empty (default), should use /${ProjectId}-${StageId}
            if isinstance(origin_path, dict):
                path_if_key = '!If' if '!If' in origin_path else 'Fn::If'
                path_if_list = origin_path[path_if_key]
                
                # The default path (second element) should be !Sub "/${ProjectId}-${StageId}"
                default_path = path_if_list[1]
                if isinstance(default_path, dict):
                    sub_key = '!Sub' if '!Sub' in default_path else 'Fn::Sub'
                    path_template = default_path[sub_key]
                    assert path_template == "/${ProjectId}-${StageId}", \
                        "Default API origin path should match previous version: /${ProjectId}-${StageId}"


# =============================================================================
# Cache Policy Property-Based Tests
# Feature: 0-0-29-network-add-managed-cache-policies
# =============================================================================


def valid_cache_policy_arn_strategy():
    """Generate valid CloudFront cache policy ARNs."""
    # ARN format: arn:aws:cloudfront::<account-id>:cache-policy/<policy-id>
    account_id = st.text(alphabet='0123456789', min_size=12, max_size=12)
    policy_id = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-',
        min_size=1,
        max_size=50
    )
    
    return st.builds(
        lambda acc, pol: f"arn:aws:cloudfront::{acc}:cache-policy/{pol}",
        account_id, policy_id
    )


def invalid_cache_policy_arn_strategy():
    """Generate invalid CloudFront cache policy ARNs."""
    return st.one_of(
        # Missing arn: prefix
        st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-:/',
            min_size=10,
            max_size=50
        ).filter(lambda s: not s.startswith('arn:aws:cloudfront::')),
        
        # Wrong service (not cloudfront)
        st.builds(
            lambda acc, pol: f"arn:aws:s3::{acc}:cache-policy/{pol}",
            st.text(alphabet='0123456789', min_size=12, max_size=12),
            st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789-', min_size=1, max_size=20)
        ),
        
        # Wrong resource type (not cache-policy)
        st.builds(
            lambda acc, pol: f"arn:aws:cloudfront::{acc}:distribution/{pol}",
            st.text(alphabet='0123456789', min_size=12, max_size=12),
            st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789-', min_size=1, max_size=20)
        ),
        
        # Invalid account ID (not 12 digits)
        st.builds(
            lambda acc, pol: f"arn:aws:cloudfront::{acc}:cache-policy/{pol}",
            st.text(alphabet='0123456789', min_size=1, max_size=11),
            st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789-', min_size=1, max_size=20)
        ),
        
        # Invalid policy ID (contains invalid characters)
        st.builds(
            lambda acc, pol: f"arn:aws:cloudfront::{acc}:cache-policy/{pol}",
            st.text(alphabet='0123456789', min_size=12, max_size=12),
            st.text(alphabet='!@#$%^&*()', min_size=1, max_size=10)
        )
    )


class TestCustomARNValidationProperty:
    """
    Property 7: Custom ARN validation
    Validates: Requirements 9.1, 9.2, 9.3, 9.4
    
    For any string value provided as CloudFrontStaticCustomCachePolicyArn or 
    CloudFrontApiCustomCachePolicyArn, CloudFormation should accept it if and only if 
    it matches the pattern ^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$ 
    or is an empty string, and reject it with a constraint error message otherwise.
    """
    
    @given(valid_arn=valid_cache_policy_arn_strategy())
    @settings(max_examples=20)
    def test_valid_cache_policy_arns_accepted(self, valid_arn):
        """
        Test that valid cache policy ARNs match the AllowedPattern.
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        import re
        
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Test CloudFrontStaticCustomCachePolicyArn parameter
        static_arn_param = parameters.get('CloudFrontStaticCustomCachePolicyArn')
        assert static_arn_param is not None, "CloudFrontStaticCustomCachePolicyArn parameter should exist"
        
        static_pattern = static_arn_param.get('AllowedPattern')
        assert static_pattern is not None, "CloudFrontStaticCustomCachePolicyArn should have AllowedPattern"
        
        # Valid ARN should match the pattern
        static_match = re.match(static_pattern, valid_arn)
        assert static_match is not None, \
            f"Valid ARN '{valid_arn}' should be accepted by AllowedPattern '{static_pattern}'"
        
        # Test CloudFrontApiCustomCachePolicyArn parameter
        api_arn_param = parameters.get('CloudFrontApiCustomCachePolicyArn')
        assert api_arn_param is not None, "CloudFrontApiCustomCachePolicyArn parameter should exist"
        
        api_pattern = api_arn_param.get('AllowedPattern')
        assert api_pattern is not None, "CloudFrontApiCustomCachePolicyArn should have AllowedPattern"
        
        # Valid ARN should match the pattern
        api_match = re.match(api_pattern, valid_arn)
        assert api_match is not None, \
            f"Valid ARN '{valid_arn}' should be accepted by AllowedPattern '{api_pattern}'"
    
    @given(invalid_arn=invalid_cache_policy_arn_strategy())
    @settings(max_examples=20)
    def test_invalid_cache_policy_arns_rejected(self, invalid_arn):
        """
        Test that invalid cache policy ARNs do NOT match the AllowedPattern.
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        import re
        
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Test CloudFrontStaticCustomCachePolicyArn parameter
        static_arn_param = parameters.get('CloudFrontStaticCustomCachePolicyArn')
        static_pattern = static_arn_param.get('AllowedPattern')
        
        # Invalid ARN should NOT match the pattern
        static_match = re.match(static_pattern, invalid_arn)
        assert static_match is None, \
            f"Invalid ARN '{invalid_arn}' should be rejected by AllowedPattern '{static_pattern}'"
        
        # Test CloudFrontApiCustomCachePolicyArn parameter
        api_arn_param = parameters.get('CloudFrontApiCustomCachePolicyArn')
        api_pattern = api_arn_param.get('AllowedPattern')
        
        # Invalid ARN should NOT match the pattern
        api_match = re.match(api_pattern, invalid_arn)
        assert api_match is None, \
            f"Invalid ARN '{invalid_arn}' should be rejected by AllowedPattern '{api_pattern}'"
    
    def test_empty_string_accepted(self):
        """
        Test that empty string is accepted by the AllowedPattern.
        **Validates: Requirements 9.3**
        """
        import re
        
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Test CloudFrontStaticCustomCachePolicyArn parameter
        static_arn_param = parameters.get('CloudFrontStaticCustomCachePolicyArn')
        static_pattern = static_arn_param.get('AllowedPattern')
        
        # Empty string should match the pattern
        static_match = re.match(static_pattern, "")
        assert static_match is not None, \
            f"Empty string should be accepted by AllowedPattern '{static_pattern}'"
        
        # Test CloudFrontApiCustomCachePolicyArn parameter
        api_arn_param = parameters.get('CloudFrontApiCustomCachePolicyArn')
        api_pattern = api_arn_param.get('AllowedPattern')
        
        # Empty string should match the pattern
        api_match = re.match(api_pattern, "")
        assert api_match is not None, \
            f"Empty string should be accepted by AllowedPattern '{api_pattern}'"
    
    def test_constraint_description_exists(self):
        """
        Test that ConstraintDescription exists for custom ARN parameters.
        **Validates: Requirements 9.4**
        """
        network_template = load_network_template()
        parameters = network_template.get('Parameters', {})
        
        # Test CloudFrontStaticCustomCachePolicyArn parameter
        static_arn_param = parameters.get('CloudFrontStaticCustomCachePolicyArn')
        assert 'ConstraintDescription' in static_arn_param, \
            "CloudFrontStaticCustomCachePolicyArn should have ConstraintDescription"
        
        static_constraint = static_arn_param.get('ConstraintDescription')
        assert static_constraint is not None and len(static_constraint) > 0, \
            "CloudFrontStaticCustomCachePolicyArn ConstraintDescription should not be empty"
        
        # Test CloudFrontApiCustomCachePolicyArn parameter
        api_arn_param = parameters.get('CloudFrontApiCustomCachePolicyArn')
        assert 'ConstraintDescription' in api_arn_param, \
            "CloudFrontApiCustomCachePolicyArn should have ConstraintDescription"
        
        api_constraint = api_arn_param.get('ConstraintDescription')
        assert api_constraint is not None and len(api_constraint) > 0, \
            "CloudFrontApiCustomCachePolicyArn ConstraintDescription should not be empty"


class TestCachePolicyResolutionProperty:
    """
    Property 3: Static cache policy ARN resolution
    Property 4: API cache policy ARN resolution
    Property 6: Environment-based cache policy override
    Validates: Requirements 5.1-5.12, 11.1, 11.2
    
    For any valid combination of DeployEnvironment and cache policy parameters, 
    the resolved cache policy IDs should match expected values based on the 
    environment and policy type selection.
    """
    
    # Managed policy IDs from the design
    MANAGED_POLICY_IDS = {
        'CachingOptimized': '658327ea-f89d-4fab-a63d-7e88639e58f6',
        'CachingDisabled': '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',
        'CachingOptimizedForUncompressedObjects': 'b2884449-e4de-46a7-ac36-70bc7f1ddd6d',
        'Elemental-MediaPackage': '08627262-05a9-4f76-9ded-b50ca2e3a84f'
    }
    
    @given(
        deploy_env=st.sampled_from(['DEV', 'TEST', 'PROD']),
        static_policy=st.sampled_from([
            'CachingOptimized', 'CachingDisabled', 
            'CachingOptimizedForUncompressedObjects', 'Elemental-MediaPackage'
        ]),
        api_policy=st.sampled_from([
            'CachingOptimized', 'CachingDisabled', 
            'CachingOptimizedForUncompressedObjects', 'Elemental-MediaPackage'
        ])
    )
    @settings(max_examples=20)
    def test_managed_policy_resolution(self, deploy_env, static_policy, api_policy):
        """
        Test that managed cache policies resolve to correct IDs via FindInMap.
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.7, 5.8, 5.9, 5.10, 11.1, 11.2**
        """
        network_template = load_network_template()
        
        # Verify CachePolicyIds mapping exists
        mappings = network_template.get('Mappings', {})
        assert 'CachePolicyIds' in mappings, "CachePolicyIds mapping should exist"
        
        cache_policy_ids = mappings['CachePolicyIds']
        
        # Verify all managed policy IDs are in the mapping
        for policy_name, policy_id in self.MANAGED_POLICY_IDS.items():
            assert policy_name in cache_policy_ids, \
                f"Managed policy '{policy_name}' should be in CachePolicyIds mapping"
            assert cache_policy_ids[policy_name].get('Id') == policy_id, \
                f"Managed policy '{policy_name}' should have ID '{policy_id}'"
        
        # Verify the static policy is in the mapping
        assert static_policy in cache_policy_ids, \
            f"Static policy '{static_policy}' should be in CachePolicyIds mapping"
        assert cache_policy_ids[static_policy].get('Id') == self.MANAGED_POLICY_IDS[static_policy], \
            f"Static policy '{static_policy}' should have correct ID"
        
        # Verify the API policy is in the mapping
        assert api_policy in cache_policy_ids, \
            f"API policy '{api_policy}' should be in CachePolicyIds mapping"
        assert cache_policy_ids[api_policy].get('Id') == self.MANAGED_POLICY_IDS[api_policy], \
            f"API policy '{api_policy}' should have correct ID"
    
    @given(
        deploy_env=st.sampled_from(['DEV', 'TEST']),
        static_policy=st.sampled_from([
            'CachingOptimized', 'CachingDisabled', 
            'CachingOptimizedForUncompressedObjects', 'Elemental-MediaPackage',
            'CustomDefault', 'CustomArn'
        ]),
        api_policy=st.sampled_from([
            'CachingOptimized', 'CachingDisabled', 
            'CachingOptimizedForUncompressedObjects', 'Elemental-MediaPackage',
            'CustomDefault', 'CustomArn'
        ])
    )
    @settings(max_examples=20)
    def test_environment_override_for_dev_test(self, deploy_env, static_policy, api_policy):
        """
        Test that DEV and TEST environments force CachingDisabled regardless of parameter values.
        **Validates: Requirements 11.1, 11.2**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the DefaultCacheBehavior
        default_cache_behavior = dist_config.get('DefaultCacheBehavior')
        assert default_cache_behavior is not None, "DefaultCacheBehavior should exist"
        
        # Get the CachePolicyId property
        cache_policy_id = default_cache_behavior.get('CachePolicyId')
        assert cache_policy_id is not None, "CachePolicyId should exist in DefaultCacheBehavior"
        
        # CachePolicyId structure: !If [StaticOriginIsRoot, <static-logic>, <api-logic>]
        # Each branch has: !If [IsProduction, <prod-logic>, !FindInMap [CachePolicyIds, CachingDisabled, Id]]
        # For non-PROD (DEV/TEST), both branches should use CachingDisabled
        if isinstance(cache_policy_id, dict):
            if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
            assert if_key in cache_policy_id, "CachePolicyId should use !If conditional"
            
            if_list = cache_policy_id[if_key]
            assert len(if_list) == 3, "!If should have 3 elements"
            
            # First element should be StaticOriginIsRoot condition
            condition_name = if_list[0]
            assert condition_name == 'StaticOriginIsRoot', \
                "First condition should be StaticOriginIsRoot to determine origin type"
            
            # Second element (static origin branch) should have IsProduction check
            static_branch = if_list[1]
            if isinstance(static_branch, dict):
                static_if_key = '!If' if '!If' in static_branch else 'Fn::If'
                assert static_if_key in static_branch, "Static branch should use !If"
                
                static_if_list = static_branch[static_if_key]
                assert len(static_if_list) == 3, "Static !If should have 3 elements"
                assert static_if_list[0] == 'IsProduction', \
                    "Static branch should check IsProduction"
                
                # Third element (non-PROD) should be CachingDisabled
                static_non_prod = static_if_list[2]
                if isinstance(static_non_prod, dict):
                    find_in_map_key = '!FindInMap' if '!FindInMap' in static_non_prod else 'Fn::FindInMap'
                    assert find_in_map_key in static_non_prod, \
                        "Non-PROD static cache policy should use !FindInMap"
                    
                    find_in_map_list = static_non_prod[find_in_map_key]
                    assert find_in_map_list[0] == 'CachePolicyIds', \
                        "Should lookup in CachePolicyIds mapping"
                    assert find_in_map_list[1] == 'CachingDisabled', \
                        "DEV/TEST should force CachingDisabled for static origin"
                    assert find_in_map_list[2] == 'Id', \
                        "Should get the Id attribute"
            
            # Third element (API origin branch) should also have IsProduction check
            api_branch = if_list[2]
            if isinstance(api_branch, dict):
                api_if_key = '!If' if '!If' in api_branch else 'Fn::If'
                assert api_if_key in api_branch, "API branch should use !If"
                
                api_if_list = api_branch[api_if_key]
                assert len(api_if_list) == 3, "API !If should have 3 elements"
                assert api_if_list[0] == 'IsProduction', \
                    "API branch should check IsProduction"
                
                # Third element (non-PROD) should be CachingDisabled
                api_non_prod = api_if_list[2]
                if isinstance(api_non_prod, dict):
                    find_in_map_key = '!FindInMap' if '!FindInMap' in api_non_prod else 'Fn::FindInMap'
                    assert find_in_map_key in api_non_prod, \
                        "Non-PROD API cache policy should use !FindInMap"
                    
                    find_in_map_list = api_non_prod[find_in_map_key]
                    assert find_in_map_list[0] == 'CachePolicyIds', \
                        "Should lookup in CachePolicyIds mapping"
                    assert find_in_map_list[1] == 'CachingDisabled', \
                        "DEV/TEST should force CachingDisabled for API origin"
                    assert find_in_map_list[2] == 'Id', \
                        "Should get the Id attribute"
    
    def test_custom_default_resolution(self):
        """
        Test that CustomDefault resolves to resource reference.
        **Validates: Requirements 5.5, 5.11**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the DefaultCacheBehavior
        default_cache_behavior = dist_config.get('DefaultCacheBehavior')
        cache_policy_id = default_cache_behavior.get('CachePolicyId')
        
        # Navigate through the conditional structure to find CustomDefault handling
        # Structure: !If [IsProduction, <prod-logic>, <non-prod-logic>]
        # Prod logic: !If [StaticOriginIsRoot, <static-logic>, <api-logic>]
        # Static logic: !If [StaticCachePolicyIsCustomDefault, !Ref CloudFrontCachePolicyStatic, ...]
        
        if isinstance(cache_policy_id, dict):
            if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
            if_list = cache_policy_id[if_key]
            
            # Get PROD branch (second element)
            prod_branch = if_list[1]
            
            # This should be another !If for StaticOriginIsRoot
            if isinstance(prod_branch, dict):
                prod_if_key = '!If' if '!If' in prod_branch else 'Fn::If'
                prod_if_list = prod_branch[prod_if_key]
                
                # Get static origin branch (second element)
                static_branch = prod_if_list[1]
                
                # This should be another !If for StaticCachePolicyIsCustomDefault
                if isinstance(static_branch, dict):
                    static_if_key = '!If' if '!If' in static_branch else 'Fn::If'
                    static_if_list = static_branch[static_if_key]
                    
                    # First element should be StaticCachePolicyIsCustomDefault
                    assert static_if_list[0] == 'StaticCachePolicyIsCustomDefault', \
                        "Should check StaticCachePolicyIsCustomDefault condition"
                    
                    # Second element (when CustomDefault) should be !Ref CloudFrontCachePolicyStatic
                    custom_default_value = static_if_list[1]
                    if isinstance(custom_default_value, dict):
                        ref_key = '!Ref' if '!Ref' in custom_default_value else 'Ref'
                        assert ref_key in custom_default_value, \
                            "CustomDefault should use !Ref"
                        assert custom_default_value[ref_key] == 'CloudFrontCachePolicyStatic', \
                            "CustomDefault should reference CloudFrontCachePolicyStatic resource"
    
    def test_custom_arn_resolution(self):
        """
        Test that CustomArn resolves to parameter value.
        **Validates: Requirements 5.6, 5.12**
        """
        network_template = load_network_template()
        
        # Get the CloudFrontDistribution resource
        resources = network_template.get('Resources', {})
        distribution = resources.get('CloudFrontDistribution', {})
        dist_config = distribution.get('Properties', {}).get('DistributionConfig', {})
        
        # Get the DefaultCacheBehavior
        default_cache_behavior = dist_config.get('DefaultCacheBehavior')
        cache_policy_id = default_cache_behavior.get('CachePolicyId')
        
        # Navigate through the conditional structure to find CustomArn handling
        # Structure: !If [IsProduction, <prod-logic>, <non-prod-logic>]
        # Prod logic: !If [StaticOriginIsRoot, <static-logic>, <api-logic>]
        # Static logic: !If [StaticCachePolicyIsCustomDefault, ..., !If [StaticCachePolicyIsCustomArn, !Ref CloudFrontStaticCustomCachePolicyArn, ...]]
        
        if isinstance(cache_policy_id, dict):
            if_key = '!If' if '!If' in cache_policy_id else 'Fn::If'
            if_list = cache_policy_id[if_key]
            
            # Get PROD branch (second element)
            prod_branch = if_list[1]
            
            # This should be another !If for StaticOriginIsRoot
            if isinstance(prod_branch, dict):
                prod_if_key = '!If' if '!If' in prod_branch else 'Fn::If'
                prod_if_list = prod_branch[prod_if_key]
                
                # Get static origin branch (second element)
                static_branch = prod_if_list[1]
                
                # This should be another !If for StaticCachePolicyIsCustomDefault
                if isinstance(static_branch, dict):
                    static_if_key = '!If' if '!If' in static_branch else 'Fn::If'
                    static_if_list = static_branch[static_if_key]
                    
                    # Third element (when not CustomDefault) should be another !If for CustomArn
                    not_custom_default_branch = static_if_list[2]
                    if isinstance(not_custom_default_branch, dict):
                        arn_if_key = '!If' if '!If' in not_custom_default_branch else 'Fn::If'
                        arn_if_list = not_custom_default_branch[arn_if_key]
                        
                        # First element should be StaticCachePolicyIsCustomArn
                        assert arn_if_list[0] == 'StaticCachePolicyIsCustomArn', \
                            "Should check StaticCachePolicyIsCustomArn condition"
                        
                        # Second element (when CustomArn) should be !Ref CloudFrontStaticCustomCachePolicyArn
                        custom_arn_value = arn_if_list[1]
                        if isinstance(custom_arn_value, dict):
                            ref_key = '!Ref' if '!Ref' in custom_arn_value else 'Ref'
                            assert ref_key in custom_arn_value, \
                                "CustomArn should use !Ref"
                            assert custom_arn_value[ref_key] == 'CloudFrontStaticCustomCachePolicyArn', \
                                "CustomArn should reference CloudFrontStaticCustomCachePolicyArn parameter"
    
    def test_conditions_exist_for_cache_policy_types(self):
        """
        Test that all required conditions exist for cache policy resolution.
        **Validates: Requirements 5.5, 5.6, 5.11, 5.12**
        """
        network_template = load_network_template()
        conditions = network_template.get('Conditions', {})
        
        # Verify static cache policy conditions
        assert 'StaticCachePolicyIsCustomDefault' in conditions, \
            "StaticCachePolicyIsCustomDefault condition should exist"
        assert 'StaticCachePolicyIsCustomArn' in conditions, \
            "StaticCachePolicyIsCustomArn condition should exist"
        
        # Verify API cache policy conditions
        assert 'ApiCachePolicyIsCustomDefault' in conditions, \
            "ApiCachePolicyIsCustomDefault condition should exist"
        assert 'ApiCachePolicyIsCustomArn' in conditions, \
            "ApiCachePolicyIsCustomArn condition should exist"
        
        # Verify custom resource creation conditions
        assert 'CreateCustomStaticCachePolicy' in conditions, \
            "CreateCustomStaticCachePolicy condition should exist"
        assert 'CreateCustomApiCachePolicy' in conditions, \
            "CreateCustomApiCachePolicy condition should exist"
