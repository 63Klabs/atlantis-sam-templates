# Initial Spec Prompt

Add Origin Path Parameters to Static and Api

Two parameters should be added
- StaticOriginPath
- ApiOriginPath

The parameters should default to empty string

If the parameters are provided they should be used instead
of the hardcoded values in the template.

The parameters should receive a proper description, validation, and constraint description.

The parameters must start with a `/`
The parmeters must not end with a `/`
However, a single `/` is valid

Example valid values: `/foo`, `/foo/bar`, `/foo-bar/baz_qux`

Example invalid values: `foo`, `foo/bar`, `/foo/`

Placeholders such as {StageId} cannot be used. This should be explicily listed in the parameters description since they are allowed in other situations. Since this template is not variable a specific path can be entered.

The description should state that if left blank, the default value of xxxx will be used. (List the default in the proper description keeping the {StageId} and {ProjectId} placeholders)

If empty the default values should be used.
Conditionals should be implemented to use the parameters instead of defaults
Special care should be taken with how CloudFront uses the origin path for root.
We need to include a `/` in the template parameter so we can use conditionals.
However, when CloudFront uses the origin path for root it needs to be blank. A special condition needs to be implemented for this.

Static current and should be default if StaticOriginPath is empty:
```yaml
OriginPath: !Sub "/${StageId}/public"
```

Api current and should be default if ApiOriginPath is empty:
```yaml
OriginPath: !Sub "/${ProjectId}-${StageId}"
```