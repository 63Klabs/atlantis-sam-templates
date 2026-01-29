---
inclusion: always
---
<!------------------------------------------------------------------------------------
   Add rules to this file or a short description and have Kiro refine them for you.
   
   Learn about inclusion modes: https://kiro.dev/docs/steering/#inclusion-modes
-------------------------------------------------------------------------------------> 

# CloudFormation Template Documentation for End-User 

When templates are created, modified, or deleted, the `docs/templates/v2/` directory is automatically updated with the latest documentation based upon the template.

## Document Structure

Each template documentation file should follow this structure:

### Header Section
- Template title (level-1 `#`) matching the template filename
- Brief description of what the template does (1-2 sentences)
- Template version and last updated date
- Link to the actual template file in the repository using the correct relative path: `../../../../templates/v2/{category}/{template-name}.yml`
  - From `docs/templates/v2/{category}/` you need 4 `../` to reach the repository root, then navigate to `templates/v2/{category}/`
  - Example: `[templates/v2/storage/template-storage-s3-artifacts.yml](../../../../templates/v2/storage/template-storage-s3-artifacts.yml)`

### Overview Section (level-2 `##`)
- Detailed description of the template's purpose
- Use cases and when to use this template
- Prerequisites and dependencies (other templates, existing resources)
- Important notes or warnings

### Parameters Section (level-2 `##`)

The parameters section should be organized based upon the Metadata section of the template. Each parameter group from `AWS::CloudFormation::Interface` should be a level-3 (`###`) heading with the group label as the heading text.

Under each parameter group heading:
1. Include the group description if available
2. List all parameters in that group as a table of contents with links to detailed parameter sections
3. Format: `- [ParameterName](#parametername)` (lowercase anchor links)

Each parameter should have its own detailed section (level-4 `####`) with:
- Parameter name as the heading
- Description from the template
- A two-column table with attributes:

| Attribute | Setting |
|-----------|---------|
| Type | (String, Number, CommaDelimitedList, etc.) |
| Default | (default value or "None") |
| Allowed Values | (if constrained) |
| Allowed Pattern | (regex pattern if specified) |
| Min Length | (if specified) |
| Max Length | (if specified) |
| Constraint Description | (validation message) |

### Resources Section (level-2 `##`)

List all resources that are created by the template. Start with a table of contents linking to each resource:
- Format: `- [ResourceLogicalId](#resourcelogicalid) - ResourceType`
- Include conditional notation if applicable: `(Conditional: ConditionName)`

Each resource should have its own section (level-3 `###`) with:
- Resource logical ID as the heading
- Resource type on the next line (e.g., `Type: AWS::CloudFront::Distribution`)
- Condition on the next line if applicable (e.g., `Condition: CreateDistribution`)
- Description of what the resource does and why it's needed
- Key properties or configurations worth noting
- Dependencies on other resources if relevant

### Outputs Section (level-2 `##`)

List all outputs from the template. Each output should have its own section (level-3 `###`) with:
- Output name as the heading
- Condition if applicable (e.g., `Condition: CreateDistribution`)
- Description from the template
- Export name if the output is exported
- Example value or format
- How this output is typically used

### Additional Sections (Optional)

Include these sections when relevant:
- **Conditions** (level-2 `##`): Document complex conditions and their logic
- **Mappings** (level-2 `##`): Explain any mappings used in the template
- **Examples** (level-2 `##`): Provide example parameter configurations
- **Troubleshooting** (level-2 `##`): Common issues and solutions
- **Related Templates** (level-2 `##`): Links to other templates commonly used together based on the `USE WITH` in the comments section at the top of the template.
- **Tutorials** (level-2 `##`): Links to relevant tutorials or walkthroughs as listed under `TUTORIALS` in the comments section at the top of the template.

## CloudFormation Best Practices

When documenting CloudFormation templates, follow these AWS best practices:

1. **Parameter Documentation**:
   - Clearly explain the purpose and impact of each parameter
   - Document valid value ranges and patterns
   - Explain relationships between parameters
   - Note which parameters are required vs optional
   - Provide examples of typical values

2. **Resource Documentation**:
   - Explain the purpose of each resource in the context of the overall architecture
   - Document resource dependencies and relationships
   - Note any resources that incur costs
   - Explain conditional resource creation logic
   - Document IAM permissions required

3. **Output Documentation**:
   - Explain how outputs are intended to be used
   - Document which outputs are exported for cross-stack references
   - Provide examples of output values
   - Note which outputs are conditional

4. **Security Considerations**:
   - Document any security-related parameters or configurations
   - Note encryption settings and key management
   - Explain IAM roles and policies created
   - Document network security configurations

5. **Cost Considerations**:
   - Note resources that incur ongoing costs
   - Explain cost differences between parameter choices (e.g., CloudFront price classes)
   - Document resources that scale with usage

6. **Operational Notes**:
   - Document update behavior (replacement vs in-place updates)
   - Note any manual steps required before or after deployment
   - Explain rollback behavior
   - Document monitoring and logging configurations

## Template V2 Docs Structure

```
docs/templates/v2/
├── README.md (index linking to all category READMEs)
├── network/
│   ├── README.md (category overview and links to all network template docs)
│   ├── template-network-route53-cloudfront-s3-apigw-README.md
│   └── ...
├── pipeline/
│   ├── README.md (category overview and links to all pipeline template docs)
│   ├── template-pipeline-github-README.md
│   └── ...
├── service-role/
│   ├── README.md (category overview and links to all service-role template docs)
│   ├── template-service-role-pipeline-README.md
│   └── ...
└── storage/
    ├── README.md (category overview and links to all storage template docs)
    ├── template-storage-s3-artifacts-README.md
    └── ...
```

### File Naming Convention
- Template documentation files should be named: `{template-filename}-README.md`
- Example: `template-network-route53-cloudfront-s3-apigw.yml` → `template-network-route53-cloudfront-s3-apigw-README.md`

### Directory README Files
Each category directory (network, pipeline, service-role, storage) should have a README.md that:
- Provides an overview of the category
- Lists all templates in that category with brief descriptions
- Links to each template's detailed documentation
- Explains common use cases for templates in that category

### Main Index README
The main `docs/templates/v2/README.md` should:
- Provide an overview of the template repository
- Link to each category README
- Explain the template versioning scheme
- Provide general guidance on using the templates

## Documentation Maintenance Rules

1. **When a template is created**: Generate complete documentation following the structure above
2. **When a template is modified**: Update only the affected sections of the documentation
3. **When a template is deleted**: Remove the documentation file and update category README
4. **When parameters change**: Update the Parameters section and any affected Examples
5. **When resources change**: Update the Resources section and any affected architecture descriptions
6. **When outputs change**: Update the Outputs section

### Preserving Existing Content

When updating existing template documentation:

1. **Preserve Blockquotes**: Any existing blockquotes (`>`) in the documentation MUST be preserved in the updated version
   - Blockquotes serve as important tips, reminders, and clarifications for both end users and AI
   - They provide context, directives, and guidance that should not be lost during updates
   - When updating a section that contains blockquotes, maintain them in the same context
   - If the content around a blockquote changes significantly, adjust the blockquote placement to maintain its relevance

2. **Read Before Writing**: Before updating any existing documentation file:
   - Read the entire current documentation file first
   - Identify all blockquotes and their context
   - Note any custom sections or content not in the standard structure
   - Preserve all custom content unless it's explicitly outdated or incorrect

3. **Contextual Updates**: When updating documentation sections:
   - Keep blockquotes in their original sections unless the section is removed
   - If a section is restructured, move blockquotes to the most relevant new location
   - Add new blockquotes when documenting important warnings, tips, or AI directives
   - Use blockquotes for:
     - Important warnings about breaking changes or destructive operations
     - Tips for optimal parameter configurations
     - Clarifications about complex behaviors
     - Directives for AI documentation generation
     - Reminders about prerequisites or dependencies

4. **Blockquote Format**: When adding or preserving blockquotes:
   ```markdown
   > **Important:** This is an important note
   > 
   > Additional context can span multiple lines
   ```

5. **Custom Content**: Preserve any custom sections or content that doesn't fit the standard structure:
   - Architecture diagrams or ASCII art
   - Custom examples specific to the template
   - Historical notes about template evolution
   - Migration guides from previous versions
   - Known issues or limitations sections

## Spec-Driven Development Integration

Documentation updates should be included as the **final task** in any spec-driven development process that modifies CloudFormation templates. The task should:
- Be marked as required (not optional)
- Only apply to templates that were actually modified
- Include verification that documentation matches the template
- Update both the template-specific README and the category README if needed

Example task format:
```markdown
- [ ] X.Y Update documentation for modified templates
  - Review and update template-specific README files
  - Update category README if new templates were added
  - Verify all parameters, resources, and outputs are documented
  - Ensure examples and troubleshooting sections are current
```
