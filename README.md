# Atlantis CloudFormation Template Repository for Serverless Deployments using AWS SAM and CloudFormation

> This repository contains a collection of AWS CloudFormation templates designed for serverless deployments using AWS SAM (Simple Application Model). It is based on the Atlantis Template and Scripts Platform for managing Serverless Deployments using AWS SAM and CloudFormation. Templates in this repository are used by the Atlantis SAM Configuration scripts.

> By default, the SAM Configuration repository `config.py` script will list available templates from a public S3 bucket maintained by 63Klabs.

Feel free to browse the documentation and templates in this repository to understand how they are used. They are available for use in the Atlantis SAM Configuration scripts through the public `S3://63klabs` bucket.

> Utilize the default 63klabs bucket as a template source FOR BEGINNING, EXPERIMENTAL, EDUCATIONAL, and TRAINING PURPOSES. It will get you started quicker and does not require advanced knowledge of everything covered in the deployment documentation. Just go build!

If you are an organization looking to use these templates in production, please consider deploying your own copy to your own S3 bucket for security and control. See [Technical Documentation](./docs/technical/README.md).

The S3 bucket `63klabs` is public and read-only. It contains the latest versions of the templates in this repository. The 63klabs bucket receives the templates from the GitHub repository: [Atlantis Template Repository for Serverless Deployments using AWS SAM and CloudFormation](https://github.com/63Klabs/atlantis-cfn-template-repo-for-serverless-deployments)

## CloudFormation Template Validation

This repository includes automated CloudFormation template validation using cfn-lint to ensure template quality and catch syntax errors before deployment.

### Features

- **Automatic Template Discovery**: Recursively scans the `templates/v2` directory for all CloudFormation template files
- **Comprehensive Validation**: Uses cfn-lint to validate templates against AWS best practices and syntax rules
- **Local Development Integration**: Integrates with pytest for local testing alongside existing test suites
- **CI/CD Pipeline Integration**: Automatically validates templates during build process
- **Detailed Error Reporting**: Provides specific error details including file paths and violation descriptions

### Local Development Setup

1. **Set up the virtual environment**:
   ```bash
   python3 scripts/setup_venv.py
   ```

2. **Activate the virtual environment**:
   ```bash
   # Linux/macOS
   source .venv/bin/activate
   
   # Windows
   .venv\Scripts\activate
   ```

3. **Run CloudFormation template validation**:
   ```bash
   # Run all tests including CFN validation
   python -m pytest tests/
   
   # Run only CFN template validation
   python -m pytest tests/test_cfn_templates.py
   
   # Run CFN validation standalone
   python scripts/cfn_lint_runner.py
   ```

### CI/CD Integration

CloudFormation template validation is automatically integrated into the build pipeline via `buildspec.yml`. The validation:

- Runs during the build phase after dependency installation
- Fails the build if any templates have validation errors
- Provides detailed error reports in build logs
- Uses isolated virtual environment for dependency management

### Template Validation Rules

The validation process checks for:

- CloudFormation syntax errors
- AWS resource property validation
- Best practice compliance
- Security and performance recommendations
- Template structure and formatting

### Troubleshooting

**Virtual Environment Issues**:
- Ensure Python 3.7+ is installed
- Run `python3 scripts/setup_venv.py` to recreate the virtual environment
- Check that cfn-lint is properly installed: `.venv/bin/cfn-lint --version`

**Template Validation Errors**:
- Review error messages for specific file paths and line numbers
- Consult [cfn-lint documentation](https://github.com/aws-cloudformation/cfn-lint) for rule details
- Use `cfn-lint --help` for additional validation options

## Tutorials

Documentation for each template is available in the [docs](./docs) directory.

For a complete tutorial on how to use these templates with the Atlantis Templates and Scripts Plaform, please refer to the [Tutorial Documentation on GitHub](https://github.com/63klabs/tutorials).

## Changelog

[Change Log](./CHANGELOG.md)

## Contributing

[Contributing Guidelines](./CONTRIBUTING.md)

## License

[MIT License](./LICENSE)

## Security

If you discover a potential security issue in this project, please review the [Security Document](./SECURITY.md). All security vulnerabilities will be promptly addressed.

## Author

Chad Kluck
DevOps & Developer Experience Engineer
AWS Certified Cloud Practitioner | AWS Certified Developer - Associate | AWS
Certified Solutions Architect - Associate
[Website](https://chadkluck.me)
