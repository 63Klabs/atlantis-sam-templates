# Pipeline Templates

This directory contains CloudFormation templates for creating AWS CodePipeline infrastructure to automate the build and deployment of serverless applications.

## Overview

Pipeline templates provide continuous integration and continuous deployment (CI/CD) capabilities for your AWS SAM applications. They automate the process of building, testing, and deploying your application whenever changes are pushed to your source code repository.

## Available Templates

### [template-pipeline.yml](template-pipeline-README.md)
**Version:** v2.0.17 | **Last Updated:** 2025-12-16

Full-featured CI/CD pipeline for AWS SAM deployments using AWS CodeCommit as the source repository. Includes Source, Build, Deploy, and optional PostDeploy stages.

**Key Features:**
- CodeCommit repository integration with branch-specific triggers
- CodeBuild for building and packaging SAM applications
- CloudFormation deployment with changeset execution
- Optional PostDeploy stage for integration tests and configuration export
- Pipeline notifications via SNS and EventBridge
- Comprehensive IAM roles with least-privilege permissions

**Use Cases:**
- Full serverless application deployments (Lambda, API Gateway, DynamoDB, etc.)
- Applications requiring post-deployment validation or testing
- Projects using AWS CodeCommit for source control

### [template-pipeline-github.yml](template-pipeline-github-README.md)
**Version:** v2.0.1 | **Last Updated:** 2025-05-16

CI/CD pipeline for AWS SAM deployments using GitHub as the source repository via AWS CodeConnections.

**Key Features:**
- GitHub repository integration via CodeConnections
- CodeBuild for building and packaging SAM applications
- CloudFormation deployment with changeset execution
- Pipeline notifications via SNS and EventBridge
- Comprehensive IAM roles with least-privilege permissions

**Use Cases:**
- Serverless applications hosted on GitHub
- Teams using GitHub for source control and collaboration
- Projects requiring GitHub Actions integration

### [template-pipeline-build-only.yml](template-pipeline-build-only-README.md)
**Version:** v2.0.3 | **Last Updated:** 2025-05-12

Simplified pipeline with only Source and Build stages (no CloudFormation deployment). Ideal for build-and-copy workflows.

**Key Features:**
- CodeCommit repository integration
- CodeBuild for building and copying artifacts
- No CloudFormation deployment stage
- Pipeline notifications via SNS and EventBridge
- Simplified IAM roles focused on build operations

**Use Cases:**
- Static website builds that copy to S3
- Build processes that don't require CloudFormation deployment
- Custom deployment workflows handled outside the pipeline

## Common Features

All pipeline templates include:

- **Automated Triggers**: EventBridge rules detect repository changes and trigger pipeline execution
- **Build Caching**: Local caching in CodeBuild for faster builds
- **Environment Variables**: Comprehensive set of environment variables passed to build processes
- **Notifications**: Email notifications for pipeline start, success, and failure events
- **IAM Security**: Least-privilege IAM roles with permissions boundaries support
- **Multi-Environment Support**: DEV, TEST, and PROD environment configurations
- **Parameter Store Integration**: Access to SSM Parameter Store for application configuration
- **S3 Artifact Management**: Secure storage and retrieval of build artifacts

## Choosing the Right Template

| Requirement | Recommended Template |
|-------------|---------------------|
| Full SAM deployment with CodeCommit | template-pipeline.yml |
| Full SAM deployment with GitHub | template-pipeline-github.yml |
| Build-only workflow (no CloudFormation) | template-pipeline-build-only.yml |
| Post-deployment testing/validation | template-pipeline.yml (with PostDeploy enabled) |
| Static website deployment | template-pipeline-build-only.yml |

## Prerequisites

Before deploying any pipeline template, ensure you have:

1. **Source Repository**: 
   - CodeCommit repository (for template-pipeline.yml and template-pipeline-build-only.yml)
   - GitHub repository with CodeConnections setup (for template-pipeline-github.yml)

2. **S3 Artifacts Bucket**: An existing S3 bucket for storing build artifacts

3. **IAM Permissions**: Sufficient permissions to create IAM roles and policies

4. **Optional Resources**:
   - S3 bucket for static hosting (if using S3StaticHostBucket parameter)
   - Permissions boundary policy (if required by your organization)
   - External managed policies (for CloudFormationSvcRoleIncludeManagedPolicyArns, etc.)

## Deployment Steps

1. **Prepare Parameters**: Gather required parameter values (Prefix, ProjectId, StageId, Repository, etc.)

2. **Deploy Pipeline Stack**: Use AWS SAM CLI or CloudFormation console to deploy the pipeline template

3. **Confirm SNS Subscription**: Check email and confirm the SNS subscription for pipeline notifications

4. **Trigger Pipeline**: Push a commit to the watched branch to trigger the first pipeline execution

5. **Monitor Execution**: Watch the pipeline execute through the AWS CodePipeline console

## Resource Naming Convention

All resources created by pipeline templates follow this naming pattern:
```
<Prefix>-<ProjectId>-<StageId>-<ResourceId>
```

Example: `acme-myapp-prod-Pipeline`

This convention ensures:
- Unique resource names across deployments
- Easy identification of resource ownership
- Consistent IAM permission scoping

## Cost Considerations

Pipeline resources incur costs based on usage:

- **CodePipeline**: $1 per active pipeline per month
- **CodeBuild**: Charged per build minute based on compute type
- **S3**: Storage costs for artifacts
- **CloudWatch Logs**: Log storage and retention costs
- **SNS**: Minimal costs for notification delivery

To minimize costs:
- Use BUILD_GENERAL1_SMALL compute type for small projects
- Set appropriate log retention periods (default: 90 days)
- Clean up old artifacts from S3 periodically
- Use DEV environment for local testing to avoid pipeline executions

## Security Best Practices

1. **Permissions Boundaries**: Use PermissionsBoundaryArn parameter to enforce organizational policies

2. **Least Privilege**: Pipeline templates follow least-privilege principles with scoped IAM permissions

3. **Role Paths**: Use RolePath parameter to organize IAM roles by application or team

4. **Managed Policies**: Use Include*ManagedPolicyArns parameters to add external resource permissions

5. **Parameter Store**: Store sensitive configuration in SSM Parameter Store, not in code

6. **Artifact Encryption**: Consider enabling S3 bucket encryption for artifact storage

## Troubleshooting

### Pipeline Fails to Start
- Check EventBridge rule is enabled and configured correctly
- Verify repository name and branch match parameters
- Ensure SourceEventServiceRole has correct permissions

### Build Stage Fails
- Check CodeBuild logs in CloudWatch
- Verify buildspec.yml exists and is valid
- Ensure CodeBuildServiceRole has necessary permissions
- Check environment variables are set correctly

### Deploy Stage Fails
- Review CloudFormation changeset for errors
- Verify CloudFormationSvcRole has permissions for all resources
- Check template-configuration.json is valid
- Ensure parameter overrides match template parameters

### PostDeploy Stage Fails (template-pipeline.yml only)
- Check PostDeploy CodeBuild logs in CloudWatch
- Verify buildspec-postdeploy.yml exists and is valid
- Ensure PostDeployServiceRole has necessary permissions
- Confirm deployed resources are accessible

## Related Templates

Pipeline templates are typically used with:

- **Service Role Templates**: Pre-created service roles for CloudFormation
- **Storage Templates**: S3 buckets for artifacts and static hosting
- **Application Templates**: The SAM templates being deployed by the pipeline

## Additional Resources

- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [GitHub Repository](https://github.com/63klabs/atlantis-cfn-template-repo-for-serverless-deployments/)
