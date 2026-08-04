#!/bin/bash
# Verification script for Task 7.4: Verify all params/conditions/mappings 
# referenced by consumed modules remain defined in template-pipeline.yml

set -e

TEMPLATE_PATH="templates/v2/pipeline/template-pipeline.yml"

echo "📋 Verifying prerequisites for 15 modules in template-pipeline.yml"
echo "=========================================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to check if a parameter exists
check_parameter() {
    local param=$1
    if grep -q "^  ${param}:" "$TEMPLATE_PATH"; then
        echo -e "  ${GREEN}✓${NC} Parameter: $param"
        return 0
    else
        echo -e "  ${RED}✗${NC} Parameter: $param MISSING"
        ((ERRORS++))
        return 1
    fi
}

# Function to check if a condition exists
check_condition() {
    local condition=$1
    if grep -q "^  ${condition}:" "$TEMPLATE_PATH"; then
        echo -e "  ${GREEN}✓${NC} Condition: $condition"
        return 0
    else
        echo -e "  ${RED}✗${NC} Condition: $condition MISSING"
        ((ERRORS++))
        return 1
    fi
}

# Function to check if a mapping exists
check_mapping() {
    local mapping=$1
    if grep -q "^  ${mapping}:" "$TEMPLATE_PATH"; then
        echo -e "  ${GREEN}✓${NC} Mapping: $mapping"
        return 0
    else
        echo -e "  ${RED}✗${NC} Mapping: $mapping MISSING"
        ((ERRORS++))
        return 1
    fi
}

echo "Checking Parameters..."
echo "----------------------------------------"

# All unique parameters required by modules
REQUIRED_PARAMS=(
    "Prefix"
    "ProjectId"
    "StageId"
    "AlarmNotificationEmail"
    "RolePath"
    "PermissionsBoundaryArn"
    "Repository"
    "RepositoryBranch"
    "S3ArtifactsBucket"
    "S3BucketNameOrgPrefix"
    "S3StaticHostBucket"
    "ParameterStoreHierarchy"
    "DeployEnvironment"
    "BuildSpec"
    "CodeBuildSvcRoleIncludeManagedPolicyArns"
    "CloudFormationSvcRoleIncludeManagedPolicyArns"
    "PostDeployS3StaticHostBucket"
    "PostDeployBuildSpec"
    "PostDeploySvcRoleIncludeManagedPolicyArns"
)

for param in "${REQUIRED_PARAMS[@]}"; do
    check_parameter "$param"
done

echo ""
echo "Checking Conditions..."
echo "----------------------------------------"

# All unique conditions required by modules
REQUIRED_CONDITIONS=(
    "IsNotDevelopment"
    "HasPermissionsBoundaryArn"
    "HasManagedPoliciesForCodeBuildSvcRole"
    "UseS3BucketNameOrgPrefix"
    "HasS3StaticHostBucket"
    "HasS3BuildSpecLocation"
    "UseDefaultBuildSpecLocation"
    "HasManagedPoliciesForCloudFormationSvcRole"
    "IsPostDeployEnabledAndNotDev"
    "HasManagedPoliciesForPostDeploySvcRole"
    "HasPostDeployS3StaticHostBucket"
    "HasPostDeployBuildSpecS3Location"
    "UseDefaultPostDeployBuildSpecLocation"
)

for condition in "${REQUIRED_CONDITIONS[@]}"; do
    check_condition "$condition"
done

echo ""
echo "Checking Mappings..."
echo "----------------------------------------"

# Mappings required by cloudformation-svc-role module
REQUIRED_MAPPINGS=(
    "LambdaInsightsAccountId"
    "LambdaParamSecretsAccountId"
)

for mapping in "${REQUIRED_MAPPINGS[@]}"; do
    check_mapping "$mapping"
done

echo ""
echo "=========================================================================="
echo "📊 Summary:"
echo ""
echo "  Total Parameters Checked: ${#REQUIRED_PARAMS[@]}"
echo "  Total Conditions Checked: ${#REQUIRED_CONDITIONS[@]}"
echo "  Total Mappings Checked: ${#REQUIRED_MAPPINGS[@]}"
echo "  Errors: $ERRORS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ VERIFICATION PASSED${NC}"
    echo ""
    echo "All parameters, conditions, and mappings referenced by the 15 consumed"
    echo "modules are present in template-pipeline.yml, including:"
    echo "  - LambdaInsightsAccountId mapping"
    echo "  - LambdaParamSecretsAccountId mapping"
    echo ""
    exit 0
else
    echo -e "${RED}❌ VERIFICATION FAILED${NC}"
    echo ""
    echo "$ERRORS missing prerequisites found."
    echo ""
    exit 1
fi
