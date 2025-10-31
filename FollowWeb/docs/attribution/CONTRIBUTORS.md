# Contributors

## Project Maintainers

### FollowWeb Development Team
- **Role**: Core development, architecture, and maintenance
- **Contributions**: Initial project creation, core algorithms implementation, testing framework, documentation

## Core Dependencies and Third-Party Acknowledgments

FollowWeb Network Analysis Package is built upon the excellent work of numerous open-source projects and their contributors. We extend our gratitude to all the developers and maintainers who have made this project possible.

### Network Analysis Foundation
- **NetworkX Development Team**: For providing the comprehensive graph analysis library that forms the backbone of our network analysis capabilities
- **nx-parallel Contributors**: For parallel processing optimizations that improve performance on large networks

### Data Processing and Visualization
- **pandas Development Team**: For robust data manipulation and analysis tools
- **matplotlib Development Team**: For flexible and powerful plotting capabilities
- **pyvis Development Team**: For interactive network visualization features

### Testing and Quality Assurance
- **pytest Development Team and Ecosystem**: For comprehensive testing framework and extensions
- **Python Code Quality Tool Maintainers**: ruff, mypy teams for code quality tools

### Build and Distribution
- **Python Packaging Authority (PyPA)**: For modern Python packaging tools (build, twine, wheel)
- **tox Development Team**: For multi-environment testing capabilities

## How to Contribute

We welcome contributions from the community! Here are ways you can help:

### Code Contributions
- Bug fixes and improvements
- New analysis algorithms or strategies
- Performance optimizations
- Documentation improvements
- Test coverage enhancements

### Non-Code Contributions
- Bug reports and feature requests
- Documentation improvements
- User experience feedback
- Performance testing and benchmarking
- Community support and discussions

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes with appropriate tests
4. Ensure all quality checks pass (`make check`)
5. Submit a pull request with a clear description

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd followweb-visualizor

# Set up development environment
make dev-setup

# Run tests to ensure everything works
make test

# Run code quality checks
make check
```

### Code Standards
- Follow PEP 8 style guidelines (enforced by ruff)
- Include type hints for all public functions
- Write comprehensive tests for new features
- Update documentation for user-facing changes
- Focus on clean, efficient v1.0 implementation

### Testing Guidelines
- Write unit tests for isolated functionality
- Include integration tests for cross-module features
- Add performance tests for optimization changes
- Ensure all tests pass across supported Python versions

## Recognition

All contributors will be recognized in this file and in release notes. Significant contributions may be acknowledged in the main README and documentation.

### Types of Recognition
- **Code Contributors**: Listed with their contributions
- **Bug Reporters**: Acknowledged in issue resolution
- **Documentation Contributors**: Credited in documentation updates
- **Community Contributors**: Recognized for support and feedback

## License

By contributing to FollowWeb, you agree that your contributions will be licensed under the same MIT License that covers the project.

## Contact

For questions about contributing, please:
- Open an issue for bug reports or feature requests
- Start a discussion for general questions
- Contact the maintainers for sensitive issues

---

Thank you to all contributors who help make FollowWeb better for everyone!