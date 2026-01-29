# Initial Specification Prompt

Add CloudFront logging

Currently logging for CloudFront distributions is commented out in the template-network-route53-cloudfront-s3-apigw.yml template:

```yaml
        # Logging:
        #   IncludeCookies: 'false'
        #   Bucket: amzn-s3-demo-logging-bucket.s3.amazonaws.com
        #   Prefix: myprefix
```

We need to accept a parameter for the S3 bucket name to be used for CloudFront logging and uncomment the Logging section. The Parameter should only accept a valid bucket name and should not accept .s3.amazonaws.com as we will append that in the template to keep it simple.

The parameter should be optional and checked for validity as a bucket name. Provide a proper description and constraint description.

Conditionals should be used to determine if a parameter is provided, and if so, enable the Logging section.

The prefix should be `cloudfront/prefix-projectId-stageId`

If there are any recommended enhancements for the Logging properties please suggest and ask if they should be included.