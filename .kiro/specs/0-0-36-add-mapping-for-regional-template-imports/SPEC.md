# Add Mapping for Regional Template Imports

Currently the templates must be deployed in the same region as the 63klabs bucket (us-east-2).

We need to perform the following updates on any template that uses the import function from modules.

1. The parameter `S3ModuleLocation` should only accept a bucket name. By default it should be blank (to use the mapping).
2. Add a new parameter called `S3ModuleNamespace` and by default should be `atlantis`
3. Add a mapping section for the buckets based on region (see bucket list).
4. Add a conditional for checking if an S3ModuleLocation is specified
5. When filling in the bucket location for the import, use the mapping if no S3ModuleLocation is specified, and append the namespace as a prefix. (example: s3://63klabs-atlas-us-east-1/atlantis/)

## Mapping

us-east-1: 63klabs-atlas-us-east-1
us-east-2: 63klabs-zenith-us-east-2
us-west-1: 63klabs-fabric-us-west-1
us-west-2: 63klabs-orbit-us-west-2

## Update all Templates that Import

All templates that perform an import including but not limited to v2/account and v2/service-role must be updated.

Ask all clarifying and follow up questions in SPEC-QUESTIONS.md before moving on to the spec driven workflow. All questions must be answered by the user in the SPEC-QUESTIONS.md before proceeding.