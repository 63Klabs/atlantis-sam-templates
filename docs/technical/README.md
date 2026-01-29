# Technical Documentation for Maintainers of the Repository

## Overview

This repository contains CloudFormation templates for deploying various stacks such as S3 buckets for static web sites, access logs, CloudFront and Route53 configurations, and deployment pipelines.

It may be used by Platform Engineers to maintain a central repository of templates to be used by developers.

Developers (the end-user) will typically not have direct access to this repository. Instead, they will run scripts provided by a SAM Configuration repository hosted within the organization. The SAM Configuration repository should be created and maintained by the organization's platform engineers. It can be intialized by downloading the files from the [Atlantis SAM Configuration Repo for Serverles Deployments](https://github.com/63Klabs/atlantis-cfn-configuration-repo-for-serverless-deployments)

When the developer runs the `config.py` script from the SAM Configuration repository, they will be able to select a template to use.

## Using the Repository

> By default, the SAM Configuration repository will list available templates from a public S3 bucket maintained by 63Klabs.

When an organization is starting out with the Atlantis Templates and Scripts Platform, it is best to focus on the SAM Config repository first and use the templates provided by the 63klabs public S3 bucket (which is sourced from the [Atlantis CloudFormation Template repository on GitHub](https://github.com/63Klabs/atlantis-cfn-template-repo-for-serverless-deployments)).

If, as an organization, you wish to supply your own templates, you may copy this repository to your own organization git provider and S3 bucket available internally.

The Atlantis SAM Configuration repository allows multiple S3 buckets to serve as template sources when running the `config.py` script. You could keep the default 63klabs bucket and add your own bucket to serve as a source for custom templates.

## Developers can update existing stacks to use updated templates

> By default, the SAM Configuration repository will list available templates from a public S3 bucket maintained by 63Klabs.

Each time a developer runs the config.py script on an existing configuration, the script will check the S3 bucket for any template updates. If one exists it will prompt the user if they want to apply the updated template.

A user can always re-apply a previous version of the template (but they would have to know the S3 version ID which they can grab from another stack's template version id tag or refer to a previous SAM Config repo commit).

Care is taken to not introduce breaking changes and if a breaking change is introduced, the template will move to a new version file with migration options.

## Self-Hosting

> By default, the SAM Configuration repository will list available templates from a public S3 bucket maintained by 63Klabs.

If you choose to self-host these templates you will need to create a copy of this repository for your organizational use, create an S3 bucket (with versioning) to store the templates (that the developers have access to) and connect your copy of this repository to a pipeline that uses the included `buildspec.yml` at the root of this repo to copy the templates to your internal S3 bucket. (If using GitHub actions to deploy from GitHub, `.github/workflows/deploy.yml` is also provided as an example.)

## Updating Templates

If you update a template you must ensure backwards compatibility with existing stacks. Do not rename resources, parameters, or stack exports (variables).

To assist in AI-Assisted Engineering, a steering directory has been added for use by Kiro (or other AI-Assistant). Please review these documents for important information before making changes.
