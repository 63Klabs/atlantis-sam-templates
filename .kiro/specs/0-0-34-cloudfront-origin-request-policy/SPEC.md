# template-storage-s3-oac-for-cloudfront.yml uses GetAtt DomainName for S3 domain but it outputs no longer supported S3 domain for CloudFront

[GitHub Issue #3](https://github.com/63Klabs/atlantis-sam-templates/issues/3)

On May 1, 2026, some of our CloudFront distributions that were fronting S3 buckets using OAC stopped working. Instead of getting the static site at the CloudFront distribution domain, the browser would redirect to the S3 bucket domain and path with a 307 and produce an error.

The redirected URL would be in the S3 domain format: <bucketname>.s3.<region>.amazonaws.com/test/public/index.html
or /beta/public, and so on, for various paths for different distributions.

While AWS has announced the preferred S3 domain is this <bucketname>.s3.<region>.amazonaws.com, CloudFormation still outputs the old global domain <bucketname>.s3..amazonaws.com when using the `!GetAtt OriginBucketRegional.DomainName` in a template.

The template-storage-s3-oac-for-cloudfront.yml template uses `!GetAtt DomainName` for the output to be used when configuring the network stack for the S3 origin of a CloudFront distribution.

Since the AWS-provided GetAtt DomainName no longer returns correct results, we should generate our own domain string and avoid using the AWS-provided GetAtt.

So, in the template-storage-s3-oac-for-cloudfront.yml output section, we need to change the use of GetAtt to a statically constructed output of <bucketname>.s3.<region>.amazonaws.com.

**Current**
```yaml
  OriginBucketDomainForCloudFront:
    Description: Domain to use for CloudFront S3 Origin.
    Value: !GetAtt OriginBucketRegional.DomainName
```

**New**
```yaml
  OriginBucketDomainForCloudFront:
    Description: Domain to use for CloudFront S3 Origin.
    Value: !Sub "https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com"
```

Be sure to create a changelog entry. This is not considered a breaking change.
