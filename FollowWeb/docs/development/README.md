# Development Documentation

This directory contains developer-focused documentation for the FollowWeb package.

## Developer Documentation

### Core Development Guides
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development setup, guidelines, and contribution process
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation with examples
- **[PACKAGE_OVERVIEW.md](PACKAGE_OVERVIEW.md)** - High-level package architecture and module overview

### Technical Implementation Guides
- **[PARALLEL_PROCESSING_GUIDE.md](PARALLEL_PROCESSING_GUIDE.md)** - Centralized parallel processing system implementation

## User Documentation

User-focused documentation is located in the main `docs/` directory:

- **[../USER_GUIDE.md](../USER_GUIDE.md)** - User guide with tutorials and workflows
- **[../CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md)** - Configuration guide with layout options
- **[../INSTALL_GUIDE.md](../INSTALL_GUIDE.md)** - Installation and setup guide

## Organization

### Developer vs User Documentation

**Developer Documentation** (this directory):
- API references and technical implementation details
- Architecture overviews and module documentation
- Contributing guidelines and development setup
- Technical guides for parallel processing, testing, etc.

**User Documentation** (main docs directory):
- Installation and setup instructions
- User guides and tutorials
- Configuration guides and examples
- End-user focused content

## Contributing

When adding new documentation:

1. **Determine the audience**:
   - **Developers/Contributors**: Place in `docs/development/`
   - **End Users**: Place in main `docs/` directory

2. **Follow naming conventions**:
   - Use descriptive, uppercase names with underscores
   - Include `.md` extension
   - Update this README when adding new files

3. **Maintain organization**:
   - Keep related content together
   - Cross-reference between user and developer docs when appropriate
   - Update navigation links in main README.md

4. **Documentation standards**:
   - Use clear headings and structure
   - Include code examples where appropriate
   - Provide cross-references to related documentation
   - Follow the established markdown formatting style