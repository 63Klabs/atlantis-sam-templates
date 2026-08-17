# Pipeline Templates

This directory contains CloudFormation templates for creating AWS CodePipeline infrastructure to automate the build and deployment of serverless applications.

## Overview

Pipeline templates provide continuous integration and continuous deployment (CI/CD) capabilities for your AWS SAM applications. They automate the process of building, testing, and deploying your application whenever changes are pushed to your source code repository.

## Available Templates

### [template-pipeline.yml](template-pipeline-README.md)
**Version:** v2.0.23 | **Last Updated:** 2026-08-15

Full-featured CI/CD pipeline for AWS SAM deployments using AWS CodeCommit as the source repository. Includes Source, Build, Deploy, optional PostDeploy, and optional promotion (Approve-to-Promote + Promote) stages.

**Key Features:**
- CodeCommit repository integration with branch-specific triggers
- CodeBuild for building and packaging SAM applications
- CloudFormation deployment with changeset execution
- Optional PostDeploy stage for integration tests and configuration export
- Optional, default-off promotion to a downstream stage (same or cross account/region)
- Pipeline notifications via SNS and EventBridge
- Comprehensive IAM roles with least-privilege permissions

**Use Cases:**
- Full serverless application deployments (Lambda, API Gateway, DynamoDB, etc.)
- Applications requiring post-deployment validation or testing
- Projects using AWS CodeCommit for source control
- Multi-stage promotion pipelines (e.g. test → beta → prod)

### [template-pipeline-github.yml](template-pipeline-github-README.md)
**Version:** v2.0.5 | **Last Updated:** 2026-08-15

CI/CD pipeline for AWS SAM deployments using GitHub as the source repository via AWS CodeConnections. Includes optional promotion (Approve-to-Promote + Promote) stages.

**Key Features:**
- GitHub repository integration via CodeConnections
- CodeBuild for building and packaging SAM applications
- CloudFormation deployment with changeset execution
- Optional, default-off promotion to a downstream stage (same or cross account/region)
- Pipeline notifications via SNS and EventBridge
- Comprehensive IAM roles with least-privilege permissions

**Use Cases:**
- Serverless applications hosted on GitHub
- Teams using GitHub for source control and collaboration
- Projects requiring GitHub Actions integration
- Multi-stage promotion pipelines (e.g. test → beta → prod)

### [template-pipeline-build-only.yml](template-pipeline-build-only-README.md)
**Version:** v2.0.7 | **Last Updated:** 2026-08-15

Simplified pipeline with only Source and Build stages (no CloudFormation deployment). Ideal for build-and-copy workflows. Includes optional promotion (Approve-to-Promote + Promote) stages.

**Key Features:**
- CodeCommit repository integration
- CodeBuild for building and copying artifacts
- No CloudFormation deployment stage
- Optional, default-off promotion to a downstream stage (same or cross account/region)
- Pipeline notifications via SNS and EventBridge
- Simplified IAM roles focused on build operations

**Use Cases:**
- Static website builds that copy to S3
- Build processes that don't require CloudFormation deployment
- Custom deployment workflows handled outside the pipeline

### [template-pipeline-promoted-artifact.yml](template-pipeline-promoted-artifact-README.md)
**Version:** v0.0.0 | **Last Updated:** 2026-08-15

S3-triggered "receiving" pipeline for cross-account (or same-account) promotion. Triggered by an EventBridge rule when an origin pipeline's Promote stage writes a promoted source archive (`source.zip`) into the account-wide artifacts bucket under `promotions/*`. Rebuilds and deploys from that archive with the same Build behavior as the origin pipelines, and can itself chain promotion onward (e.g. `beta` → `prod`).

**Key Features:**
- S3 Source action watching a stable, per-target trigger key (no polling)
- Optional `ApproveRelease` manual approval gate before Build (default-on)
- Deploy stage optional/skippable (`DeployStageEnabled`) for build-only-style receiving workloads
- Supports its own optional PostDeploy and promotion (Approve-to-Promote + Promote) stages for chained promotion
- Pipeline notifications via SNS and EventBridge

**Use Cases:**
- Receiving side of cross-account promotion (DEV/TEST/PROD account topology)
- Same-account multi-stage promotion (e.g. test → beta → prod within one account)
- Auditable, approval-gated release into beta/prod environments

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
| Receiving side of a promoted (cross-account/stage) deployment | template-pipeline-promoted-artifact.yml |
| Sending side of a promotion (test → beta, beta → prod, etc.) | Any origin template above, with the Promotion parameter group configured |

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

### Promote Stage Fails or Receiving Pipeline Doesn't Trigger (origin templates)
- Verify `PromoteTargetStageId` equals the receiving pipeline's `StageId` exactly
- For cross-account promotion, confirm the receiving account's `PromotionSourceAccountIds` includes the sending account
- Confirm the receiving account-wide bucket was deployed with `EnableS3ArtifactsBucketEventBridge="true"`
- Check the Promote CodeBuild logs (`/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote`) for the exact S3 error

## Related Templates

Pipeline templates are typically used with:

- **Service Role Templates**: Pre-created service roles for CloudFormation
- **Storage Templates**: S3 buckets for artifacts and static hosting
- **Account Templates**: [account-wide-infrastructure.yml](../account/account-wide-infrastructure-README.md) provides the account-wide artifacts bucket, cross-account promotion bucket policy, and EventBridge opt-in used by promotion
- **Application Templates**: The SAM templates being deployed by the pipeline

## Additional Resources

- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
