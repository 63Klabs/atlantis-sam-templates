The following error message appears when attempting to deploy the GitHub Pipeline (`template-pipeline-github.yml`)

```
User: arn:aws:sts::123456789012:assumed-role/XME-CloudFormation-Service-Role-Pipeline-Management/AWSCloudFormation is not authorized to perform: codestar-connections:PassConnection on resource: arn:aws:codeconnections:us-east-2:123456789012:connection/76e6e0e6-8ca1-4197-a4a1-522cc74c5e0a because no identity-based policy allows the codestar-connections:PassConnection action (Service: CodePipeline, Status Code: 400, Request ID: 09708dcd-9e4d-4f11-aea2-969843a278e5)
```

We need to check the Prefix-based Service Role definition for Pipeline Management and ensure this is set.

We need to follow least privilage and lock it down as much as possible with our naming conventions and tagging standards.

Currently the GitHub org and codestar connection is set at the account level in the account-level templates.

We may need to update both the account-level and prefix based templates and child templates to come up with the most robust and efficent solution.

We are still in beta so we don't need an upgrade plan, but we also do not want breaking changes.

You should:

1. Detect the issue
2. Identify a fix
3. Understand how permissions are deployed and interconnected among the templates and processes that rely on these templates.
4. Make a well-thought out update to the templates that is backwards compatible and non-breaking

We are in a planning phase only. I want options and recommendations. Ask any clarifying questions. Place all insight, options, recomendations, and questions in PLAN.md within this spec directory. We need to be very thoughtful on our approach and will iterate over the plan before implementation.
