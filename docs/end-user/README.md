# End-User Documentation

The end user of Atlantis SAM Templates does not interact with the template repository, or S3 bucket directly.

Instead, the end user is the developer or operations member who runs the `config.py` script from their organization's SAM Config repository.

The actual consumer of the templates is the `config.py` and `deploy.py` script used by the Atlantis platform to deploy infrastructure.

The config script queries the S3 bucket that contains the available templates and presents the available templates to the user. The user makes a selection and the `samconfig` is saved with the S3 location of the selected template.

During deployment, the deploy script gets the S3 location of the template from `samconfig` and copies the template to temporary, local storage. It then performs a `sam deploy`.

## Versioning

Templates are versioned in S3 using S3 object versioning. As such, you will notice the S3 location of the template used for a SAM configuration will have `?versionId={{SOME_VERSION_ID}}` appended to the S3 location:

```
s3://63klabs/atlantis/templates/v2/pipeline/template-pipeline-build-only.yml?versionId=yTeC1JZj1rgh96cJC08dO9A3n4m.sT.G
```

When creating a new configuration, the latest version identifier will be selected.

When updating a configuration, the config script checks to see if there is a newer version than the one that is configured. If there is a new version, the user is asked if they want to update to the latest version. The user can decline and the old version will continued to be used for deployments. If the user chooses the new version then the new `versionId` will be used.

If, after updating, the user wants to go back to a previous version they can get the previous `versionId` and update the `samconfig` file. To obtain the previous `versionId` either refer to a previous commit or use the [Atlantis MCP server](https://mcp.atlantis.63klabs.net).

## Sources

> The end-user is responsible to selecting the correct template to use, as there may be multiple options across multiple namespaces and buckets.

An organization may make multiple sources (buckets) and namespaces available to it's operations and developers. 

By default the source is the `atlantis` namespace in the public `63klabs` bucket. (`s3://63klabs/atlantis`)

If additional sources exist and are configured for an organization's internal use, they will be displayed when the end-user runs the `config` script.

## Installing

The end-user does not need to perform any installation. The templates are available automatically from the `config` and `deploy` scripts.

An organization's administrator will need to set up the SAM config repository and repository settings.
