"""
CloudFormation template validation utilities for testing.

This module provides helper functions for loading, parsing, and validating
CloudFormation templates, supporting both unit and property-based testing.
"""

import yaml
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class CFNLoader(yaml.SafeLoader):
    """YAML loader that handles CloudFormation intrinsic functions."""
    pass


def cfn_constructor(loader, node):
    """Generic constructor for CloudFormation intrinsic functions."""
    if isinstance(node, yaml.ScalarNode):
        return {node.tag: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {node.tag: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {node.tag: loader.construct_mapping(node)}
    return {node.tag: None}


# Register CloudFormation intrinsic functions
CFN_TAGS = [
    '!Ref', '!GetAtt', '!Sub', '!Join', '!If', '!Not', '!Equals', 
    '!And', '!Or', '!Select', '!Split', '!Base64', '!Cidr',
    '!FindInMap', '!GetAZs', '!ImportValue', '!Condition'
]

for tag in CFN_TAGS:
    CFNLoader.add_constructor(tag, cfn_constructor)


def load_template(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    Load and parse a CloudFormation YAML template.
    
    Args:
        filepath: Path to the CloudFormation template file
        
    Returns:
        Parsed template as a dictionary
        
    Raises:
        FileNotFoundError: If template file doesn't exist
        yaml.YAMLError: If template has invalid YAML syntax
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Template file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.load(f, Loader=CFNLoader)


def get_template_section(template: Dict[str, Any], section: str) -> Dict[str, Any]:
    """
    Get a specific section from a CloudFormation template.
    
    Args:
        template: Parsed CloudFormation template
        section: Section name (e.g., 'Parameters', 'Resources', 'Conditions')
        
    Returns:
        Dictionary containing the requested section, empty dict if not found
    """
    return template.get(section, {})


def find_resources_by_type(template: Dict[str, Any], resource_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Find all resources of a specific type in the template.
    
    Args:
        template: Parsed CloudFormation template
        resource_type: AWS resource type (e.g., 'AWS::CodeBuild::Project')
        
    Returns:
        Dictionary mapping resource names to resource definitions
    """
    resources = get_template_section(template, 'Resources')
    return {
        name: resource for name, resource in resources.items()
        if resource.get('Type') == resource_type
    }


def find_resources_with_condition(template: Dict[str, Any], condition_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Find all resources that use a specific condition.
    
    Args:
        template: Parsed CloudFormation template
        condition_name: Name of the condition to search for
        
    Returns:
        Dictionary mapping resource names to resource definitions
    """
    resources = get_template_section(template, 'Resources')
    matching_resources = {}
    
    for name, resource in resources.items():
        resource_condition = resource.get('Condition')
        if resource_condition == condition_name:
            matching_resources[name] = resource
        elif isinstance(resource_condition, dict):
            # Handle complex conditions
            condition_str = str(resource_condition)
            if condition_name in condition_str:
                matching_resources[name] = resource
    
    return matching_resources


def get_parameter_references(obj: Any, param_name: str) -> List[str]:
    """
    Recursively find all references to a parameter in a CloudFormation object.
    
    Args:
        obj: CloudFormation object (dict, list, or primitive)
        param_name: Parameter name to search for
        
    Returns:
        List of reference locations found
    """
    references = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == '!Ref' and value == param_name:
                references.append(f"!Ref {param_name}")
            else:
                references.extend(get_parameter_references(value, param_name))
    elif isinstance(obj, list):
        for item in obj:
            references.extend(get_parameter_references(item, param_name))
    elif isinstance(obj, str) and obj == param_name:
        references.append(obj)
    
    return references


def validate_parameter_constraints(template: Dict[str, Any], param_name: str) -> Dict[str, Any]:
    """
    Validate parameter constraints and return constraint information.
    
    Args:
        template: Parsed CloudFormation template
        param_name: Parameter name to validate
        
    Returns:
        Dictionary containing parameter constraint information
        
    Raises:
        KeyError: If parameter doesn't exist
    """
    parameters = get_template_section(template, 'Parameters')
    if param_name not in parameters:
        raise KeyError(f"Parameter '{param_name}' not found in template")
    
    param = parameters[param_name]
    constraints = {}
    
    # Extract common constraint types
    constraint_fields = [
        'Type', 'Default', 'AllowedValues', 'AllowedPattern',
        'MinLength', 'MaxLength', 'MinValue', 'MaxValue'
    ]
    
    for field in constraint_fields:
        if field in param:
            constraints[field] = param[field]
    
    return constraints


def validate_condition_logic(template: Dict[str, Any], condition_name: str) -> Dict[str, Any]:
    """
    Validate condition logic and return condition information.
    
    Args:
        template: Parsed CloudFormation template
        condition_name: Condition name to validate
        
    Returns:
        Dictionary containing condition structure information
        
    Raises:
        KeyError: If condition doesn't exist
    """
    conditions = get_template_section(template, 'Conditions')
    if condition_name not in conditions:
        raise KeyError(f"Condition '{condition_name}' not found in template")
    
    condition = conditions[condition_name]
    
    # Analyze condition structure
    analysis = {
        'condition_name': condition_name,
        'condition_def': condition,
        'type': None,
        'parameters_referenced': [],
        'conditions_referenced': []
    }
    
    # Determine condition type
    if isinstance(condition, dict):
        if '!Equals' in condition:
            analysis['type'] = 'Equals'
        elif '!And' in condition:
            analysis['type'] = 'And'
        elif '!Or' in condition:
            analysis['type'] = 'Or'
        elif '!Not' in condition:
            analysis['type'] = 'Not'
        elif '!Condition' in condition:
            analysis['type'] = 'ConditionRef'
    
    # Find parameter references
    condition_str = str(condition)
    template_params = get_template_section(template, 'Parameters')
    for param_name in template_params.keys():
        if param_name in condition_str:
            analysis['parameters_referenced'].append(param_name)
    
    # Find condition references
    template_conditions = get_template_section(template, 'Conditions')
    for cond_name in template_conditions.keys():
        if cond_name != condition_name and cond_name in condition_str:
            analysis['conditions_referenced'].append(cond_name)
    
    return analysis


def validate_iam_policy_structure(policy_document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate IAM policy document structure.
    
    Args:
        policy_document: IAM policy document
        
    Returns:
        Dictionary containing policy analysis
    """
    analysis = {
        'version': policy_document.get('Version'),
        'statements': [],
        'statement_count': 0,
        'actions': set(),
        'resources': set(),
        'effects': set()
    }
    
    statements = policy_document.get('Statement', [])
    if not isinstance(statements, list):
        statements = [statements]
    
    analysis['statement_count'] = len(statements)
    
    for i, statement in enumerate(statements):
        stmt_analysis = {
            'index': i,
            'sid': statement.get('Sid'),
            'effect': statement.get('Effect'),
            'actions': [],
            'resources': [],
            'conditions': statement.get('Condition')
        }
        
        # Extract actions
        actions = statement.get('Action', [])
        if isinstance(actions, str):
            actions = [actions]
        stmt_analysis['actions'] = actions
        analysis['actions'].update(actions)
        
        # Extract resources
        resources = statement.get('Resource', [])
        if isinstance(resources, str):
            resources = [resources]
        stmt_analysis['resources'] = resources
        analysis['resources'].update(str(r) for r in resources)
        
        # Track effects
        if stmt_analysis['effect']:
            analysis['effects'].add(stmt_analysis['effect'])
        
        analysis['statements'].append(stmt_analysis)
    
    return analysis


def validate_environment_variables(env_vars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate CodeBuild environment variables structure.
    
    Args:
        env_vars: List of environment variable definitions
        
    Returns:
        Dictionary containing environment variable analysis
    """
    analysis = {
        'variable_count': len(env_vars),
        'variables': {},
        'variable_names': set(),
        'parameter_references': set(),
        'hardcoded_values': set()
    }
    
    for env_var in env_vars:
        name = env_var.get('Name')
        value = env_var.get('Value')
        var_type = env_var.get('Type', 'PLAINTEXT')
        
        if name:
            analysis['variable_names'].add(name)
            analysis['variables'][name] = {
                'value': value,
                'type': var_type
            }
            
            # Analyze value type
            if isinstance(value, dict) and '!Ref' in value:
                analysis['parameter_references'].add(value['!Ref'])
            elif isinstance(value, str) and not any(func in str(value) for func in CFN_TAGS):
                analysis['hardcoded_values'].add(value)
    
    return analysis


def compare_resource_properties(resource1: Dict[str, Any], resource2: Dict[str, Any], 
                              properties_to_compare: List[str]) -> Dict[str, Any]:
    """
    Compare specific properties between two resources.
    
    Args:
        resource1: First resource definition
        resource2: Second resource definition
        properties_to_compare: List of property paths to compare (e.g., ['Environment.ComputeType'])
        
    Returns:
        Dictionary containing comparison results
    """
    comparison = {
        'matching_properties': [],
        'differing_properties': [],
        'missing_in_resource1': [],
        'missing_in_resource2': []
    }
    
    def get_nested_property(resource: Dict[str, Any], property_path: str) -> Any:
        """Get a nested property using dot notation."""
        keys = property_path.split('.')
        current = resource.get('Properties', {})
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    for prop_path in properties_to_compare:
        value1 = get_nested_property(resource1, prop_path)
        value2 = get_nested_property(resource2, prop_path)
        
        if value1 is None and value2 is None:
            continue
        elif value1 is None:
            comparison['missing_in_resource1'].append(prop_path)
        elif value2 is None:
            comparison['missing_in_resource2'].append(prop_path)
        elif value1 == value2:
            comparison['matching_properties'].append(prop_path)
        else:
            comparison['differing_properties'].append({
                'property': prop_path,
                'resource1_value': value1,
                'resource2_value': value2
            })
    
    return comparison


def validate_pipeline_stages(pipeline_resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate CodePipeline stages configuration.
    
    Args:
        pipeline_resource: CodePipeline resource definition
        
    Returns:
        Dictionary containing pipeline stage analysis
    """
    analysis = {
        'stage_count': 0,
        'stages': [],
        'stage_names': [],
        'conditional_stages': False,
        'postdeploy_stage_present': False
    }
    
    properties = pipeline_resource.get('Properties', {})
    stages = properties.get('Stages')
    
    if stages is None:
        return analysis
    
    # Handle conditional stages
    if isinstance(stages, dict) and '!If' in stages:
        analysis['conditional_stages'] = True
        if_condition = stages['!If']
        
        if len(if_condition) >= 2:
            # Analyze both branches
            stages_with_condition = if_condition[1] if len(if_condition) > 1 else []
            stages_without_condition = if_condition[2] if len(if_condition) > 2 else []
            
            # Check stages with condition
            for stage in stages_with_condition:
                stage_name = stage.get('Name', '')
                analysis['stage_names'].append(f"{stage_name} (conditional)")
                if stage_name == 'PostDeploy':
                    analysis['postdeploy_stage_present'] = True
            
            analysis['stage_count'] = len(stages_with_condition)
    elif isinstance(stages, list):
        # Direct stage list
        analysis['stage_count'] = len(stages)
        for stage in stages:
            stage_name = stage.get('Name', '')
            analysis['stage_names'].append(stage_name)
            if stage_name == 'PostDeploy':
                analysis['postdeploy_stage_present'] = True
    
    return analysis


def validate_regex_pattern(pattern: str, test_strings: List[str]) -> Dict[str, Any]:
    """
    Validate a regex pattern against test strings.
    
    Args:
        pattern: Regular expression pattern
        test_strings: List of strings to test against the pattern
        
    Returns:
        Dictionary containing validation results
    """
    try:
        compiled_pattern = re.compile(pattern)
    except re.error as e:
        return {
            'valid_pattern': False,
            'error': str(e),
            'matches': {},
            'match_count': 0
        }
    
    results = {
        'valid_pattern': True,
        'pattern': pattern,
        'matches': {},
        'match_count': 0,
        'matching_strings': [],
        'non_matching_strings': []
    }
    
    for test_string in test_strings:
        match = compiled_pattern.match(test_string)
        results['matches'][test_string] = match is not None
        
        if match:
            results['matching_strings'].append(test_string)
            results['match_count'] += 1
        else:
            results['non_matching_strings'].append(test_string)
    
    return results


# =============================================================================
# Lightweight CFN condition / intrinsic evaluators for promotion tests
# -----------------------------------------------------------------------------
# These helpers statically evaluate a small, known subset of CloudFormation
# intrinsic functions (as parsed by CFNLoader, i.e. short-form tag keys like
# '!Not', '!Equals', '!Ref', '!Condition', '!And', '!Or', as well as long-form
# 'Fn::If'/'Ref'/'Fn::Sub' used inside AWS::Include modules) against a supplied
# set of parameter values. They are intentionally narrow (only what these
# templates actually use) rather than a general-purpose CFN interpreter.
# =============================================================================


def _tag_get(mapping, *keys):
    """Return (key, value) for the first key present in mapping, else (None, None)."""
    for key in keys:
        if key in mapping:
            return key, mapping[key]
    return None, None


def resolve_ref_shortform(value, params):
    """Resolve a short-form !Ref (or Ref) node to its parameter value.

    Non-Ref values are returned unchanged (e.g. literal strings used as the
    right-hand side of !Equals).
    """
    if isinstance(value, dict):
        _, name = _tag_get(value, '!Ref', 'Ref')
        if name is not None:
            return params.get(name, '')
    return value


def eval_condition(cond_def, conditions, params):
    """Evaluate a short-form CFN Condition definition given parameter values.

    Supports the subset of intrinsics used by this repository's pipeline
    templates: !Not, !And, !Or, !Equals, !Condition, plus bare !Ref/literal
    comparison operands.

    Args:
        cond_def: The condition's AST (as parsed by CFNLoader) OR a condition
            name (str) to look up in `conditions`.
        conditions: The template's full Conditions section (dict of name -> AST).
        params: Dict of parameter name -> string value to use for !Ref lookups.

    Returns:
        bool: The evaluated truth value of the condition.
    """
    if isinstance(cond_def, str):
        # Treat as a condition name reference.
        return eval_condition(conditions[cond_def], conditions, params)

    if not isinstance(cond_def, dict):
        return bool(cond_def)

    key, val = _tag_get(cond_def, '!Not', 'Fn::Not')
    if key is not None:
        return not eval_condition(val[0], conditions, params)

    key, val = _tag_get(cond_def, '!And', 'Fn::And')
    if key is not None:
        return all(eval_condition(c, conditions, params) for c in val)

    key, val = _tag_get(cond_def, '!Or', 'Fn::Or')
    if key is not None:
        return any(eval_condition(c, conditions, params) for c in val)

    key, val = _tag_get(cond_def, '!Equals', 'Fn::Equals')
    if key is not None:
        left = resolve_ref_shortform(val[0], params)
        right = resolve_ref_shortform(val[1], params)
        return left == right

    key, val = _tag_get(cond_def, '!Condition', 'Condition')
    if key is not None:
        return eval_condition(val, conditions, params)

    raise ValueError(f"Unsupported condition AST: {cond_def!r}")


def get_included_stage_names(stages, conditions, params):
    """Given a Stages list (with possible !If-wrapped conditional stages),
    return the ordered list of stage Names that would render given `params`.

    Each entry in `stages` is either:
      - a plain stage dict with a 'Name' key, or
      - {'!If': [condition_name, stage_dict, <else-branch>]}

    The else-branch (typically !Ref AWS::NoValue) causes the stage to be
    omitted when the condition is false.
    """
    included = []
    for entry in stages:
        if isinstance(entry, dict):
            key, if_args = _tag_get(entry, '!If', 'Fn::If')
            if key is not None:
                cond_name, true_val, _false_val = if_args
                if eval_condition(cond_name, conditions, params):
                    included.append(true_val.get('Name'))
                continue
            included.append(entry.get('Name'))
    return included


def resolve_longform(value, conditions_bool, refs):
    """Resolve a long-form (AWS::Include module) intrinsic-function AST to a
    concrete string, given precomputed condition booleans and Ref values.

    Supports: Fn::If, Ref, Fn::GetAtt (returns a placeholder), and Fn::Sub
    (both the plain-string form and the [template, {vars}] form).

    Args:
        value: The AST node to resolve.
        conditions_bool: Dict of condition name -> bool (supplied directly by
            the test; these modules don't define their own Conditions section).
        refs: Dict of Ref/pseudo-parameter name -> string value.
    """
    if isinstance(value, dict):
        if 'Fn::If' in value:
            cond_name, true_val, false_val = value['Fn::If']
            branch = true_val if conditions_bool[cond_name] else false_val
            return resolve_longform(branch, conditions_bool, refs)

        if 'Ref' in value:
            name = value['Ref']
            return refs.get(name, f"{{{name}}}")

        if 'Fn::GetAtt' in value:
            return "{{GetAtt:%s}}" % ".".join(value['Fn::GetAtt'])

        if 'Fn::Sub' in value:
            sub_val = value['Fn::Sub']
            if isinstance(sub_val, str):
                template, var_map = sub_val, {}
            else:
                template, var_map = sub_val[0], sub_val[1]

            resolved_vars = {
                k: resolve_longform(v, conditions_bool, refs)
                for k, v in var_map.items()
            }

            def repl(match):
                name = match.group(1)
                if name in resolved_vars:
                    return str(resolved_vars[name])
                return str(refs.get(name, f"{{{name}}}"))

            return re.sub(r"\$\{([^}]+)\}", repl, template)

    return value
