# CloudFormation Template Version Control

## Quick Reference

**When making template changes:**

| Scenario | PATCH = 0 | PATCH > 0 | Action Required |
|----------|-----------|-----------|-----------------|
| Non-breaking change | No version change | Auto-increment PATCH | Update version + date |
| Non-critical breaking | No version change | Create new file (MINOR) | New file + migration testing + 24-month support |
| Critical breaking | No version change | Create new file (MAJOR) | New file + migration testing + 24-month support |

**Key Rules:**
- PATCH = 0: Development mode, no automatic versioning
- PATCH > 0: Production mode, automatic PATCH increments for non-breaking changes
- Breaking changes: Always create new versioned file + test migration
- Deprecation: 24-month support period for old versions
- Archive location: `templates/archived/v2/<category>/`

## Version Format

Each CloudFormation template MUST list a version and date in the comment section at the top of the file.

**Format:** `Version: vMAJOR.MINOR.PATCH/YYYY-MM-DD`

**Example:**
```yaml
# Version: v2.0.17/2025-12-16
```

## Semantic Versioning Rules

### Version Number Structure: vMAJOR.MINOR.PATCH

- **MAJOR**: Incremented for critical breaking changes that require user intervention
- **MINOR**: Incremented for non-critical breaking changes
- **PATCH**: Incremented for non-breaking changes (bug fixes, improvements)

### Development Version Indicator

**If the PATCH version is 0** (e.g., v0.0.0, v0.1.0, v2.1.0), this indicates:
- Template is in active development
- Template has NOT been deployed to any environment
- Breaking changes MAY occur without creating a new template file
- No version stability guarantees
- PATCH increments do NOT occur automatically

**After initial deployment:**
- Version MUST be manually incremented to v0.0.1 (or higher)
- All subsequent changes follow semantic versioning rules
- Breaking changes require new template files
- PATCH increments occur automatically for non-breaking changes

## Breaking Changes

### Critical Breaking Changes (MAJOR version bump)

Changes that REQUIRE user intervention or cause stack update failures:

- **Parameter Changes:**
  - Renaming parameters
  - Removing required parameters
  - Changing parameter types
  - Removing parameters with no default value

- **Resource Changes:**
  - Renaming logical IDs of critical resources (causes replacement)
  - Removing critical resources (Lambda functions, DynamoDB tables, S3 buckets with data)
  - Changing resource types
  - Changes that force resource replacement with data loss

- **Output Changes:**
  - Removing or renaming exported outputs (breaks dependent stacks)
  - Changing export names

- **Structural Changes:**
  - Removing or renaming conditions used by other stacks
  - Changes to stack dependencies

### Non-Critical Breaking Changes (MINOR version bump)

Changes that may require stack updates but don't cause failures:

- **Parameter Changes:**
  - Changing default values (may affect new deployments)
  - Adding constraints to existing parameters
  - Removing optional parameters with defaults

- **Resource Changes:**
  - Removing non-critical resources (CloudWatch alarms, logs)
  - Renaming non-critical resource logical IDs
  - Changes that force replacement of stateless resources

- **Output Changes:**
  - Removing non-exported outputs
  - Changing output descriptions

### Non-Breaking Changes (PATCH version bump)

Changes that are backward compatible:

- **Additions:**
  - Adding new optional parameters
  - Adding new resources
  - Adding new outputs
  - Adding new conditions or mappings

- **Improvements:**
  - Bug fixes
  - Documentation updates in comments
  - Improving resource configurations without changing behavior
  - Adding tags
  - Optimizing IAM policies (without removing permissions)

- **Clarifications:**
  - Updating parameter descriptions
  - Improving constraint descriptions
  - Adding comments

## Version Increment Process

### Automatic Patch Increment

**When:** Non-breaking changes are made to a deployed template (PATCH > 0)

**Trigger Points:**
1. **Spec-Driven Development:** First task of any spec workflow that modifies a template
2. **Direct Template Changes:** Any manual "vibe coding" changes to a template

**Process:**
1. Check if PATCH > 0 (if PATCH = 0, skip increment)
2. Increment PATCH version by 1
3. Update date to current date (YYYY-MM-DD format)
4. Make template changes
5. Update documentation if needed
6. Commit changes with version increment noted

**Example:** v2.0.17 → v2.0.18

**Important:** PATCH increment happens BEFORE making changes, not after. This ensures the version number reflects the upcoming changes.

### Manual Minor Increment (Non-Critical Breaking Change)

**When:** Non-critical breaking changes are required

**Process:**
1. Create NEW template file: `template-name-v2-1.yml`
2. Copy current template to new file
3. Set version to v2.1.0 in new file
4. Make breaking changes to new file
5. **Create and test migration procedure**
6. Update documentation for new template
7. Mark old template as deprecated in documentation (24-month sunset)
8. Provide migration guide in documentation

**Example:** 
- Old: `template-pipeline.yml` (v2.0.17) - deprecated, 24-month support
- New: `template-pipeline-v2-1.yml` (v2.1.0) - current

### Manual Major Increment (Critical Breaking Change)

**When:** Critical breaking changes are required

**Process:**
1. Create NEW template file: `template-name-v3-0.yml`
2. Copy current template to new file
3. Set version to v3.0.0 in new file
4. Make breaking changes to new file
5. **Create comprehensive migration procedure**
6. **Test migration from old to new version**
7. Create comprehensive migration guide
8. Update documentation for new template
9. Mark old template as deprecated with 24-month sunset date
10. Provide side-by-side comparison in documentation

**Example:**
- Old: `template-pipeline.yml` (v2.0.17) - deprecated, 24-month support
- New: `template-pipeline-v3-0.yml` (v3.0.0) - current

## File Naming Conventions

### Current/Latest Version
- **Filename:** `template-name.yml` (no version suffix)
- **Version:** Latest stable version
- **Usage:** Default template for new deployments

### Versioned Templates
- **Filename:** `template-name-vMAJOR-MINOR.yml`
- **Version:** Specific major.minor version
- **Usage:** Maintained for backward compatibility

**Examples:**
```
template-pipeline.yml              # v2.0.17 (current)
template-pipeline-v2-1.yml         # v2.1.0 (newer with breaking changes)
template-pipeline-v3-0.yml         # v3.0.0 (major rewrite)
```

## Spec-Driven Development Integration

### Breaking Change Detection

When a specification, requirements, design, or task requires changes that would be breaking:

1. **Analyze Impact:**
   - Identify which changes are breaking
   - Classify as MAJOR or MINOR
   - Document affected parameters, resources, outputs

2. **Prompt User:**
   - Present breaking changes clearly
   - Explain impact on existing deployments
   - Offer options:
     - Create new versioned template
     - Modify approach to avoid breaking changes
     - Cancel and revise requirements

3. **User Confirmation Required:**
   - User must explicitly confirm breaking changes
   - User must approve new template file creation
   - User must acknowledge migration requirements

### Version Increment Rules for Specs

**First Task: Version Increment (if PATCH > 0)**

When a spec-driven development workflow modifies a template:

1. **Check Current Version:**
   - If PATCH = 0: Skip version increment (development mode)
   - If PATCH > 0: Proceed with increment

2. **Analyze Changes:**
   - Review spec requirements and design
   - Identify if changes are breaking or non-breaking
   - Classify breaking changes as MAJOR or MINOR

3. **Non-Breaking Changes:**
   - Increment PATCH version as first task
   - Update date
   - Proceed with implementation

4. **Breaking Changes:**
   - Prompt user with breaking change analysis
   - Explain impact on existing deployments
   - Offer options:
     - Create new versioned template (MINOR or MAJOR)
     - Modify approach to avoid breaking changes
     - Cancel and revise requirements
   - Require explicit user confirmation
   - **Require migration testing plan**

5. **User Confirmation Required For Breaking Changes:**
   - User must explicitly confirm breaking changes
   - User must approve new template file creation
   - User must acknowledge 24-month support commitment
   - User must approve migration testing requirements

### Multiple Template Changes in Single Spec

When a spec modifies multiple templates:

1. **Version Increment Task Per Template:**
   - Create separate version increment task for each template
   - Each task checks PATCH value independently
   - Format: "X.1 Increment version for template-name.yml (if PATCH > 0)"

2. **Breaking Change Analysis:**
   - Analyze each template independently
   - Some templates may have breaking changes, others non-breaking
   - Prompt user for each template with breaking changes

3. **Task Organization:**
   ```markdown
   - [ ] 1. Version Management
     - [ ] 1.1 Increment version for template-pipeline.yml (if PATCH > 0)
     - [ ] 1.2 Increment version for template-storage.yml (if PATCH > 0)
   - [ ] 2. Implementation Tasks
     - [ ] 2.1 Update pipeline template
     - [ ] 2.2 Update storage template
   - [ ] 3. Documentation
     - [ ] 3.1 Update template-pipeline documentation
     - [ ] 3.2 Update template-storage documentation
     - [ ] 3.3 Update CHANGELOG.md
   ```

### Migration Testing Requirements

For all breaking changes (MINOR and MAJOR):

1. **Test Migration Procedure:**
   - Create test stack with old template version
   - Document step-by-step migration process
   - Execute migration to new template version
   - Verify all resources migrate correctly
   - Test rollback procedure

2. **Document Migration:**
   - Parameter mapping (old → new)
   - Resource changes and impacts
   - Required manual steps
   - Rollback procedure
   - Common issues and solutions

3. **Validation:**
   - Confirm no data loss
   - Verify application functionality
   - Check dependent stacks still work
   - Test in non-production environment first

## Template Lifecycle

### Version Validation

Before making any template changes, validate the current version:

**Validation Checklist:**
1. **Check version format:** `Version: vMAJOR.MINOR.PATCH/YYYY-MM-DD`
2. **Verify PATCH value:** Determines if auto-increment applies
3. **Check deployment status:** Development (PATCH=0) vs Production (PATCH>0)
4. **Review version history:** Check template README for previous changes
5. **Identify dependencies:** Check which stacks use this template

**Version Detection:**
```bash
# Extract version from template
grep "^# Version:" template-name.yml

# Example output:
# Version: v2.0.17/2025-01-15
```

### 1. Development Phase
- **Version:** v0.0.0, v0.1.0, v1.0.0, etc. (PATCH = 0)
- **Status:** Unstable, breaking changes allowed
- **File:** Single template file without version suffix
- **Changes:** All changes allowed without new files

### 2. Initial Deployment
- **Action:** Manually increment to v0.0.1 (or v0.1.1, v1.0.1)
- **Status:** Stable, semantic versioning enforced
- **File:** Same template file
- **Changes:** Follow semantic versioning rules

### 3. Maintenance Phase
- **Non-Breaking:** Increment PATCH, update existing file
- **Breaking:** Create new versioned file, maintain old file

### 4. Deprecation Phase
- **Action:** Mark template as deprecated in documentation
- **Timeline:** 24-month sunset period from deprecation date
- **Support:** Continue bug fixes (PATCH) only, no new features
- **Migration:** Provide migration guide to newer version
- **Communication:** Announce deprecation to users with sunset date

### 5. Sunset Phase
- **Action:** Remove template from active directory after 24-month period
- **Archive:** Move to `templates/archived/v2/<category>/` directory
  - Example: `templates/archived/v2/pipeline/template-pipeline-v2-0.yml`
- **Documentation:** Update to indicate archived status and archive location
- **Support:** No further updates or support

## Documentation Requirements

### CHANGELOG Integration

All template version changes MUST be documented in the repository `CHANGELOG.md`:

**Format:**
```markdown
## [Template Name] vX.Y.Z - YYYY-MM-DD

### Added
- New features or resources

### Changed
- Modifications to existing functionality

### Deprecated
- Features marked for removal (with sunset date)

### Removed
- Features removed in this version

### Fixed
- Bug fixes

### Breaking Changes
- List all breaking changes with migration notes
- Link to migration guide
```

**Example:**
```markdown
## [template-pipeline] v2.1.0 - 2025-01-28

### Changed
- Default value of `DeployEnvironment` changed from "DEV" to "PROD"

### Breaking Changes
- **MINOR BREAKING:** Default environment change may affect new deployments
- Migration guide: See docs/templates/v2/pipeline/template-pipeline-v2-1-README.md#migration
- Old version (v2.0.x) deprecated with 24-month support period ending 2027-01-28
```

### Version Changes in Documentation

When template version changes:

1. **Template README:**
   - Update version number in header
   - Add version history section if not present
   - Document breaking changes in dedicated section

2. **Category README:**
   - Update template version references
   - Add migration notes for breaking changes
   - Link to archived versions if applicable

3. **Migration Guides:**
   - Required for MINOR and MAJOR version bumps
   - Document parameter mapping (old → new)
   - Provide step-by-step migration process
   - Include rollback procedures

### Version History Format

Add to template README:

```markdown
## Version History

### v2.1.0 (2025-12-16) - BREAKING CHANGES
- **Breaking:** Renamed parameter `S3Bucket` to `S3BucketName`
- **Breaking:** Removed deprecated `LegacyMode` parameter
- Added support for new caching policies
- See [Migration Guide](#migration-from-v20x-to-v21x)

### v2.0.17 (2025-11-15)
- Fixed IAM policy for S3 access
- Improved error handling in CodeBuild

### v2.0.16 (2025-10-20)
- Added support for additional regions
- Updated Lambda runtime versions
```

## Examples

### Example 1: Non-Breaking Change (PATCH)

**Scenario:** Fix bug in IAM policy

**Current:** `template-storage.yml` v1.2.5

**Action:**
1. Fix IAM policy in `template-storage.yml`
2. Update version to v1.2.6
3. Update date
4. Commit changes

**Result:** `template-storage.yml` v1.2.6

---

### Example 2: Non-Critical Breaking Change (MINOR)

**Scenario:** Change default value of `DeployEnvironment` from "DEV" to "PROD"

**Current:** `template-pipeline.yml` v2.0.17

**Action:**
1. Create `template-pipeline-v2-1.yml`
2. Set version to v2.1.0
3. Change default value
4. **Test migration procedure:**
   - Deploy test stack with v2.0.17
   - Update stack to v2.1.0
   - Verify no disruption
   - Document any manual steps
5. Create migration guide with tested procedure
6. Update documentation
7. Mark v2.0.x as deprecated (24-month sunset)

**Result:** 
- `template-pipeline.yml` v2.0.17 (deprecated, 24-month support)
- `template-pipeline-v2-1.yml` v2.1.0 (current)

---

### Example 3: Critical Breaking Change (MAJOR)

**Scenario:** Rename parameter `S3ArtifactsBucket` to `ArtifactsBucketName` and change resource structure

**Current:** `template-pipeline.yml` v2.0.17

**Action:**
1. Create `template-pipeline-v3-0.yml`
2. Set version to v3.0.0
3. Make breaking changes
4. **Comprehensive migration testing:**
   - Deploy test stack with v2.0.17
   - Create migration script/procedure
   - Test migration to v3.0.0
   - Verify all resources work correctly
   - Test rollback procedure
   - Document all findings
5. Create comprehensive migration guide with tested procedures
6. Update all documentation
7. Set 24-month deprecation timeline for v2.x

**Result:**
- `template-pipeline.yml` v2.0.17 (deprecated, 24-month sunset)
- `template-pipeline-v3-0.yml` v3.0.0 (current)

**After 24 months:**
- `templates/archived/v2/pipeline/template-pipeline-v2-0.yml` (archived)

## Best Practices

1. **Avoid Breaking Changes:** Always try to make changes backward compatible
2. **Deprecation Warnings:** Add deprecation warnings before removing features
3. **Migration Guides:** Always provide clear migration paths with tested procedures
4. **Version Documentation:** Keep version history up to date in template READMEs
5. **Testing:** Test version upgrades thoroughly before release (required for breaking changes)
6. **Communication:** Announce breaking changes to users in advance with clear timelines
7. **Backward Compatibility:** Maintain old versions for 24-month deprecation period
8. **Clear Naming:** Use consistent file naming for versioned templates
9. **Archive Organization:** Maintain archived templates in category-specific directories
10. **CHANGELOG Updates:** Document all version changes in repository CHANGELOG.md

## Questions for Clarification

Before implementing version control changes, consider:

1. **What is the current deployment status?** (Development vs. Deployed)
2. **What type of change is being made?** (Breaking vs. Non-breaking)
3. **How many stacks are using this template?** (Impact assessment)
4. **What is the migration complexity?** (User effort required)
5. **Is there a backward-compatible alternative?** (Avoid breaking if possible)
6. **What is the deprecation timeline?** (24 months from deprecation date)

## Troubleshooting

### Common Scenarios

**Scenario 1: Forgot to increment PATCH before making changes**
- **Solution:** Increment PATCH now before committing
- **Note:** Version should reflect the state AFTER changes

**Scenario 2: Made breaking change without creating new file**
- **Solution:** 
  - If not yet committed: Revert changes, create new versioned file
  - If already committed: Create new versioned file, revert breaking changes from old file
  - Document the correction in CHANGELOG

**Scenario 3: Template marked as PATCH=0 but already deployed**
- **Solution:** Immediately increment to appropriate version (e.g., v2.0.1)
- **Note:** This indicates the template was deployed without proper version tracking

**Scenario 4: Need to make emergency fix to deprecated template**
- **Solution:** 
  - Increment PATCH on deprecated template
  - Apply fix
  - Update documentation
  - Remind users to migrate to current version

**Scenario 5: Breaking change discovered after release**
- **Solution:**
  - If MINOR: Document as breaking in README and CHANGELOG
  - If MAJOR: Consider creating new MAJOR version
  - Provide migration guide immediately
  - Communicate to all users

**Scenario 6: Multiple developers working on same template**
- **Solution:**
  - Coordinate version increments
  - First developer increments version
  - Subsequent developers use same version number
  - All changes included in single version bump

### Version Conflict Resolution

**When two branches increment the same version:**
1. Merge the first branch
2. Second branch must increment to next version
3. Update CHANGELOG to reflect both changes
4. Coordinate with team to avoid conflicts

**When breaking and non-breaking changes conflict:**
1. Breaking changes take precedence
2. Create new versioned file for breaking changes
3. Apply non-breaking changes to both old and new versions (if applicable)
4. Document clearly in CHANGELOG