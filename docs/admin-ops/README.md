# Documentation for Admins and Operations

This repository requires a CI/CD pipeline to publish templates to an S3 bucket available within your organization.

These templates are used by `config` and `deploy` scripts from your organization's Atlantis SAM Config repository.

It is recommended that as you start setting up your organization for the Atlantis Platform, that you use the `63klabs` public bucket. Then, after your organization has experience, you can manage and host your own templates.

Use the supplied `buildspec.yml` or GitHub workflow to publish your templates to your internal S3 bucket.

Developers and operations will require read access to the S3 bucket.

## Guides

- [Account Management Stack Deployment](./account-management.md) — self-hosting the Atlantis DevOps Platform.
- [Approval-Audit CLI](./approval-audit-cli.md) — copy-paste AWS CLI commands to find Atlantis pipelines with the promotion (`ApproveToPromote`) or release (`ApproveRelease`) approval gate disabled.
