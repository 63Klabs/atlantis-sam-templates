# Network Templates

Network infrastructure templates for configuring CloudFront distributions, Route53 DNS records, and API Gateway custom domains.

## Overview

Network templates handle the routing and distribution layer of your serverless applications. They connect your storage (S3) and application (API Gateway) resources to custom domains through CloudFront CDN and Route53 DNS management.

## Templates

### [template-network-route53-cloudfront-s3-apigw](./template-network-route53-cloudfront-s3-apigw-README.md)

Serves Static Content (S3) and/or API Gateway via CloudFront with custom domain (Route53).

**Use Cases:**
- Static website hosting with custom domain
- API Gateway with custom domain and optional CloudFront caching
- Combined static and API on same domain with path-based routing
- Multi-stage deployments with environment-specific configurations

**Key Features:**
- CloudFront distribution with Origin Access Control (OAC) for S3
- Flexible routing: separate domains or path-based routing
- Environment-specific cache policies and TTLs
- Automatic stage-based subdomain naming for non-production environments
- Support for both CloudFront-backed and standalone API Gateway domains

**Prerequisites:**
- Existing S3 bucket (for static content)
- Existing API Gateway (for API endpoints)
- Route53 hosted zone
- ACM certificates (us-east-1 for CloudFront, regional for API Gateway)

## Common Use Cases

### Static Website with CDN

Use network templates to serve static content from S3 through CloudFront with a custom domain. This provides:
- Global content delivery with low latency
- HTTPS support with custom certificates
- Automatic compression and HTTP/2
- Protection of S3 bucket from direct public access

### API with Custom Domain

Expose API Gateway endpoints through custom domains, either:
- Behind CloudFront for additional caching and global distribution
- Direct to API Gateway for lower latency and simpler architecture

### Full-Stack Application

Combine static frontend and API backend on the same domain using path-based routing:
- `app.example.com` → Static SPA from S3
- `app.example.com/api` → API Gateway endpoints

### Multi-Environment Deployments

Deploy the same application across multiple environments (dev, test, prod) with automatic subdomain differentiation:
- Production: `app.example.com`
- Test: `app-test.example.com`
- Dev: `app-dev.example.com`

## Architecture Patterns

### Pattern 1: Static-Only Architecture

```
User → Route53 → CloudFront → S3 (OAC)
```

Best for: Static websites, SPAs, documentation sites

### Pattern 2: API-Only Architecture (CloudFront)

```
User → Route53 → CloudFront → API Gateway → Lambda
```

Best for: Public APIs with global audience, APIs needing caching

### Pattern 3: API-Only Architecture (Direct)

```
User → Route53 → API Gateway → Lambda
```

Best for: Internal APIs, APIs requiring lowest latency, WebSocket APIs

### Pattern 4: Combined Architecture

```
User → Route53 → CloudFront → S3 (static at /)
                            → API Gateway (API at /api)
```

Best for: Full-stack applications, SPAs with backend APIs

## Cost Considerations

### CloudFront Costs

- **Data Transfer Out**: Charged per GB transferred to users
- **Requests**: Charged per 10,000 requests (HTTP/HTTPS)
- **Price Classes**: 
  - PriceClass_100: North America & Europe (lowest cost)
  - PriceClass_200: Adds Asia, Middle East, Africa
  - PriceClass_All: All edge locations (highest cost)

### Route53 Costs

- **Hosted Zone**: $0.50/month per hosted zone
- **Queries**: $0.40 per million queries (first billion)
- **Alias Records**: No charge for alias queries to AWS resources

### API Gateway Costs

- **REST API Requests**: $3.50 per million requests
- **Data Transfer**: Standard AWS data transfer rates
- **Custom Domain**: No additional charge

**Cost Optimization Tips:**
- Use PriceClass_100 for non-production environments
- Implement appropriate cache TTLs to reduce origin requests
- Use CloudFront for static content to reduce S3 request costs

## Security Best Practices

1. **Use Origin Access Control (OAC)**: Never make S3 buckets publicly accessible. Use OAC to restrict access to CloudFront only.

2. **HTTPS Only**: Always configure custom domains with ACM certificates and enforce HTTPS.

3. **Certificate Management**: 
   - CloudFront certificates must be in us-east-1
   - API Gateway certificates must be in the same region as the API
   - Use wildcard certificates for flexibility

4. **Header Forwarding**: Only forward necessary headers to API Gateway to maximize cache efficiency.

5. **IAM Permissions**: Use least-privilege service roles for CloudFormation deployments.

## Deployment Notes

### Deployment Time

- **CloudFront Distributions**: 15-20 minutes for initial creation or updates
- **Route53 Records**: 1-2 minutes, plus DNS propagation time
- **API Gateway Domains**: 2-5 minutes

### Update Behavior

- **CloudFront**: Most updates are in-place, but some properties trigger replacement
- **Route53**: Records can be updated in-place
- **API Gateway Domains**: Certificate changes may require replacement

### DNS Propagation

After deployment, DNS changes can take:
- **Within AWS**: Minutes
- **Global Propagation**: Up to 48 hours (typically much faster)

## Integration with Other Templates

Network templates work with:

- **Storage Templates**: Provide S3 buckets with OAC policies
  - `template-storage-s3-oac-for-cloudfront.yml`

- **Application Templates**: Provide API Gateway endpoints
  - Application SAM templates with API Gateway resources

- **Service Role Templates**: Provide IAM roles for deployments
  - `template-service-role-storage.yml`
  - `template-service-role-pipeline.yml`

- **Pipeline Templates**: Automate deployments and updates
  - `template-pipeline-github.yml`

## Troubleshooting

### Common Issues

**CloudFront 403 Errors**
- Check S3 bucket policy allows OAC access
- Verify objects exist in the correct path (`/{StageId}/public/`)

**Certificate Validation Failures**
- Ensure CloudFront certificates are in us-east-1
- Verify certificate covers the subdomain (use wildcard)

**DNS Not Resolving**
- Verify hosted zone exists and matches domain parameter
- Wait for DNS propagation (up to 48 hours)
- Check Route53 records were created correctly

**Stage Name Issues**
- Non-prod stages automatically append stage ID to subdomain
- Use StageId "prod" for production deployments without suffix

## Additional Resources

- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [AWS Route53 Documentation](https://docs.aws.amazon.com/route53/)
- [AWS API Gateway Custom Domains](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html)
- [CloudFront Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
