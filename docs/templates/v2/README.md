# CloudFormation Templates v2

Comprehensive collection of CloudFormation templates for building serverless applications on AWS with best practices for security, cost optimization, and operational excellence.

## Overview

This repository provides production-ready CloudFormation templates organized into four categories:

- **[Network](#network-templates)**: CloudFront distributions, Route53 DNS, API Gateway custom domains
- **[Pipeline](#pipeline-templates)**: CI/CD pipelines with CodePipeline, CodeBuild, and GitHub integration
- **[Service Role](#service-role-templates)**: IAM roles and policies for AWS services
- **[Storage](#storage-templates)**: S3 buckets and DynamoDB tables for various use cases

All templates follow semantic versioning and include comprehensive documentation, parameter validation, and example configurations.

## Template Categories

### Network Templates

[View Network Templates Documentation](./network/README.md)

Network templates handle routing and content delivery for serverless applications.

| Template | Description | Use Cases |
|----------|-------------|-----------|
| [template-network-route53-cloudfront-s3-apigw](./network/template-network-route53-cloudfront-s3-apigw-README.md) | CloudFront distribution with Route53 DNS for S3 and/or API Gateway | Static websites, SPAs, API custom domains, full-stack applications |

**Common Use Cases:**
- Static website hosting with custom domain and CDN
- API Gateway with custom domain and optional caching
- Combined static frontend and API backend on same domain
- Multi-environment deployments with automatic subdomain naming

---

### Pipeline Templates

[View Pipeline Templates Documentation](./pipeline/README.md)

Pipeline templates automate building, testing, and deploying serverless applications.

| Template | Description | Use Cases |
|----------|-------------|-----------|
| [template-pipeline](./pipeline/template-pipeline-README.md) | Full CI/CD pipeline with CodeCommit, build, and deploy stages | Complete deployment automation, multi-stage deployments, post-deploy testing |
| [template-pipeline-github](./pipeline/template-pipeline-github-README.md) | CI/CD pipeline with GitHub source via CodeConnections | GitHub-based projects, open source projects, external repositories |
| [template-pipeline-build-only](./pipeline/template-pipeline-build-only-README.md) | Build-only pipeline without deploy stage | Static websites, custom deployment workflows, build artifact generation |

**Common Use Cases:**
- Automated SAM application deployments
- Static website builds and deployments
- Multi-environment CI/CD workflows
- Post-deployment testing and validation
- GitHub-integrated development workflows

---

### Service Role Templates

[View Service Role Templates Documentation](./service-role/README.md)

Service role templates create IAM roles and policies for AWS services to interact with your resources.

| Template | Description | Use Cases |
|----------|-------------|-----------|
| [template-service-role-api-gateway-cloudwatch](./service-role/template-service-role-api-gateway-cloudwatch-README.md) | Account-level IAM role for API Gateway CloudWatch logging | API Gateway logging, CloudWatch integration |
| [template-service-role-codeconnections-github](./service-role/template-service-role-codeconnections-github-README.md) | GitHub connection for CodePipeline | GitHub repository access, CodePipeline source stage |
| [template-service-role-pipeline](./service-role/template-service-role-pipeline-README.md) | Prefix-based service role for pipeline management | CloudFormation deployments, CodePipeline execution, CodeBuild projects |
| [template-service-role-storage](./service-role/template-service-role-storage-README.md) | Prefix-based service role for storage management | S3 operations, DynamoDB access, Lambda deployments |

**Common Use Cases:**
- CloudFormation service roles for stack deployments
- CodePipeline and CodeBuild execution roles
- API Gateway CloudWatch logging
- GitHub repository integration
- Least-privilege IAM policies for AWS services

---

### Storage Templates

[View Storage Templates Documentation](./storage/README.md)

Storage templates provide S3 buckets and DynamoDB tables for data persistence, caching, logging, and artifacts.

| Template | Description | Use Cases |
|----------|-------------|-----------|
| [template-storage-cache-data](./storage/template-storage-cache-data-README.md) | S3 bucket and DynamoDB table for Lambda caching | Lambda function caching, external API caching, temporary data storage |
| [template-storage-s3-access-logs](./storage/template-storage-s3-access-logs-README.md) | S3 bucket for storing access logs | Centralized logging, compliance, audit trails, security monitoring |
| [template-storage-s3-artifacts](./storage/template-storage-s3-artifacts-README.md) | S3 bucket for CodeBuild/CodePipeline artifacts | CI/CD artifacts, build outputs, deployment packages |
| [template-storage-s3-devops](./storage/template-storage-s3-devops-README.md) | S3 bucket for shared DevOps resources | Reusable Lambda functions, buildspecs, scripts, CloudFormation includes |
| [template-storage-s3-oac-for-cloudfront](./storage/template-storage-s3-oac-for-cloudfront-README.md) | S3 bucket as CloudFront origin with OAC | Static websites, SPAs, CDN-served content, automatic cache invalidation |

**Common Use Cases:**
- Static website hosting through CloudFront
- CI/CD pipeline artifact storage
- Lambda function caching layer
- Centralized logging and compliance
- Shared DevOps tooling and scripts

## Template Versioning

All templates follow [Semantic Versioning](https://semver.org/) with the format `vMAJOR.MINOR.PATCH`:

- **MAJOR**: Critical breaking changes requiring user intervention
- **MINOR**: Non-critical breaking changes
- **PATCH**: Non-breaking changes, bug fixes, improvements

### Version Format

Each template includes a version comment at the top:

```yaml
# Version: v2.0.17/2025-01-28
```

### Development vs Production

- **PATCH = 0** (e.g., v2.0.0): Development mode, breaking changes allowed
- **PATCH > 0** (e.g., v2.0.1): Production mode, semantic versioning enforced

### Breaking Changes

Breaking changes require creating a new versioned template file:

- **Non-Critical Breaking**: `template-name-v2-1.yml` (MINOR bump)
- **Critical Breaking**: `template-name-v3-0.yml` (MAJOR bump)

Old versions are maintained for 24 months after deprecation before being archived.

## Getting Started

### Prerequisites

Before using these templates, ensure you have:

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Configured with credentials
3. **CloudFormation Access**: Permissions to create stacks
4. **Service Roles**: Deploy service role templates first (if needed)
5. **Supporting Resources**: Some templates require existing resources (S3 buckets, hosted zones, etc.)

### Deployment Order

For a complete serverless application, deploy templates in this order:

1. **Service Roles**: Create IAM roles for CloudFormation and other services
   - `template-service-role-pipeline.yml`
   - `template-service-role-storage.yml`
   - `template-service-role-api-gateway-cloudwatch.yml` (if using API Gateway)

2. **Storage**: Create S3 buckets and DynamoDB tables
   - `template-storage-s3-access-logs.yml` (for logging)
   - `template-storage-s3-artifacts.yml` (for CI/CD)
   - `template-storage-s3-devops.yml` (for shared resources)
   - `template-storage-s3-oac-for-cloudfront.yml` (for static content)
   - `template-storage-cache-data.yml` (for Lambda caching)

3. **Application**: Deploy your SAM application
   - Your custom SAM template with Lambda functions, API Gateway, etc.

4. **Network**: Configure routing and custom domains
   - `template-network-route53-cloudfront-s3-apigw.yml`

5. **Pipeline**: Automate deployments
   - `template-pipeline-github.yml` or `template-pipeline.yml`

### Parameter Naming Conventions

Templates use consistent parameter naming:

- **Prefix**: Organization or team identifier (e.g., "WS", "ACME")
- **ProjectId**: Specific project identifier (e.g., "my-app")
- **StageId**: Environment stage (e.g., "dev", "test", "prod")
- **DeployEnvironment**: Deployment environment ("DEV", "TEST", "PROD")

### Resource Naming Pattern

Resources are named using the pattern:

```
{Prefix}-{ProjectId}-{StageId}-{ResourceType}
```

Example: `WS-my-app-prod-Bucket`

## Common Architecture Patterns

### Pattern 1: Static Website with CDN

```
GitHub → CodePipeline → CodeBuild → S3 → CloudFront → Route53 → Users
```

**Templates Used:**
1. `template-service-role-pipeline.yml`
2. `template-storage-s3-artifacts.yml`
3. `template-storage-s3-oac-for-cloudfront.yml`
4. `template-network-route53-cloudfront-s3-apigw.yml`
5. `template-pipeline-github.yml`

---

### Pattern 2: Serverless API with Custom Domain

```
GitHub → CodePipeline → CodeBuild → SAM Deploy → API Gateway → Route53 → Users
                                              → Lambda Functions
                                              → DynamoDB
```

**Templates Used:**
1. `template-service-role-pipeline.yml`
2. `template-service-role-storage.yml`
3. `template-service-role-api-gateway-cloudwatch.yml`
4. `template-storage-s3-artifacts.yml`
5. `template-storage-cache-data.yml`
6. Your SAM application template
7. `template-network-route53-cloudfront-s3-apigw.yml`
8. `template-pipeline-github.yml`

---

### Pattern 3: Full-Stack Application

```
GitHub → CodePipeline → CodeBuild → S3 (static) → CloudFront → Route53 → Users
                                  → SAM Deploy → API Gateway ↗
                                              → Lambda Functions
                                              → DynamoDB
```

**Templates Used:**
1. `template-service-role-pipeline.yml`
2. `template-service-role-storage.yml`
3. `template-storage-s3-artifacts.yml`
4. `template-storage-s3-oac-for-cloudfront.yml`
5. `template-storage-cache-data.yml`
6. Your SAM application template
7. `template-network-route53-cloudfront-s3-apigw.yml`
8. `template-pipeline-github.yml`

---

### Pattern 4: Multi-Environment Deployment

Deploy the same application across multiple environments with environment-specific configurations:

- **Production**: `app.example.com`
- **Test**: `app-test.example.com`
- **Dev**: `app-dev.example.com`

Each environment uses the same templates with different parameter values (StageId, DeployEnvironment).

## Best Practices

### Security

1. **Use Service Roles**: Always use dedicated service roles with least-privilege permissions
2. **Enable Encryption**: All S3 buckets and DynamoDB tables use encryption at rest
3. **Block Public Access**: S3 buckets have public access blocked by default
4. **HTTPS Only**: Enforce HTTPS for all S3 and API Gateway access
5. **Origin Access Control**: Use OAC for CloudFront to S3 access (never public buckets)
6. **Permissions Boundaries**: Apply when required by your organization

### Cost Optimization

1. **Lifecycle Policies**: Automatically delete old objects from S3
2. **PAY_PER_REQUEST**: Use for DynamoDB with variable traffic
3. **CloudFront Price Classes**: Use PriceClass_100 for non-production
4. **Cache TTLs**: Configure appropriate cache durations
5. **Resource Tagging**: Tag all resources for cost allocation

### Operational Excellence

1. **Parameter Validation**: Use AllowedValues and AllowedPattern constraints
2. **Metadata Grouping**: Organize parameters into logical groups
3. **Comprehensive Outputs**: Provide console links and resource identifiers
4. **Conditional Resources**: Use conditions for optional features
5. **Documentation**: Keep template documentation up to date

### Reliability

1. **Deletion Policies**: Retain critical resources (logs, DevOps buckets)
2. **Versioning**: Enable versioning on artifact buckets
3. **Backup and Recovery**: Plan for disaster recovery
4. **Multi-Region**: Consider multi-region deployments for critical applications
5. **Monitoring**: Set up CloudWatch alarms and logging

## Troubleshooting

### Common Issues

**Stack Creation Fails**
- Check IAM permissions for CloudFormation service role
- Verify all prerequisite resources exist
- Review parameter values for correctness
- Check CloudFormation events for specific error messages

**Resource Name Too Long**
- Shorten Prefix or ProjectId parameters
- Ensure Prefix + ProjectId ≤ 28 characters for S3 buckets
- Use S3BucketNameOrgPrefix parameter for shorter names

**Access Denied Errors**
- Verify service role has required permissions
- Check resource policies allow the service
- Ensure HTTPS is being used for S3 access
- Verify ARN patterns match resources

**CloudFront 403 Errors**
- Check S3 bucket policy allows OAC access
- Verify objects exist in correct paths
- Ensure CloudFront distribution ARN matches policy

**Pipeline Fails to Deploy**
- Verify service role has CloudFormation permissions
- Check artifact bucket is accessible
- Ensure SAM template is valid
- Review CodeBuild logs for build errors

### Getting Help

- **GitHub Issues**: Report bugs or request features
- **AWS Documentation**: Comprehensive AWS service documentation
- **Template Documentation**: Detailed docs for each template in this repository
- **CloudFormation Events**: Check stack events for error details

## Additional Resources

### AWS Documentation

- [AWS CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/)
- [AWS CloudFront Developer Guide](https://docs.aws.amazon.com/cloudfront/)
- [Amazon S3 User Guide](https://docs.aws.amazon.com/s3/)

### Best Practices

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Serverless Application Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/)
- [Security Best Practices](https://docs.aws.amazon.com/security/)
- [Cost Optimization](https://aws.amazon.com/pricing/cost-optimization/)

### Repository

- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
- [Issues and Feature Requests](https://github.com/63Klabs/atlantis-sam-templates/issues)
- [Security Reports](https://github.com/63Klabs/atlantis-sam-templates/security)
- [Latest Updates](https://github.com/63Klabs/atlantis-sam-templates/releases)

## Contributing

Contributions are welcome! Please:

1. Follow the existing template structure and conventions
2. Include comprehensive documentation
3. Add parameter validation and metadata
4. Provide example configurations
5. Test templates before submitting
6. Update version numbers appropriately

## License

See repository LICENSE file for details.

---

**Author**: Chad Kluck - 63klabs.net

**Last Updated**: 2025-01-29
