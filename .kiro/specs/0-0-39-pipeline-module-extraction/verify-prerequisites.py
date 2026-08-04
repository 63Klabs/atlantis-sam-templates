#!/usr/bin/env python3
"""
Verification script for Task 7.4: Verify all params/conditions/mappings 
referenced by consumed modules remain defined in template-pipeline.yml

This script checks that template-pipeline.yml defines all prerequisites 
required by the 15 modules it will consume.
"""

import yaml
import sys
from pathlib import Path

# Module prerequisites from design.md
MODULE_PREREQUISITES = {
    # Notification modules (1-5)
    "pipeline-notification-topic.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId", "AlarmNotificationEmail"],
        "conditions": [],
        "mappings": []
    },
    "pipeline-notification-started-rule.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId"],
        "conditions": [],
        "mappings": [],
        "sibling_resources": ["PipelineNotificationTopic"]
    },
    "pipeline-notification-succeeded-rule.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId"],
        "conditions": [],
        "mappings": [],
        "sibling_resources": ["PipelineNotificationTopic"]
    },
    "pipeline-notification-failed-rule.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId"],
        "conditions": [],
        "mappings": [],
        "sibling_resources": ["PipelineNotificationTopic"]
    },
    "pipeline-notification-topic-policy.yml": {
        "parameters": [],
        "conditions": [],
        "mappings": [],
        "sibling_resources": ["PipelineNotificationTopic"]
    },
    
    # Source trigger modules (6-7)
    "source-event-service-role.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId", "RolePath", "PermissionsBoundaryArn"],
        "conditions": ["IsNotDevelopment", "HasPermissionsBoundaryArn"],
        "mappings": []
    },
    "source-event-rule.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId", "Repository", "RepositoryBranch"],
        "conditions": ["IsNotDevelopment"],
        "mappings": [],
        "sibling_resources": ["SourceEventServiceRole"]
    },
    
    # Build support modules (8-10)
    "codebuild-log-group.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId"],
        "conditions": ["IsNotDevelopment"],
        "mappings": []
    },
    "codebuild-service-role.yml": {
        "parameters": [
            "Prefix", "ProjectId", "StageId", "RolePath", "PermissionsBoundaryArn",
            "S3ArtifactsBucket", "S3BucketNameOrgPrefix", "S3StaticHostBucket",
            "ParameterStoreHierarchy", "DeployEnvironment", "BuildSpec",
            "CodeBuildSvcRoleIncludeManagedPolicyArns"
        ],
        "conditions": [
            "IsNotDevelopment", "HasPermissionsBoundaryArn", 
            "HasManagedPoliciesForCodeBuildSvcRole", "UseS3BucketNameOrgPrefix",
            "HasS3StaticHostBucket", "HasS3BuildSpecLocation"
        ],
        "mappings": []
    },
    "codebuild-project.yml": {
        "parameters": [
            "Prefix", "ProjectId", "StageId", "S3ArtifactsBucket",
            "S3BucketNameOrgPrefix", "Repository", "RepositoryBranch",
            "ParameterStoreHierarchy", "DeployEnvironment", "AlarmNotificationEmail",
            "S3StaticHostBucket", "RolePath", "PermissionsBoundaryArn", "BuildSpec"
        ],
        "conditions": [
            "IsNotDevelopment", "UseS3BucketNameOrgPrefix",
            "HasS3BuildSpecLocation", "UseDefaultBuildSpecLocation"
        ],
        "mappings": [],
        "sibling_resources": ["CodeBuildServiceRole"]
    },
    
    # Deploy service role modules (11-12)
    "cloudformation-svc-role.yml": {
        "parameters": [
            "Prefix", "ProjectId", "StageId", "RolePath", "PermissionsBoundaryArn",
            "S3ArtifactsBucket", "S3BucketNameOrgPrefix", "ParameterStoreHierarchy",
            "DeployEnvironment", "CloudFormationSvcRoleIncludeManagedPolicyArns"
        ],
        "conditions": [
            "HasPermissionsBoundaryArn", "HasManagedPoliciesForCloudFormationSvcRole",
            "UseS3BucketNameOrgPrefix"
        ],
        "mappings": ["LambdaInsightsAccountId", "LambdaParamSecretsAccountId"]
    },
    "codedeploy-service-role.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId", "RolePath", "PermissionsBoundaryArn"],
        "conditions": ["HasPermissionsBoundaryArn"],
        "mappings": []
    },
    
    # PostDeploy modules (13-15)
    "postdeploy-service-role.yml": {
        "parameters": [
            "Prefix", "ProjectId", "StageId", "RolePath", "PermissionsBoundaryArn",
            "S3ArtifactsBucket", "S3BucketNameOrgPrefix", "ParameterStoreHierarchy",
            "DeployEnvironment", "PostDeployS3StaticHostBucket", "PostDeployBuildSpec",
            "PostDeploySvcRoleIncludeManagedPolicyArns"
        ],
        "conditions": [
            "IsPostDeployEnabledAndNotDev", "HasPermissionsBoundaryArn",
            "HasManagedPoliciesForPostDeploySvcRole", "HasPostDeployS3StaticHostBucket",
            "HasPostDeployBuildSpecS3Location", "UseS3BucketNameOrgPrefix"
        ],
        "mappings": []
    },
    "postdeploy-project.yml": {
        "parameters": [
            "Prefix", "ProjectId", "StageId", "S3ArtifactsBucket",
            "S3BucketNameOrgPrefix", "Repository", "RepositoryBranch",
            "ParameterStoreHierarchy", "DeployEnvironment", "AlarmNotificationEmail",
            "PostDeployS3StaticHostBucket", "RolePath", "PermissionsBoundaryArn",
            "PostDeployBuildSpec"
        ],
        "conditions": [
            "IsPostDeployEnabledAndNotDev", "UseS3BucketNameOrgPrefix",
            "HasPostDeployBuildSpecS3Location", "UseDefaultPostDeployBuildSpecLocation"
        ],
        "mappings": [],
        "sibling_resources": ["PostDeployServiceRole"]
    },
    "postdeploy-log-group.yml": {
        "parameters": ["Prefix", "ProjectId", "StageId"],
        "conditions": ["IsPostDeployEnabledAndNotDev"],
        "mappings": []
    }
}


def load_template(template_path):
    """Load CloudFormation template from YAML file."""
    with open(template_path, 'r') as f:
        return yaml.safe_load(f)


def verify_prerequisites(template, module_name, prereqs):
    """Verify that template contains all prerequisites for a module."""
    errors = []
    warnings = []
    
    # Check parameters
    template_params = set(template.get('Parameters', {}).keys())
    required_params = set(prereqs.get('parameters', []))
    missing_params = required_params - template_params
    if missing_params:
        errors.append(f"  Missing parameters: {', '.join(sorted(missing_params))}")
    
    # Check conditions
    template_conditions = set(template.get('Conditions', {}).keys())
    required_conditions = set(prereqs.get('conditions', []))
    missing_conditions = required_conditions - template_conditions
    if missing_conditions:
        errors.append(f"  Missing conditions: {', '.join(sorted(missing_conditions))}")
    
    # Check mappings
    template_mappings = set(template.get('Mappings', {}).keys())
    required_mappings = set(prereqs.get('mappings', []))
    missing_mappings = required_mappings - template_mappings
    if missing_mappings:
        errors.append(f"  Missing mappings: {', '.join(sorted(missing_mappings))}")
    
    # Check sibling resources (these will be present AFTER module integration)
    sibling_resources = prereqs.get('sibling_resources', [])
    if sibling_resources:
        warnings.append(f"  Note: Module references sibling resources: {', '.join(sibling_resources)}")
    
    return errors, warnings


def main():
    """Main verification function."""
    template_path = Path(__file__).parent.parent.parent.parent / 'templates' / 'v2' / 'pipeline' / 'template-pipeline.yml'
    
    if not template_path.exists():
        print(f"❌ ERROR: Template not found at {template_path}")
        return 1
    
    print(f"📋 Loading template: {template_path}")
    template = load_template(template_path)
    
    print(f"\n🔍 Verifying prerequisites for 15 modules consumed by template-pipeline.yml\n")
    print("=" * 80)
    
    all_errors = []
    all_warnings = []
    
    for module_name, prereqs in sorted(MODULE_PREREQUISITES.items()):
        print(f"\n✓ {module_name}")
        errors, warnings = verify_prerequisites(template, module_name, prereqs)
        
        if errors:
            all_errors.extend([f"{module_name}:"] + errors)
            for error in errors:
                print(f"  ❌ {error}")
        else:
            print(f"  ✅ All prerequisites present")
        
        if warnings:
            all_warnings.extend([f"{module_name}:"] + warnings)
            for warning in warnings:
                print(f"  ⚠️  {warning}")
    
    print("\n" + "=" * 80)
    print(f"\n📊 Summary:")
    print(f"  Modules checked: {len(MODULE_PREREQUISITES)}")
    print(f"  Errors found: {len([e for e in all_errors if not e.endswith(':')])} ")
    print(f"  Warnings: {len([w for w in all_warnings if not w.endswith(':')])} ")
    
    if all_errors:
        print("\n❌ VERIFICATION FAILED - Missing prerequisites:")
        for error in all_errors:
            print(f"  {error}")
        return 1
    else:
        print("\n✅ VERIFICATION PASSED - All prerequisites are present in template-pipeline.yml")
        
        # Print collected unique parameters, conditions, and mappings
        all_params = set()
        all_conditions = set()
        all_mappings = set()
        
        for prereqs in MODULE_PREREQUISITES.values():
            all_params.update(prereqs.get('parameters', []))
            all_conditions.update(prereqs.get('conditions', []))
            all_mappings.update(prereqs.get('mappings', []))
        
        print(f"\n📋 Complete prerequisite list:")
        print(f"\n  Parameters ({len(all_params)}):")
        for param in sorted(all_params):
            print(f"    - {param}")
        
        print(f"\n  Conditions ({len(all_conditions)}):")
        for condition in sorted(all_conditions):
            print(f"    - {condition}")
        
        if all_mappings:
            print(f"\n  Mappings ({len(all_mappings)}):")
            for mapping in sorted(all_mappings):
                print(f"    - {mapping}")
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
