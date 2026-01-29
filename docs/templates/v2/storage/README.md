# Storage Templates

Storage infrastructure templates for S3 buckets, DynamoDB tables, and related storage resources for serverless applications.

## Overview

Storage templates provide the foundation for data persistence, caching, logging, and artifact management in serverless applications. They create properly configured S3 buckets and DynamoDB tables with appropriate security policies, encryption, lifecycle management, and access controls.

## Templates

### [template-storage-cache-data](./template-storage-cache-data-README.md)

Shared storage for Lambda applications utilizing Cache-Data (S3/DynamoDb).

**Use Cases:**
- Implement caching layer for Lambda functions
- Store and retrieve cached data with automatic expiration
- Cache large objects in S3 with metadata in DynamoDB
- Share cached data across multiple Lambda functions

**Key Features:**
- DynamoDB table with TTL for automatic expiration
- S3 bucket with lifecycle policies for cost optimization
- PAY_PER_REQUEST billing for variable traffic
- Optional managed IAM policy for Lambda execution roles

**Prerequisites:**
- Understanding of @63klabs/cache-data npm package

---

### [template-storage-s3-access-logs](./template-storage-s3-access-logs-README.md)

S3 bucket for storing S3 access logs from other buckets.

**Use Cases:**
- Centralized logging for S3 bucket access
- Compliance and audit trail
- Security monitoring and analysis
- Automatic log retention management

**Key Features:**
- Configured for S3 log delivery service
- Automatic log expiration (configurable 1-365 days)
- Encryption and public access blocking
- Retained on stack deletion for compliance

**Prerequisites:**
- None (standalone logging bucket)

---

### [template-storage-s3-artifacts](./template-storage-s3-artifacts-README.md)

S3 bucket for storing CodeBuild and CodeDeploy artifacts.

**Use Cases:**
- Store CodeBuild build artifacts
- Store CodePipeline artifacts between stages
- Store CloudFormation templates and deployment packages
- Centralized artifact storage for CI/CD pipelines

**Key Features:**
- Versioning enabled for artifact history
- Automatic cleanup (2 years current, 30 days non-current)
- Access restricted to CodePipeline, CodeBuild, CloudFormation
- Optional account-wide access (empty prefix)

**Prerequisites:**
- CodePipeline and/or CodeBuild projects (for access control)

---

### [template-storage-s3-devops](./template-storage-s3-devops-README.md)

S3 bucket for storing shared DevOps files (buildspecs, scripts, reusable Lambda source).

**Use Cases:**
- Store reusable Lambda function source code
- Store buildspec files for multiple CodeBuild projects
- Store common build scripts
- Store CloudFormation template includes
- Centralize DevOps tooling and scripts

**Key Features:**
- Versioning suspended (latest version only)
- No lifecycle policies (files kept indefinitely)
- Access for CloudFormation and CodeBuild
- Retained on stack deletion (critical infrastructure)

**Prerequisites:**
- CodeBuild project (optional, for managing contents)

---

### [template-storage-s3-oac-for-cloudfront](./template-storage-s3-oac-for-cloudfront-README.md)

S3 bucket configured as CloudFront origin with Origin Access Control (OAC) and optional automatic cache invalidation.

**Use Cases:**
- Serve static websites through CloudFront
- Host single-page applications (SPAs)
- Store and serve static assets via CDN
- Automatic CloudFront cache invalidation on content changes

**Key Features:**
- Origin Access Control (OAC) for secure CloudFront access
- S3 event notifications for automatic cache invalidation
- Access restricted to CloudFront and CodeBuild
- Optional logging and alarm notifications

**Prerequisites:**
- CloudFront distribution (from network templates)
- Lambda invalidator function (optional, for auto-invalidation)

## Common Use Cases

### Static Website Hosting

Use `template-storage-s3-oac-for-cloudfront` with network templates to serve static websites:
1. Create S3 bucket with OAC
2. Create CloudFront distribution pointing to bucket
3. Deploy static content via CodeBuild
4. Automatic cache invalidation on updates

### CI/CD Pipeline Storage

Use `template-storage-s3-artifacts` for pipeline artifact storage:
1. Create artifacts bucket
2. Configure CodePipeline to use bucket
3. Automatic cleanup of old artifacts
4. Version tracking for rollbacks

### Shared DevOps Resources

Use `template-storage-s3-devops` for reusable scripts and functions:
1. Create DevOps bucket
2. Upload shared Lambda functions, buildspecs, scripts
3. Reference from multiple stacks and pipelines
4. Manage via CodeBuild or manual uploads

### Lambda Caching Layer

Use `template-storage-cache-data` for Lambda function caching:
1. Create cache-data infrastructure
2. Configure Lambda functions with @63klabs/cache-data
3. Automatic expiration via DynamoDB TTL
4. Cost-effective PAY_PER_REQUEST billing

### Centralized Logging

Use `template-storage-s3-access-logs` for S3 access logging:
1. Create logging bucket
2. Configure other S3 buckets to log to it
3. Automatic log expiration
4. Retained for compliance

## Architecture Patterns

### Pattern 1: Static Website with CDN

```
CodeBuild → S3 (OAC) → CloudFront → Users
                ↓
         Lambda Invalidator
```

Best for: Static websites, SPAs, documentation sites

### Pattern 2: CI/CD Pipeline

```
GitHub → CodePipeline → CodeBuild → S3 Artifacts → CloudFormation
```

Best for: Automated deployments, multi-stage pipelines

### Pattern 3: Shared DevOps Resources

```
CodeBuild → S3 DevOps ← CloudFormation Stacks
                      ← CodeBuild Projects
                      ← Lambda Functions
```

Best for: Reusable scripts, shared Lambda functions, common buildspecs

### Pattern 4: Lambda with Caching

```
API Gateway → Lambda → DynamoDB (Cache Metadata)
                    → S3 (Cache Data)
```

Best for: API backends, data processing, external API caching

## Cost Considerations

### S3 Storage Costs

- **Standard Storage**: $0.023 per GB/month (first 50 TB)
- **Requests**: $0.0004 per 1,000 PUT requests, $0.0004 per 10,000 GET requests
- **Data Transfer**: Free to CloudFront, $0.09 per GB to internet

### DynamoDB Costs

- **PAY_PER_REQUEST**: $1.25 per million write requests, $0.25 per million read requests
- **Storage**: $0.25 per GB/month
- **No minimum capacity charges**

### Cost Optimization Tips

1. **Use Lifecycle Policies**: Automatically delete old objects
   - Artifacts: 2 years current, 30 days non-current
   - Logs: 90 days (configurable)
   - Cache: 15-30 days based on TTL

2. **Enable Bucket Key Encryption**: Reduces encryption costs by 99%

3. **Use PAY_PER_REQUEST for DynamoDB**: No capacity planning, pay only for usage

4. **Leverage CloudFront**: Free data transfer from S3 to CloudFront

5. **Monitor and Clean Up**: Regularly review and delete unused resources

## Security Best Practices

### S3 Security

1. **Block Public Access**: Always enabled on all templates
2. **Encryption at Rest**: AES256 encryption on all buckets
3. **Encryption in Transit**: HTTPS-only via bucket policies
4. **Least Privilege Access**: Service-specific policies with ARN restrictions
5. **Logging**: Enable access logging for audit trails

### DynamoDB Security

1. **Encryption at Rest**: Enabled by default
2. **IAM Policies**: Least privilege access for Lambda functions
3. **VPC Endpoints**: Use VPC endpoints for private access (when applicable)

### IAM Best Practices

1. **Service Roles**: Use service-specific roles with minimal permissions
2. **Resource Restrictions**: Limit access by ARN patterns
3. **Permissions Boundaries**: Apply when required by organization
4. **Role Paths**: Organize roles by application or team

## Deployment Notes

### Deployment Order

1. **Logging Bucket** (`template-storage-s3-access-logs`) - First, for other buckets to log to
2. **Artifacts Bucket** (`template-storage-s3-artifacts`) - For pipeline artifacts
3. **DevOps Bucket** (`template-storage-s3-devops`) - For shared resources
4. **Cache-Data** (`template-storage-cache-data`) - For application caching
5. **Origin Bucket** (`template-storage-s3-oac-for-cloudfront`) - For CloudFront origins

### Update Behavior

- **S3 Buckets**: Most updates are in-place, but bucket name changes require replacement
- **DynamoDB Tables**: Most updates are in-place, but key schema changes require replacement
- **Bucket Policies**: Always in-place updates
- **IAM Policies**: In-place updates, but may affect active resources

### Deletion Policies

- **Logging Bucket**: Retain (preserve logs)
- **Artifacts Bucket**: Delete (artifacts not needed after pipeline deletion)
- **DevOps Bucket**: Retain (critical infrastructure)
- **Cache-Data Bucket**: Delete (cache can be regenerated)
- **Cache-Data Table**: Delete (cache can be regenerated)
- **Origin Bucket**: Delete (content can be redeployed)

## Integration with Other Templates

Storage templates work with:

- **Network Templates**: CloudFront distributions use origin buckets
  - `template-network-route53-cloudfront-s3-apigw.yml`

- **Pipeline Templates**: CI/CD pipelines use artifacts and DevOps buckets
  - `template-pipeline-github.yml`
  - `template-pipeline-build-only.yml`

- **Service Role Templates**: IAM roles for deployments
  - `template-service-role-storage.yml`
  - `template-service-role-pipeline.yml`

- **Application Templates**: Lambda functions use cache-data and DevOps resources

## Troubleshooting

### Common Issues

**Bucket Name Too Long**
- Shorten ProjectId parameter
- Use S3BucketNameOrgPrefix parameter
- Ensure Prefix + ProjectId ≤ 28 characters

**Access Denied Errors**
- Verify service role has correct permissions
- Check bucket policy allows the service
- Ensure ARN patterns match resources
- Verify HTTPS is being used

**Lifecycle Policies Not Working**
- Policies take 24-48 hours to take effect
- Verify objects are older than expiration period
- Check that policies are enabled
- Confirm prefix patterns match objects

**DynamoDB TTL Not Deleting Items**
- TTL deletes within 48 hours of expiration
- Verify TTL is enabled on correct attribute
- Check that purge_ts attribute is set correctly
- Ensure timestamp is in Unix epoch seconds

**CloudFront Cannot Access S3**
- Verify OAC is configured on distribution
- Check bucket policy allows CloudFront service
- Ensure distribution ARN matches policy pattern
- Verify objects exist in expected paths

## Additional Resources

- [S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [CloudFront Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [DynamoDB Time To Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [@63klabs/cache-data npm package](https://www.npmjs.com/package/@63klabs/cache-data)
