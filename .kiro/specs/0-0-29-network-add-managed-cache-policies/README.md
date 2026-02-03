# Initial Specification Prompt

Add option to attach managed cache policies

[Issue #1](https://github.com/63Klabs/atlantis-cfn-template-repo-for-serverless-deployments/issues/1)

The template-network-route53-cloudfront-s3-apigw.yml template should support attaching AWS managed cache policies to the distribution.

Currently two custom cache policies are created:
- CloudFrontCachePolicyStatic
- CloudFrontCachePolicyApi

Instead of creating the latter two, it should be possible to reference managed policies like:
- AWSManagedCachePolicyCachingOptimized
- AWSManagedCachePolicyCachingDisabled
- AWSManagedCachePolicyCachingOptimizedForUncompressedObjects
- AWSManagedCachePolicyElementalMediaPackage

Documentation for each of these polcies should be added. The Parameter description can give a brief explaination:
- CachingOptimized - For most use cases
- CachingDisabled - When you don't want caching
- CachingOptimizedForUncompressedObjects - For uncompressed content
- Elemental-MediaPackage - For media content

An appropriate section for comments linking to AWS documentation should be provided in the resource section when the template is determinging which policy to apply. This will ensure the comments are included in the template's generated README. 

We will need to use `>!` similar to what steering documents apply to README files to ensure AI applies comments and highlights the appropriate section in the accompanying template documentation readme file and does not delete the comment.

For example: 

```yaml
Resources:
  MyResource:
    Type: AWS::CloudFront::Distribution
    Properties:
      # >! This is an important comment that should also be in the documentation
      SomeSetting: !Ref SomeParameter
```

The existing policies.

```yaml

  CloudFrontCachePolicyStatic:
    Type: AWS::CloudFront::CachePolicy
    Condition: HasStaticOrigin
    Properties:
      CachePolicyConfig:
        Name: !Sub "${Prefix}-${ProjectId}-${StageId}-Static-CachePolicy"
        Comment: S3 Origin
        DefaultTTL: !If [ IsProduction, 86400, 3 ]
        MaxTTL: !If [ IsProduction, 31536000, 10 ]
        MinTTL: 0
        ParametersInCacheKeyAndForwardedToOrigin:
          CookiesConfig:
            CookieBehavior: none
          EnableAcceptEncodingBrotli: false
          EnableAcceptEncodingGzip: false
          QueryStringsConfig:
            QueryStringBehavior: none
          HeadersConfig:
            HeaderBehavior: none

  CloudFrontCachePolicyApi:
    Type: AWS::CloudFront::CachePolicy
    # Condition: ApiIsBehindCloudFront
    Properties:
      CachePolicyConfig:
        Name: !Sub "${Prefix}-${ProjectId}-${StageId}-Api-CachePolicy"
        Comment: Api Origin
        DefaultTTL: 10
        MaxTTL: 30
        MinTTL: 0
        ParametersInCacheKeyAndForwardedToOrigin:
          CookiesConfig:
            CookieBehavior: all
          EnableAcceptEncodingBrotli: false
          EnableAcceptEncodingGzip: false
          QueryStringsConfig:
            QueryStringBehavior: all
          HeadersConfig: !If 
            - HasHeadersToForwardToApi
            - HeaderBehavior: whitelist
              Headers: !Ref HeadersToForwardToApi
            - HeaderBehavior: none

```

We will need to add template parameters to configure what policy should be used. 

API and Static will need their own parameters.
- CloudFrontStaticCachePolicy
- CloudFrontStaticCustomCachePolicyArn
- CloudFrontApiCachePolicy
- CloudFrontApiCustomCachePolicyArn

We would like to use few parameters, but may need a secondary parameter if using a custom policy.

Default for static is AWSManagedCachePolicyCachingOptimized
Default for api is AWSManagedCachePolicyCachingDisabled

The 4 AWS provided options should be available for both static and api origins as enum. 2 additional options are "CustomDefault" and "CustomArn"

If "CustomDefault" is selected, then the existing custom policies should be used.
If "CustomArn" is selected, then a CustomCachePolicyArn parameter should be made available.

Conditionals should be created and used in the template.

Currently the CloudFrontCachePolicyApi has no condition, this should be updated to use the new conditional.

Please ask any clarifying questions.