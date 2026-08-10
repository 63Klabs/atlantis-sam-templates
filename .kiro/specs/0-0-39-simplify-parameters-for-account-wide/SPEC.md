# Simplify Parameters for Account Wide

Use the stack export `${OrgPrefix}-S3-Artifacts-Bucket-Name` from account-wide-infrastructure to determine the `S3ArtifactsBucket` for each of the service roles created by prefix-based-infrastructure.yml if `S3ArtifactsBucket` parameter is not provided while deploying prefix-based-infrastructure.yml. 

We will need a conditional to check if S3ArtifactsBucket was provided as an override, and then update each of the service role modules to use it or fall back to the stack export.

We will need to add a new parameter to prefix-based-infrastructure.yml called OrgPrefix that follows the same parameter definition found in account-wide-infrastructure.

Even though we are adding new functionality to accomodate S3ArtifactBucket, it should be marked as deprecated as we are doing this to remain backwards compatible. Using the export variables is encouraged.

Please review the existing prefix-based-infrastructure and account-wide-infrastructure templates along with the mmodules/managment-roles templates and create a requirements.md document. If there are any clarifying questions, or you have recomendations that I need to choose from, please provide them in QUESTIONS.md in this spec directory prior to generating requirements.md. Once QUESTIONS are answered, we will move to requirements.md. Once approved, then we will move on to design.