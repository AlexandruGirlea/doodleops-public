# App Versioning


### 1. How versioning works

We will use the following version number system: **`MAJOR.MINOR.PATCH`**. What 
does each number represent:

- MAJOR version will be used when we make incompatible changes;
- MINOR version will be used when we add new functionality that is backward 
compatible, as long as the client is using the same MAJOR version;
- PATCH version will be used when we make backward compatible bug fixes.

### 2. Folder structure:
Below we can see the folder structure for the EAW components:

```bash
├── doodleops
│      └── app_api
│          └── CHANGELOG.md
│          └── VERSION
│      └── app_web
│          └── CHANGELOG.md
│          └── VERSION
```

### 3. VERSION file
The VERSION number will be used for tagging the docker images for deployment.

The contents of the VERSION file will look like this:
```markdown
1.2.3
```

### 4. CHANGELOG file

All version changes should be documented in the CHANGELOG.md file.

Example of how to write the version in the CHANGELOG.md:

```markdown
## [0.1.0] - 2024-01-15
```

Change Actions:
```markdown
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
```

See example below:


```bash
## [0.1.0] - 2024-01-15


### Added
- New API endpoint for .......
- New logging features for ...........


### Changed
- Updated user interface for ...........


### Deprecated
- The previous version of the ...........


### Removed
- Removed deprecated method ...........


### Fixed
- Fixed a bug in ...........


### Security
- Patched SQL injection vulnerability in ...........


## [1.1.1] - 2024-01-15


### Fixed
- Addressed a login issue for ...........
```