# template-network-route53-cloudfront-s3-apigw

Serves Static Content (S3) and/or API Gateway via CloudFront with custom domain (Route53) - Deployed using SAM

**Version:** v0.0.16/2026-02-02  
**Template:** [templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml](../../../../templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml)

## Overview

This template creates a complete network infrastructure for serving static content from S3 and/or API Gateway endpoints through CloudFront with custom domain names managed by Route53. It provides flexible routing options allowing static content and APIs to share the same domain with path-based routing or use separate domains.

### Use Cases

- Serve a static website from S3 with a custom domain
- Expose an API Gateway with a custom domain (with or without CloudFront)
- Combine static content and API on the same domain with path-based routing
- Set up CloudFront distributions with Origin Access Control (OAC) for S3
- Configure multi-stage deployments (dev, test, prod) with environment-specific settings

### Prerequisites

- Existing S3 bucket (if deploying static content) - created by storage templates
- Existing API Gateway (if deploying API) - created by application templates
- Route53 hosted zone for your domain
- ACM certificate in us-east-1 (for CloudFront) and/or regional certificate (for API Gateway)
- CloudFormation Service Role with appropriate permissions
- (Optional) S3 bucket for CloudFront access logs with appropriate bucket policy allowing CloudFront to write logs

### Important Notes

- CloudFront distributions can take 15-20 minutes to deploy or update
- ACM certificates for CloudFront must be in us-east-1 region
- The template uses Origin Access Control (OAC) for S3, not the legacy Origin Access Identity (OAI)
- Non-production stages automatically append the stage ID to subdomain names
- DEV and TEST environments use PriceClass_100 regardless of the CloudFrontPriceClass parameter

## Parameters

### Application Resource Naming

Parameters that define the naming convention for all resources created by this template.

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [StageId](#stageid)

### Origins for S3 and/or API Gateway

Configure the origin sources for your CloudFront distribution or API Gateway.

- [S3OriginDomainName](#s3origindomainname)
- [StaticOriginPath](#staticoriginpath)
- [ApiGatewayId](#apigatewayid)
- [ApiOriginPath](#apioriginpath)

### Deployment Environment

Settings that control deployment behavior and resource configurations based on environment.

- [DeployEnvironment](#deployenvironment)
- [CloudFrontPriceClass](#cloudfrontpriceclass)

### Cache Policies

Configure cache policies for CloudFront distribution origins. Choose between AWS managed policies, custom default policies, or custom ARN-based policies.

- [CloudFrontStaticCachePolicy](#cloudfrontstaticcachepolicy)
- [CloudFrontStaticCustomCachePolicyArn](#cloudfrontstaticustomcachepolicyarn)
- [CloudFrontApiCachePolicy](#cloudfrontapicachepolicy)
- [CloudFrontApiCustomCachePolicyArn](#cloudfrontapicustomcachepolicyarn)

### Static CloudFront Function Associations

Associate existing CloudFront Functions with static content cache behaviors. CloudFront Functions are lightweight JavaScript functions that run at edge locations for request/response manipulation. The functions must be created separately; these parameters associate them with the static content behaviors.

- [CloudFrontStaticFunctionViewerRequest](#cloudfrontstaticfunctionviewerrequest)
- [CloudFrontStaticFunctionViewerResponse](#cloudfrontstaticfunctionviewerresponse)
- [CloudFrontStaticFunctionOriginRequest](#cloudfrontstaticfunctionoriginrequest)
- [CloudFrontStaticFunctionOriginResponse](#cloudfrontstaticfunctionoriginresponse)

### API CloudFront Function Associations

Associate existing CloudFront Functions with API origin cache behaviors. CloudFront Functions are lightweight JavaScript functions that run at edge locations for request/response manipulation. The functions must be created separately; these parameters associate them with the API origin behaviors.

- [CloudFrontApiFunctionViewerRequest](#cloudfrontapifunctionviewerrequest)
- [CloudFrontApiFunctionViewerResponse](#cloudfrontapifunctionviewerresponse)
- [CloudFrontApiFunctionOriginRequest](#cloudfrontapifunctionoriginrequest)
- [CloudFrontApiFunctionOriginResponse](#cloudfrontapifunctionoriginresponse)

### Supporting Resources

Optional references to external resources that support the infrastructure.

- [S3LogBucketName](#s3logbucketname)

### Routing for CloudFront

Configure custom domain routing for CloudFront distribution serving static content and/or API.

- [DomainForCloudFront](#domainforcloudfront)
- [CustomSubdomainCloudFront](#customsubdomaincloudfront)
- [PathStatic](#pathstatic)
- [AcmCertificateArnForCloudFront](#acmcertificatearnforcloudfront)

### Routing for API Gateway

Configure custom domain routing for standalone API Gateway (not behind CloudFront).

- [DomainForApiGateway](#domainforapigateway)
- [CustomSubdomainApiGateway](#customsubdomainapigateway)
- [PathApi](#pathapi)
- [AcmCertificateArnForApiGateway](#acmcertificatearnforapigateway)

### API behind CloudFront Forwarding

Configure header forwarding when API Gateway is placed behind CloudFront.

- [HeadersToForwardToApi](#headerstoforwardtoapi)

---

#### Prefix

Prefix pre-pended to all resources. This can be thought of as a Name Space used to identify ownership/access for teams, departments, etc. For example, resources named ws-* could belong to the web service team and could have IAM permissions to allow access to other ws-* resources. The Prefix must have a corresponding CloudFormation Service Role. Short, descriptive 2-6 character values work best. Due to resource naming length restrictions, length of Prefix + Project ID should not exceed 28 characters. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### ProjectId

This is the Project or Application Identifier. If you receive 'S3 bucket name too long' errors during stack creation, then you must shorten the Project ID or use an S3 Org Prefix. Due to resource naming length restrictions, length of Prefix + Project ID should not exceed 28 characters. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,24}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 26 |
| Constraint Description | Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### StageId

This is an alias for the branch. It does not need to match CodeCommitBranch or DeployEnvironment. Due to resource naming restrictions you can use this to provide shorter names without special characters that are allowed in branch names. For example if you have a 'test/feature-98' branch, you could use 'tf98' as the StageId. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

#### S3OriginDomainName

If deploying static content to S3, an already existing S3 bucket to deploy static content to. Leave blank if not deploying static content from S3. This must be the Domain listed in the Outputs of the CloudFormation stack that created the bucket. This is also available from the S3 bucket properties.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\.s3\.(([a-z0-9-]+)\.)?amazonaws\.com$\|^$` |
| Constraint Description | Must be a valid Bucket Domain Name. |

#### StaticOriginPath

Custom origin path for static S3 content. This parameter allows you to customize the path prefix that CloudFront uses when requesting content from the S3 origin. Leave empty to use the default path structure (`/${StageId}/public`). Use `/` for root path (no prefix). Use a custom path like `/static` or `/v1/content` to organize your S3 bucket structure according to your project needs.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty - uses default path) |
| Allowed Pattern | `^$\|^\/$\|^\/[a-zA-Z0-9\/_-]+[^\/]$` |
| Constraint Description | Must be empty (default), `/` (root), or a path starting with `/` and not ending with `/`. Valid examples: `/static`, `/v1/content`, `/app/public`. Do not use placeholders like `{StageId}`. |

**Valid Path Formats:**
- Empty string (default): Uses `/${StageId}/public` (e.g., `/prod/public`)
- `/`: Uses root path (no prefix)
- `/static`: Custom path for static content
- `/v1/content`: Versioned content path
- `/app/public`: Multi-level custom path

**Invalid Path Formats:**
- `static` - Missing leading `/`
- `/static/` - Trailing `/` not allowed (except single `/`)
- `/${StageId}/public` - Placeholder syntax not allowed

> **Migration Note:** If you have existing deployments using the default path structure (`/${StageId}/public`), you can now customize this by setting `StaticOriginPath` to a different value. Leave the parameter empty to maintain backward compatibility with existing deployments.

#### ApiGatewayId

If deploying an API, an already existing API Gateway to deploy to. Leave blank if not deploying an API Gateway custom domain. This must be the API Gateway ID that is found in the API domain. For example, xyz123abc would be the ID from xyz123abc.execute-api.us-east-1.amazonaws.com.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9]{1,14}$\|^$` |
| Constraint Description | Must be a valid API Gateway ID. May only contain alphanumeric characters. |

#### ApiOriginPath

Custom origin path for API Gateway. This parameter allows you to customize the path prefix that CloudFront uses when requesting content from the API Gateway origin. Leave empty to use the default path structure (`/${ProjectId}-${StageId}`). Use `/` for root path (no prefix). Use a custom path like `/api` or `/v2/services` to match your API Gateway stage configuration or custom path structures.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty - uses default path) |
| Allowed Pattern | `^$\|^\/$\|^\/[a-zA-Z0-9\/_-]+[^\/]$` |
| Constraint Description | Must be empty (default), `/` (root), or a path starting with `/` and not ending with `/`. Valid examples: `/api`, `/v2/services`, `/prod`. Do not use placeholders like `{StageId}`. |

**Valid Path Formats:**
- Empty string (default): Uses `/${ProjectId}-${StageId}` (e.g., `/myapp-prod`)
- `/`: Uses root path (no prefix)
- `/api`: Custom path for API
- `/v2/services`: Versioned API path
- `/prod`: Stage-specific path

**Invalid Path Formats:**
- `api` - Missing leading `/`
- `/api/` - Trailing `/` not allowed (except single `/`)
- `/${ProjectId}-${StageId}` - Placeholder syntax not allowed

> **Migration Note:** If you have existing deployments using the default path structure (`/${ProjectId}-${StageId}`), you can now customize this by setting `ApiOriginPath` to a different value. This is particularly useful when using custom stage names in API Gateway or when you want to use a simpler path structure. Leave the parameter empty to maintain backward compatibility with existing deployments.

#### DeployEnvironment

What deploy/testing environment will this run under? An environment can contain multiple stages (for example 'test' and 't98' would be in 'TEST' environment, and 'beta' and 'prod' stages would deploy to 'PROD'). Utilize this environment variable to determine your tests, app logging levels, TTLs and conditionals in the template. For example, PROD will use longer TTLs and caches while DEV and TEST will use shorter.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | PROD |
| Allowed Values | DEV, TEST, PROD |
| Constraint Description | Must specify DEV, TEST, or PROD. |

#### CloudFrontPriceClass

Price class for CloudFront distribution. For more information, see https://aws.amazon.com/cloudfront/pricing/. PROD deployments will use this value. DEV and TEST deployments will ignore this value and use PriceClass_100. Set this value based on what you want during PROD deployments.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | PriceClass_100 |
| Allowed Values | PriceClass_All, PriceClass_100, PriceClass_200 |
| Constraint Description | Must specify a valid CloudFront price class. |

**Cost Consideration:** PriceClass_100 uses only North America and Europe edge locations (lowest cost). PriceClass_200 adds Asia, Middle East, and Africa. PriceClass_All includes all global edge locations (highest cost).

#### CloudFrontStaticCachePolicy

Cache policy for static S3 origin. Choose between AWS managed policies optimized for different use cases, the template's custom default policy, or provide your own custom policy ARN. AWS managed policies are maintained by AWS and don't require creating custom resources. Note: DEV and TEST environments always use CachingDisabled regardless of this setting to ensure fresh content during development and testing.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | CachingOptimized |
| Allowed Values | CachingOptimized, CachingDisabled, CachingOptimizedForUncompressedObjects, Elemental-MediaPackage, CustomDefault, CustomArn |

**Allowed Values:**
- **CachingOptimized**: Recommended for most use cases. Caches based on query strings and headers.
- **CachingDisabled**: Disables caching. Recommended for dynamic content and APIs.
- **CachingOptimizedForUncompressedObjects**: Optimized for uncompressed content. Disables compression.
- **Elemental-MediaPackage**: Optimized for AWS Elemental MediaPackage origins.
- **CustomDefault**: Use the template's default custom cache policy.
- **CustomArn**: Use a custom cache policy ARN (requires CloudFrontStaticCustomCachePolicyArn parameter).

> **Environment Override:** DEV and TEST environments automatically use CachingDisabled regardless of this parameter value. This ensures developers always see fresh content without manual cache invalidation. Only PROD environments use the selected cache policy.

#### CloudFrontStaticCustomCachePolicyArn

Custom cache policy ARN for static origin. Only used when CloudFrontStaticCachePolicy is set to CustomArn. Leave empty if not using a custom ARN. The ARN must reference an existing CloudFront cache policy in your AWS account.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$\|^$` |
| Constraint Description | Must be a valid CloudFront cache policy ARN or empty. |

**Example ARN:** `arn:aws:cloudfront::123456789012:cache-policy/abc123-def456-789`

#### CloudFrontApiCachePolicy

Cache policy for API Gateway origin. Choose between AWS managed policies optimized for different use cases, the template's custom default policy, or provide your own custom policy ARN. For APIs, CachingDisabled is typically recommended to ensure fresh responses. Note: DEV and TEST environments always use CachingDisabled regardless of this setting.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | CachingDisabled |
| Allowed Values | CachingOptimized, CachingDisabled, CachingOptimizedForUncompressedObjects, Elemental-MediaPackage, CustomDefault, CustomArn |

**Allowed Values:**
- **CachingOptimized**: Recommended for most use cases. Caches based on query strings and headers.
- **CachingDisabled**: Disables caching. Recommended for dynamic content and APIs (default).
- **CachingOptimizedForUncompressedObjects**: Optimized for uncompressed content. Disables compression.
- **Elemental-MediaPackage**: Optimized for AWS Elemental MediaPackage origins.
- **CustomDefault**: Use the template's default custom cache policy.
- **CustomArn**: Use a custom cache policy ARN (requires CloudFrontApiCustomCachePolicyArn parameter).

> **Environment Override:** DEV and TEST environments automatically use CachingDisabled regardless of this parameter value. This ensures developers always see fresh API responses without manual cache invalidation. Only PROD environments use the selected cache policy.

#### CloudFrontApiCustomCachePolicyArn

Custom cache policy ARN for API origin. Only used when CloudFrontApiCachePolicy is set to CustomArn. Leave empty if not using a custom ARN. The ARN must reference an existing CloudFront cache policy in your AWS account.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$\|^$` |
| Constraint Description | Must be a valid CloudFront cache policy ARN or empty. |

**Example ARN:** `arn:aws:cloudfront::123456789012:cache-policy/xyz789-abc123-456`

#### CloudFrontStaticFunctionViewerRequest

CloudFront Function ARN for viewer-request event on static behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

**Example ARN:** `arn:aws:cloudfront::123456789012:function/my-viewer-request-function`

#### CloudFrontStaticFunctionViewerResponse

CloudFront Function ARN for viewer-response event on static behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

#### CloudFrontStaticFunctionOriginRequest

CloudFront Function ARN for origin-request event on static behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

#### CloudFrontStaticFunctionOriginResponse

CloudFront Function ARN for origin-response event on static behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

#### CloudFrontApiFunctionViewerRequest

CloudFront Function ARN for viewer-request event on API behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

**Example ARN:** `arn:aws:cloudfront::123456789012:function/my-api-auth-function`

#### CloudFrontApiFunctionViewerResponse

CloudFront Function ARN for viewer-response event on API behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

#### CloudFrontApiFunctionOriginRequest

CloudFront Function ARN for origin-request event on API behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

#### CloudFrontApiFunctionOriginResponse

CloudFront Function ARN for origin-response event on API behaviors. Leave empty to not associate a function.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$\|^$` |
| Constraint Description | Must be a valid CloudFront Function ARN (arn:aws:cloudfront::\<account-id\>:function/\<function-name\>) or empty. |

> **Note:** CloudFront Functions are lightweight JavaScript functions that run at CloudFront edge locations. They are created as separate resources outside this template. Use these parameters to associate existing functions with cache behaviors for tasks such as URL rewriting, header manipulation, and request/response transformations. This does not cover Lambda@Edge associations.

#### S3LogBucketName

The name of the S3 bucket used for CloudFront logging. Leave empty to disable logging. Must be a valid S3 bucket name (without .s3.amazonaws.com suffix).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Constraint Description | Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number. |

> **Important:** The S3 log bucket must exist before deploying this template and must have a bucket policy that allows CloudFront to write logs. The bucket should be in a region that supports CloudFront logging. For more information, see [AWS CloudFront Logging Documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html).

> **Cost Consideration:** Enabling CloudFront logging incurs S3 storage costs for the log files. Consider implementing lifecycle policies on the log bucket to manage costs.

#### DomainForCloudFront

The DNS name of an existing Amazon Route 53 hosted zone with corresponding * certificate in ACM. Required if you are using an S3 origin for static content. If you are only deploying a custom domain for API Gateway, then leave this and the rest of the fields in this section blank. Example: example.com

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^(?!-)[a-zA-Z0-9-\.]{1,63}(?<!-)$\|^$` |
| Constraint Description | must be a valid DNS zone name. |

#### CustomSubdomainCloudFront

The sub-domain to be placed before the DomainForCloudFront. If CustomSubdomainCloudFront is 'hello' and the DomainForCloudFront is 'example.com' then 'hello.example.com' would be the resulting domain (Also, if stage is not prod, then the stage will be appended eg: hello-test.example.com). Leave blank if you are not deploying a CloudFront distribution.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^(?!-)[a-zA-Z0-9-\.]{1,63}(?<!-)$\|^$` |
| Constraint Description | Must be a valid sub-domain that is covered by the ACM Certificate. |

#### PathStatic

If you are placing BOTH an S3 Origin with static content AND an API Gateway behind the distribution then you will need to specify either a path for static OR the api. For example.com/static use 'static'. Leave blank to serve from root. Only one path level is accepted.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^(?!-)[a-zA-Z0-9\-]{0,63}(?<!-)$` |
| Constraint Description | May only contain alphanumeric characters and dashes. |

#### AcmCertificateArnForCloudFront

The Amazon Resource Name (ARN) of an AWS Certificate Manager (ACM) certificate. Since this is for a CloudFront distribution, this certificate MUST be in us-east-1.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:acm:us-east-1:.*$\|^$` |
| Constraint Description | Must be a valid ACM certificate ARN in us-east-1. |

**Security Note:** CloudFront requires certificates to be in the us-east-1 region regardless of where your other resources are deployed.

#### DomainForApiGateway

The DNS name of an existing Amazon Route 53 hosted zone with corresponding * certificate in ACM. If you plan on placing your API Gateway behind CloudFront, leave this blank as DomainForCloudFront will be used instead. DomainForApiGateway is used for a stand-alone API Gateway. If you are not deploying an API Gateway, then leave this and the rest of the fields in this section blank. Example: example-apis.com

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^(?!-)[a-z0-9-\.]{3,196}(?<!-)$\|^$` |
| Constraint Description | must be a valid DNS zone name. |

#### CustomSubdomainApiGateway

The sub-domain to be placed before the DomainForApiGateway. If you are deploying an API Gateway behind CloudFront, then leave this blank. If CustomSubdomainApiGateway is 'hello' and the DomainForApiGateway is 'example-apis.com' then 'hello.example-apis.com' would be the resulting domain (Also, if not prod, stage will be appended eg: hello-test.example-apis.com)

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^(?!-)[a-zA-Z0-9-\.]{1,62}(?<!-)$\|^$` |
| Constraint Description | Must be a valid sub-domain that is covered by the ACM Certificate. |

#### PathApi

You need either PathApi or PathStatic if they share a CloudFront distribution. Leave blank to serve your API from the root of the domain.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^(?!-)[a-zA-Z0-9\-]{0,63}(?<!-)$` |
| Constraint Description | May only contain alphanumeric characters and dashes. |

#### AcmCertificateArnForApiGateway

The Amazon Resource Name (ARN) of an AWS Certificate Manager (ACM) certificate. This certificate MUST be in the same region as the API Gateway resource. If you are placing your API Gateway behind CloudFront, leave this blank.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:acm:.*$\|^$` |
| Constraint Description | Must be a valid ACM certificate ARN in the same region as the API Gateway resource. |

#### HeadersToForwardToApi

If you are placing an API Gateway behind CloudFront, you will need to specify the headers that you want to forward to the API. For example, if you want to forward the X-Forwarded-For header, then specify 'X-Forwarded-For' in this list. Leave blank if you are not placing API Gateway behind a CloudFront Distribution or you are not forwarding any headers to the API.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | Accept,Origin,Referer,User-Agent,Authorization |

## Resources

- [CloudFrontDistribution](#cloudfrontdistribution) - AWS::CloudFront::Distribution (Conditional: CreateDistribution)
- [CloudFrontOriginAccessControl](#cloudfrontoriginaccesscontrol) - AWS::CloudFront::OriginAccessControl (Conditional: HasStaticOrigin)
- [CloudFrontCachePolicyStatic](#cloudfrontcachepolicystatic) - AWS::CloudFront::CachePolicy (Conditional: CreateCustomStaticCachePolicy)
- [CloudFrontCachePolicyApi](#cloudfrontcachepolicyapi) - AWS::CloudFront::CachePolicy (Conditional: CreateCustomApiCachePolicy)
- [Route53RecordForCloudFront](#route53recordforcloudfront) - AWS::Route53::RecordSetGroup (Conditional: CreateDnsRecordForCloudFront)
- [ApiGatewayV2DomainName](#apigatewayv2domainname) - AWS::ApiGatewayV2::DomainName (Conditional: CreateDnsRecordForApiGateway)
- [ApiGatewayV2ApiMapping](#apigatewayv2apimapping) - AWS::ApiGatewayV2::ApiMapping (Conditional: CreateDnsRecordForApiGateway)
- [Route53RecordForApi](#route53recordforapi) - AWS::Route53::RecordSetGroup (Conditional: CreateDnsRecordForApiGateway)

### CloudFrontDistribution

Type: AWS::CloudFront::Distribution  
Condition: CreateDistribution

Creates a CloudFront distribution that serves content from S3 and/or API Gateway origins. The distribution is configured with HTTPS redirection, IPv6 support, and HTTP/2. It includes custom error responses for single-page applications (403/404 redirect to index.html) when serving static content. Optional logging can be enabled by providing an S3 log bucket name.

**Cache Policy Selection:**

The distribution uses flexible cache policy configuration that supports AWS managed policies, custom default policies, or custom ARN-based policies. Cache policies are selected based on the `CloudFrontStaticCachePolicy` and `CloudFrontApiCachePolicy` parameters:

- **AWS Managed Policies**: Use AWS-maintained policies (CachingOptimized, CachingDisabled, etc.) without creating custom resources
- **CustomDefault**: Use the template's custom cache policy resources (created conditionally)
- **CustomArn**: Reference an existing cache policy in your AWS account

Environment-based override ensures DEV and TEST environments always use CachingDisabled regardless of parameter settings, providing fresh content during development and testing.

For more information about AWS managed cache policies, see [AWS Managed Cache Policies](#aws-managed-cache-policies).

**Key Properties:**
- Supports both S3 (with OAC) and API Gateway origins
- Configurable price class based on deployment environment
- Path-based routing for multiple origins
- Compression enabled for all content
- Environment-specific cache behaviors (longer TTLs in PROD, CachingDisabled in DEV/TEST)
- Custom domain support with ACM certificates
- Optional access logging to S3 bucket with organized prefix structure
- Flexible cache policy selection (managed, custom default, or custom ARN)

**Cost Consideration:** CloudFront distributions incur costs based on data transfer and requests. Price class affects the number of edge locations used.

**Dependencies:** Requires CloudFrontOriginAccessControl (for S3), and optionally CloudFrontCachePolicyStatic and/or CloudFrontCachePolicyApi (when using CustomDefault)

### CloudFrontOriginAccessControl

Type: AWS::CloudFront::OriginAccessControl  
Condition: HasStaticOrigin

Creates an Origin Access Control (OAC) for secure access to the S3 bucket. OAC is the modern replacement for Origin Access Identity (OAI) and provides better security through AWS Signature Version 4 (SigV4) signing.

**Key Properties:**
- Uses SigV4 signing protocol
- Signing behavior set to "always"
- Specifically configured for S3 origin type

**Security Note:** The S3 bucket policy must grant access to this OAC for CloudFront to retrieve objects.

### CloudFrontCachePolicyStatic

Type: AWS::CloudFront::CachePolicy  
Condition: CreateCustomStaticCachePolicy

Defines caching behavior for static content served from S3. This resource is only created when `CloudFrontStaticCachePolicy` is set to `CustomDefault` and the deployment environment is PROD. Uses environment-specific TTL values to balance performance and freshness.

**Conditional Creation:**

This resource is created only when:
- `CloudFrontStaticCachePolicy` parameter is set to `CustomDefault`
- `DeployEnvironment` is `PROD`
- Static origin is configured (`S3OriginDomainName` is provided)

When using AWS managed policies or custom ARNs, this resource is not created, reducing stack complexity and deployment time.

**Key Properties:**
- PROD: DefaultTTL 86400s (24h), MaxTTL 31536000s (1 year)
- No cookies, query strings, or headers included in cache key
- Optimized for static content that doesn't change frequently

**Operational Note:** When using CustomDefault in PROD, this policy provides longer TTLs for better performance. In DEV/TEST environments, the distribution uses CachingDisabled managed policy instead, so this resource is not created.

### CloudFrontCachePolicyApi

Type: AWS::CloudFront::CachePolicy  
Condition: CreateCustomApiCachePolicy

Defines caching behavior for API Gateway origins. This resource is only created when `CloudFrontApiCachePolicy` is set to `CustomDefault` and the deployment environment is PROD. Configured with short TTLs and includes all cookies, query strings, and specified headers in the cache key.

**Conditional Creation:**

This resource is created only when:
- `CloudFrontApiCachePolicy` parameter is set to `CustomDefault`
- `DeployEnvironment` is `PROD`

When using AWS managed policies (like CachingDisabled, which is the default) or custom ARNs, this resource is not created, reducing stack complexity and deployment time.

**Key Properties:**
- DefaultTTL: 10s, MaxTTL: 30s
- Includes all cookies and query strings in cache key
- Forwards specified headers to origin (configurable via HeadersToForwardToApi)
- Suitable for dynamic API responses

**Operational Note:** Short TTLs prevent stale API responses while still providing some caching benefit for repeated requests. In DEV/TEST environments, the distribution uses CachingDisabled managed policy instead, so this resource is not created.

### Route53RecordForCloudFront

Type: AWS::Route53::RecordSetGroup  
Condition: CreateDnsRecordForCloudFront

Creates an A record alias in Route53 pointing to the CloudFront distribution. Automatically appends stage ID to subdomain for non-production stages.

**Key Properties:**
- Uses weighted routing with weight 1
- Alias target points to CloudFront distribution
- Hosted zone ID Z2FDTNDATAQYW2 (CloudFront's global hosted zone)

**Operational Note:** DNS changes can take several minutes to propagate globally.

### ApiGatewayV2DomainName

Type: AWS::ApiGatewayV2::DomainName  
Condition: CreateDnsRecordForApiGateway

Creates a custom domain name for API Gateway (standalone, not behind CloudFront). Uses a regional endpoint with the provided ACM certificate.

**Key Properties:**
- Regional endpoint type
- Automatically appends stage ID for non-production stages
- Uses regional ACM certificate

**Security Note:** The ACM certificate must be in the same region as the API Gateway.

### ApiGatewayV2ApiMapping

Type: AWS::ApiGatewayV2::ApiMapping  
Condition: CreateDnsRecordForApiGateway

Maps the API Gateway stage to the custom domain name. Optionally includes a base path if PathApi is specified.

**Key Properties:**
- Maps to the stage named `{ProjectId}-{StageId}`
- Supports optional base path mapping

**Dependencies:** Requires ApiGatewayV2DomainName and existing API Gateway

### Route53RecordForApi

Type: AWS::Route53::RecordSetGroup  
Condition: CreateDnsRecordForApiGateway

Creates an A record alias in Route53 pointing to the API Gateway regional domain name.

**Key Properties:**
- Uses weighted routing with weight 1
- Alias target points to API Gateway regional domain
- Uses API Gateway's regional hosted zone ID

## Outputs

### CloudFrontDomain

Condition: CreateDistribution

Domain for CloudFront distribution.

**Example Value:** `d1234567890abc.cloudfront.net`

**Usage:** Use this domain to access your content before custom domain DNS is configured, or for testing purposes.

### CloudFrontDistributionId

Condition: CreateDistribution

ID of CloudFront distribution for static website.

**Example Value:** `E1234567890ABC`

**Usage:** Required for creating CloudFront cache invalidations and for referencing in deployment scripts.

### ApiGatewayOrigin

Condition: HasApiGatewayOrigin

API Gateway Origin with path.

**Example Value:** `abc123xyz.execute-api.us-east-1.amazonaws.com/myapp-prod` or `abc123xyz.execute-api.us-east-1.amazonaws.com/api` or `abc123xyz.execute-api.us-east-1.amazonaws.com`

**Usage:** Shows the full API Gateway origin path used by CloudFront or for direct access. The path varies based on the `ApiOriginPath` parameter:
- If `ApiOriginPath` is empty (default): Uses `/${ProjectId}-${StageId}`
- If `ApiOriginPath` is `/`: Uses root path (no prefix)
- If `ApiOriginPath` is custom: Uses the exact custom path provided

### S3Origin

Condition: HasStaticOrigin

S3 Origin with path.

**Example Value:** `my-bucket.s3.us-east-1.amazonaws.com/prod/public` or `my-bucket.s3.us-east-1.amazonaws.com/static` or `my-bucket.s3.us-east-1.amazonaws.com`

**Usage:** Shows the S3 origin path used by CloudFront. The path varies based on the `StaticOriginPath` parameter:
- If `StaticOriginPath` is empty (default): Uses `/${StageId}/public`
- If `StaticOriginPath` is `/`: Uses root path (no prefix)
- If `StaticOriginPath` is custom: Uses the exact custom path provided

### ApiGatewayDomainName

Condition: CreateDnsRecordForApiGateway

Domain name of API Gateway.

**Example Value:** `api.example.com` or `api-test.example.com`

**Usage:** The custom domain name configured for the API Gateway.

### ApiGatewayDomainNameRegional

Condition: CreateDnsRecordForApiGateway

Regional URL of API Gateway domain name.

**Example Value:** `d-abc123xyz.execute-api.us-east-1.amazonaws.com`

**Usage:** The regional endpoint for the API Gateway custom domain, used in Route53 alias records.

### CustomURLForStatic

Condition: HasStaticOrigin

Custom domain and path for static content.

**Example Value:** `app.example.com` or `app.example.com/static` or `app-test.example.com`

**Usage:** The complete URL where static content is accessible. Use this in your application configuration and documentation.

### CustomURLForApi

Condition: HasApiGatewayOrigin

Custom domain and path for API.

**Example Value:** `api.example.com` or `app.example.com/api` or `api-test.example.com`

**Usage:** The complete URL where the API is accessible. Use this as the base URL for API clients.

### CloudFrontLogBucket

Condition: HasLogBucket

The S3 bucket name used for CloudFront logging.

**Example Value:** `my-cloudfront-logs`

**Usage:** Reference to the S3 bucket where CloudFront access logs are stored. Use this to locate and analyze access logs.

### CloudFrontLogPrefix

Condition: HasLogBucket

The complete prefix used for CloudFront log files in the S3 bucket.

**Example Value:** `cloudfront/myorg-webapp-prod`

**Usage:** The prefix path where CloudFront logs are organized within the S3 bucket. Logs are organized by service type (cloudfront), application ownership (Prefix-ProjectId), and deployment stage (StageId) for easy filtering and analysis.

## Conditions

The template uses several conditions to control resource creation:

- **IsProduction**: True when DeployEnvironment is PROD
- **IsProdStage**: True when StageId is "prod"
- **HasStaticOrigin**: True when S3OriginDomainName is provided
- **HasApiGatewayOrigin**: True when ApiGatewayId is provided
- **HasRouteForStaticOrigin**: True when PathStatic is provided
- **HasRouteForApi**: True when PathApi is provided
- **StaticOriginIsRoot**: True when static content is served from root path
- **ApiIsBehindCloudFront**: True when API is behind CloudFront (DomainForApiGateway is empty)
- **HasRouteForApiInCloudFront**: True when API has a path and is behind CloudFront
- **CreateDistribution**: True when either static origin or API behind CloudFront is configured
- **CreateDnsRecordForCloudFront**: True when all CloudFront domain parameters are provided
- **CreateDnsRecordForApiGateway**: True when all API Gateway domain parameters are provided
- **HasHeadersToForwardToApi**: True when headers list is not empty
- **HasLogBucket**: True when S3LogBucketName is provided (non-empty)
- **CreateCustomStaticCachePolicy**: True when static origin exists, environment is PROD, and CloudFrontStaticCachePolicy is CustomDefault
- **CreateCustomApiCachePolicy**: True when environment is PROD and CloudFrontApiCachePolicy is CustomDefault
- **HasStaticFunctionViewerRequest**: True when CloudFrontStaticFunctionViewerRequest is provided (non-empty)
- **HasStaticFunctionViewerResponse**: True when CloudFrontStaticFunctionViewerResponse is provided (non-empty)
- **HasStaticFunctionOriginRequest**: True when CloudFrontStaticFunctionOriginRequest is provided (non-empty)
- **HasStaticFunctionOriginResponse**: True when CloudFrontStaticFunctionOriginResponse is provided (non-empty)
- **HasApiFunctionViewerRequest**: True when CloudFrontApiFunctionViewerRequest is provided (non-empty)
- **HasApiFunctionViewerResponse**: True when CloudFrontApiFunctionViewerResponse is provided (non-empty)
- **HasApiFunctionOriginRequest**: True when CloudFrontApiFunctionOriginRequest is provided (non-empty)
- **HasApiFunctionOriginResponse**: True when CloudFrontApiFunctionOriginResponse is provided (non-empty)

## AWS Managed Cache Policies

AWS provides managed cache policies that are optimized for common use cases. These policies are maintained by AWS and don't require creating custom CloudFormation resources, simplifying your stack and reducing deployment time.

### Benefits of AWS Managed Policies

- **No Custom Resources**: Managed policies don't create CloudFormation resources, reducing stack complexity
- **AWS Maintained**: Policies are updated and optimized by AWS
- **Industry Standard**: Based on best practices for common use cases
- **Faster Deployment**: No need to wait for custom policy resource creation
- **Reduced Costs**: Fewer resources to manage and maintain

### Available Managed Policies

#### CachingOptimized

**Policy ID:** `658327ea-f89d-4fab-a63d-7e88639e58f6`

Recommended for most static content use cases. This policy caches content based on query strings and headers, providing a good balance between cache hit ratio and content freshness.

**Best For:**
- Static websites
- Image and asset delivery
- Content that changes infrequently

**Cache Key Includes:**
- Query strings (all)
- Headers (selected common headers)
- Compression support enabled

#### CachingDisabled

**Policy ID:** `4135ea2d-6df8-44a3-9df3-4b5a84be39ad`

Disables caching entirely. Every request is forwarded to the origin. Recommended for dynamic content and APIs where freshness is critical.

**Best For:**
- API Gateway endpoints
- Dynamic content that changes frequently
- Development and testing environments (automatically used in DEV/TEST)
- Content that must always be fresh

**Cache Key Includes:**
- No caching (all requests forwarded to origin)

#### CachingOptimizedForUncompressedObjects

**Policy ID:** `b2884449-e4de-46a7-ac36-70bc7f1ddd6d`

Optimized for content that should not be compressed. Disables automatic compression while still providing caching benefits.

**Best For:**
- Pre-compressed content (gzip, brotli)
- Binary files that don't benefit from compression
- Content where compression overhead outweighs benefits

**Cache Key Includes:**
- Query strings (all)
- Headers (selected common headers)
- Compression disabled

#### Elemental-MediaPackage

**Policy ID:** `08627262-05a9-4f76-9ded-b50ca2e3a84f`

Specifically optimized for AWS Elemental MediaPackage origins. Includes headers and query strings required for media streaming.

**Best For:**
- AWS Elemental MediaPackage origins
- Live and on-demand video streaming
- Media delivery workflows

**Cache Key Includes:**
- MediaPackage-specific headers
- Query strings for media segments
- Optimized TTLs for streaming content

### Choosing the Right Policy

| Use Case | Recommended Policy | Reason |
|----------|-------------------|--------|
| Static website | CachingOptimized | Good cache hit ratio, supports compression |
| API Gateway | CachingDisabled | Always fresh responses, no stale data |
| Pre-compressed assets | CachingOptimizedForUncompressedObjects | Avoids double compression |
| Video streaming | Elemental-MediaPackage | Optimized for media delivery |
| Development/Testing | CachingDisabled | Automatic in DEV/TEST environments |
| Custom requirements | CustomDefault or CustomArn | Full control over cache behavior |

### When to Use Custom Policies

Consider using `CustomDefault` or `CustomArn` when:
- You need specific TTL values not provided by managed policies
- You require custom header/cookie/query string handling
- You have compliance requirements for cache behavior
- You need to match existing custom policy configurations

For more information about AWS managed cache policies, see the [AWS CloudFront Documentation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html).

## Examples

### Example 1: Static Website Only

```yaml
Parameters:
  Prefix: myorg
  ProjectId: marketing-site
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-marketing-site-prod-static.s3.us-east-1.amazonaws.com
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: www
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontPriceClass: PriceClass_100
```

Result: Static website accessible at `www.example.com`

### Example 2: API Gateway Behind CloudFront

```yaml
Parameters:
  Prefix: myorg
  ProjectId: api-service
  StageId: prod
  DeployEnvironment: PROD
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  HeadersToForwardToApi: Authorization,Content-Type,X-Api-Key
```

Result: API accessible at `api.example.com`

### Example 3: Combined Static and API with Path Routing

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-webapp-prod-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  HeadersToForwardToApi: Authorization,Content-Type
```

Result: 
- Static content at `app.example.com`
- API at `app.example.com/api`

### Example 4: Custom Origin Paths for S3 and API

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-webapp-prod-static.s3.us-east-1.amazonaws.com
  StaticOriginPath: /v2/assets
  ApiGatewayId: abc123xyz
  ApiOriginPath: /production
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  HeadersToForwardToApi: Authorization,Content-Type
```

Result: 
- Static content at `app.example.com` served from S3 path `/v2/assets`
- API at `app.example.com/api` using API Gateway stage path `/production`

> **Use Case:** This configuration is useful when you have a custom S3 bucket structure (e.g., versioned assets in `/v2/assets`) or when your API Gateway uses a custom stage name that doesn't match the default `${ProjectId}-${StageId}` pattern.

### Example 5: Standalone API Gateway (No CloudFront)

```yaml
Parameters:
  Prefix: myorg
  ProjectId: internal-api
  StageId: prod
  DeployEnvironment: PROD
  ApiGatewayId: abc123xyz
  DomainForApiGateway: apis.example.com
  CustomSubdomainApiGateway: internal
  AcmCertificateArnForApiGateway: arn:aws:acm:us-east-1:123456789012:certificate/def-456
```

Result: API accessible at `internal.apis.example.com`

### Example 6: Static Website with CloudFront Logging Enabled

```yaml
Parameters:
  Prefix: myorg
  ProjectId: marketing-site
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-marketing-site-prod-static.s3.us-east-1.amazonaws.com
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: www
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontPriceClass: PriceClass_100
  S3LogBucketName: myorg-cloudfront-logs
```

Result: 
- Static website accessible at `www.example.com`
- CloudFront access logs stored in `myorg-cloudfront-logs` bucket with prefix `cloudfront/myorg-marketing-site-prod`

### Example 7: Combined Static and API with Logging Disabled

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: test
  DeployEnvironment: TEST
  S3OriginDomainName: myorg-webapp-test-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  HeadersToForwardToApi: Authorization,Content-Type
  S3LogBucketName: ""
```

Result: 
- Static content at `app-test.example.com`
- API at `app-test.example.com/api`
- No CloudFront logging (S3LogBucketName is empty)

### Example 8: Using AWS Managed Cache Policies

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-webapp-prod-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontStaticCachePolicy: CachingOptimized
  CloudFrontApiCachePolicy: CachingDisabled
  HeadersToForwardToApi: Authorization,Content-Type
```

Result:
- Static content at `app.example.com` using AWS managed CachingOptimized policy
- API at `app.example.com/api` using AWS managed CachingDisabled policy
- No custom cache policy resources created (faster deployment)

### Example 9: Using Custom Default Cache Policies

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-webapp-prod-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontStaticCachePolicy: CustomDefault
  CloudFrontApiCachePolicy: CustomDefault
  HeadersToForwardToApi: Authorization,Content-Type
```

Result:
- Static content at `app.example.com` using template's custom cache policy (24h TTL)
- API at `app.example.com/api` using template's custom cache policy (10s TTL)
- Custom cache policy resources created in CloudFormation stack

### Example 10: Using Custom ARN Cache Policies

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-webapp-prod-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontStaticCachePolicy: CustomArn
  CloudFrontStaticCustomCachePolicyArn: arn:aws:cloudfront::123456789012:cache-policy/my-static-policy
  CloudFrontApiCachePolicy: CustomArn
  CloudFrontApiCustomCachePolicyArn: arn:aws:cloudfront::123456789012:cache-policy/my-api-policy
  HeadersToForwardToApi: Authorization,Content-Type
```

Result:
- Static content at `app.example.com` using existing custom cache policy from ARN
- API at `app.example.com/api` using existing custom cache policy from ARN
- No custom cache policy resources created (references existing policies)

### Example 11: Mixed Cache Policy Types

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: prod
  DeployEnvironment: PROD
  S3OriginDomainName: myorg-webapp-prod-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontStaticCachePolicy: CachingOptimized
  CloudFrontApiCachePolicy: CustomArn
  CloudFrontApiCustomCachePolicyArn: arn:aws:cloudfront::123456789012:cache-policy/my-api-policy
  HeadersToForwardToApi: Authorization,Content-Type
```

Result:
- Static content at `app.example.com` using AWS managed CachingOptimized policy
- API at `app.example.com/api` using existing custom cache policy from ARN
- Only one custom cache policy resource created (for static origin)

### Example 12: Environment-Based Cache Policy Override

```yaml
Parameters:
  Prefix: myorg
  ProjectId: webapp
  StageId: test
  DeployEnvironment: TEST
  S3OriginDomainName: myorg-webapp-test-static.s3.us-east-1.amazonaws.com
  ApiGatewayId: abc123xyz
  DomainForCloudFront: example.com
  CustomSubdomainCloudFront: app
  PathApi: api
  AcmCertificateArnForCloudFront: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
  CloudFrontStaticCachePolicy: CachingOptimized
  CloudFrontApiCachePolicy: CustomDefault
  HeadersToForwardToApi: Authorization,Content-Type
```

Result:
- Static content at `app-test.example.com` using CachingDisabled (overridden from CachingOptimized)
- API at `app-test.example.com/api` using CachingDisabled (overridden from CustomDefault)
- No custom cache policy resources created (TEST environment uses managed CachingDisabled)
- Ensures fresh content during testing regardless of parameter settings

## Troubleshooting

### CloudFront Distribution Takes Long Time to Deploy

CloudFront distributions typically take 15-20 minutes to deploy or update. This is normal AWS behavior as the configuration propagates to all edge locations.

### Certificate Validation Errors

- For CloudFront: Ensure the ACM certificate is in us-east-1 region
- For API Gateway: Ensure the ACM certificate is in the same region as the API Gateway
- Verify the certificate covers the subdomain (wildcard certificates work best)

### 403 Forbidden Errors from S3

Check that the S3 bucket policy grants access to the CloudFront Origin Access Control. The storage template should have configured this automatically.

### Custom Domain Not Resolving

- Verify the Route53 hosted zone exists and matches the domain parameter
- Check that DNS propagation has completed (can take up to 48 hours globally)
- Verify the ACM certificate is validated and issued

### Stage Name Appended Unexpectedly

Non-production stages (StageId != "prod") automatically append the stage ID to subdomain names. This is by design to prevent conflicts between environments.

### Cache Policy Issues

**Custom ARN Not Found:**
- Verify the cache policy ARN exists in your AWS account
- Ensure the ARN format is correct: `arn:aws:cloudfront::123456789012:cache-policy/policy-id`
- Check that you have permissions to reference the cache policy

**Unexpected Caching Behavior in DEV/TEST:**
- DEV and TEST environments automatically use CachingDisabled regardless of parameter settings
- This is by design to ensure fresh content during development and testing
- To test specific cache policies, deploy to a PROD environment

**Custom Cache Policy Not Created:**
- Custom cache policies are only created when `CloudFrontStaticCachePolicy` or `CloudFrontApiCachePolicy` is set to `CustomDefault`
- Custom cache policies are not created in DEV/TEST environments (CachingDisabled is used instead)
- Verify the `DeployEnvironment` parameter is set to `PROD` if you expect custom policies to be created

## Related Templates

- **Storage Templates**: Create S3 buckets with proper OAC policies
  - `template-storage-s3-oac-for-cloudfront.yml`
