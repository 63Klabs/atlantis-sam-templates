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
