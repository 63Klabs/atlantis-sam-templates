# Implementation Plan: Pipeline SSM Parameter Access

## Overview

Add `ssm:GetParameter` and `ssm:GetParameters` permissions for public AWS SSM parameters (`/aws/service/*`) to the `CloudFormationSvcRole` inline policy in the pipeline template. This is a non-breaking, additive change (PATCH increment). The service role template requires no changes.

## Tasks

- [x] 1. Version management
  - [x] 1.1 Increment version for template-pipeline.yml
    - Current version is v2.0.18 (PATCH > 0), increment to v2.0.19
    - Update the date to the current date in the header comment
    - _Requirements: N/A (version control steering document)_

- [x] 2. Add SSM public parameter read policy statement
  - [x] 2.1 Add SSMPublicParameterReadOnly statement to CloudFormationSvcRole inline policy
    - Add a new IAM policy statement immediately after the existing `SSMParameterStoreReadThisDeploymentOnly` statement (around line 1105 in `templates/v2/pipeline/template-pipeline.yml`)
    - Statement Sid: `SSMPublicParameterReadOnly`
    - Actions: `ssm:GetParameter` and `ssm:GetParameters` only
    - Effect: `Allow`
    - Resource: `!Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/aws/service/*"`
    - Add a comment `# == SSM Public Parameters (Read-Only) ==` above the statement for consistency with existing comment style
    - Verify the existing `SSMParameterStoreReadThisDeploymentOnly` statement is not modified
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 3.1, 3.2, 3.3_

  - [ ]* 2.2 Write unit tests for SSMPublicParameterReadOnly statement
    - Create `tests/test_pipeline_ssm_access_unit.py`
    - Use `cfn_test_utils.load_template()` to load `templates/v2/pipeline/template-pipeline.yml`
    - Test that `SSMPublicParameterReadOnly` statement exists in the CloudFormationSvcRole policy
    - Test that the statement has Effect `Allow`
    - Test that the statement contains exactly `ssm:GetParameter` and `ssm:GetParameters` actions
    - Test that the statement does not contain `ssm:GetParametersByPath`, `ssm:PutParameter`, or `ssm:DeleteParameter`
    - Test that the resource ARN contains `parameter/aws/service/*` and references `${AWS::Region}` and `${AWS::AccountId}`
    - Test that the existing `SSMParameterStoreReadThisDeploymentOnly` statement is preserved with its original actions (`ssm:GetParameters`, `ssm:GetParameter`, `ssm:GetParametersByPath`, `ssm:ListTagsForResource`) and resource referencing `ParameterStoreHierarchy`
    - Test that the service role template's `ManageWorkerRolesByResourcePrefix` statement includes `iam:PutRolePolicy`
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 3.1, 3.2, 3.3_

  - [ ]* 2.3 Write property test: Public SSM statement exists with correct actions and distinct Sid
    - Create `tests/test_pipeline_ssm_access_property.py`
    - Use `hypothesis` with `@settings(max_examples=10)`
    - **Property 1: Public SSM statement exists with correct actions and distinct Sid**
    - **Validates: Requirements 1.1, 1.2, 1.5**

  - [ ]* 2.4 Write property test: Existing application-specific SSM statement is preserved
    - In `tests/test_pipeline_ssm_access_property.py`
    - **Property 2: Existing application-specific SSM statement is preserved**
    - **Validates: Requirements 1.4**

  - [ ]* 2.5 Write property test: Public SSM resource ARN is scoped to /aws/service/* only
    - In `tests/test_pipeline_ssm_access_property.py`
    - **Property 3: Public SSM resource ARN is scoped to /aws/service/* only**
    - **Validates: Requirements 3.1, 3.3**

  - [ ]* 2.6 Write property test: Public SSM statement grants only read-only actions
    - In `tests/test_pipeline_ssm_access_property.py`
    - **Property 4: Public SSM statement grants only read-only actions**
    - **Validates: Requirements 3.2**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Documentation updates
  - [x] 4.1 Update pipeline template README documentation
    - Update `docs/templates/v2/pipeline/template-pipeline-README.md`
    - Update the version number and last updated date
    - Document the new `SSMPublicParameterReadOnly` IAM policy statement in the Resources section under the CloudFormationSvcRole
    - Note that this enables `{{resolve:ssm:/aws/service/...}}` dynamic references in application templates
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 4.2 Update CHANGELOG.md
    - Add entry for `[template-pipeline] v2.0.19` documenting the new SSM public parameter read access
    - Categorize under "Added" section
    - _Requirements: 1.1, 1.2_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The service role template (`template-service-role-pipeline.yml`) requires no changes — existing `iam:PutRolePolicy` on `${Prefix}-Worker-*` already covers the CloudFormationSvcRole
- This is a non-breaking PATCH change: adds a new IAM policy statement without modifying existing statements, parameters, resources, or outputs
- Property tests use `hypothesis` library consistent with existing project patterns (see `tests/test_network_template_property.py`)
- Unit and property tests both use `cfn_test_utils.load_template()` to load and parse templates
