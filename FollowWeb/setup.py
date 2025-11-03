"""
Setup configuration for FollowWeb Network Analysis Package.

Social network analysis tool for visualizing Instagram follower/following
relationships using graph theory and network analysis techniques.
"""

# Standard library imports
import os

# Third-party imports
from setuptools import find_packages, setup

# Core dependencies - automatically installed with the package
# These libraries provide the essential functionality for network analysis and visualization
INSTALL_REQUIRES = [
    "networkx>=2.8.0",  # Graph creation, analysis algorithms, and community detection
    "pandas>=1.5.0",  # Data manipulation, CSV/JSON processing, and metrics display
    "matplotlib>=3.5.0",  # Static PNG image generation and graph plotting
    "pyvis>=0.3.0",  # Interactive HTML network visualizations with physics
]

# Optional dependencies for development and testing
# Install with: pip install followweb-visualizor[dev] or pip install followweb-visualizor[test]
EXTRAS_REQUIRE = {
    "dev": [
        "pytest>=7.0.0",  # Testing framework
        "pytest-cov>=4.0.0",  # Coverage reporting
        "pytest-xdist>=3.0.0",  # Parallel test execution
        "pytest-timeout>=2.1.0",  # Test timeout handling
        "pytest-mock>=3.10.0",  # Mocking utilities
        "pytest-benchmark>=4.0.0",  # Performance benchmarking
        "ruff>=0.1.0",  # Code linting and formatting
        "mypy>=1.0.0",  # Type checking
        "faker>=18.0.0",  # Test data generation
        "factory-boy>=3.2.0",  # Test object factories
        "pytest-doctestplus>=0.12.0",  # Enhanced doctest support
        "numpy>=1.21.0",  # Used in test data generation
    ],
    "test": [
        "pytest>=7.0.0",  # Testing framework
        "pytest-cov>=4.0.0",  # Coverage reporting
        "pytest-xdist>=3.0.0",  # Parallel test execution
        "pytest-timeout>=2.1.0",  # Test timeout handling
        "pytest-mock>=3.10.0",  # Mocking utilities
        "pytest-benchmark>=4.0.0",  # Performance benchmarking
        "faker>=18.0.0",  # Test data generation
        "factory-boy>=3.2.0",  # Test object factories
        "pytest-doctestplus>=0.12.0",  # Enhanced doctest support
        "numpy>=1.21.0",  # Used in test data generation
    ],
}


# Read the README file for long description
def read_readme():
    """Read README.md file for long description."""
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, encoding="utf-8") as f:
            return f.read()
    return "FollowWeb Network Analysis Package - Social network analysis tool"


setup(
    name="followweb-visualizor",
    version="1.0.0",
    author="FollowWeb Development Team",
    author_email="followweb.dev@example.com",  # Placeholder email
    description="Social network analysis and visualization tool for Instagram follower/following relationships with community detection and influence metrics",
    long_description="""
FollowWeb Network Analysis Package
==================================

Tool for analyzing and visualizing social networks from Instagram follower/following data.
Creates interactive network graphs with community detection, influence metrics, and analysis reports.

Key Features
------------
• Multiple Analysis Strategies: k-core decomposition, reciprocal connections, and ego-alter analysis
• Interactive Visualizations: HTML graphs with hover tooltips and physics simulation
• Static Exports: High-resolution PNG images for presentations and publications
• Community Detection: Automatic identification of social clusters using Louvain algorithm
• Centrality Metrics: Degree, betweenness, and eigenvector centrality calculations
• Comprehensive Reporting: Detailed text reports with network statistics and parameters
• Professional Architecture: Modular, maintainable codebase with comprehensive error handling

Installation
------------
pip install followweb-visualizor

Usage
-----
# Command line interface
followweb --input data.json --strategy k-core

# Or use Python module
python -m FollowWeb_Visualizor --input data.json --strategy k-core

# Programmatic usage
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

config_dict = {'input_file': 'your_data.json'}
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()

Analysis Strategies
------------------
• K-Core Analysis: Full network analysis identifying densely connected subgraphs
• Reciprocal K-Core: Focus on mutual connections and bidirectional relationships
• Ego-Alter Analysis: Personal network analysis centered on specific users

Output Files
------------
• Interactive HTML: Network visualizations with hover tooltips and physics controls
• Static PNG: High-resolution images suitable for presentations and papers
• Metrics Reports: Detailed analysis statistics, timing, and configuration parameters

Requirements
------------
Python 3.8+ with NetworkX, pandas, matplotlib, pyvis, and supporting libraries.
All dependencies are automatically installed with the package.
    """.strip(),
    long_description_content_type="text/plain",
    url="",  # Add repository URL if available
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Sociology",
        "License :: OSI Approved :: MIT License",  # Update as appropriate
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        "console_scripts": [
            "followweb=FollowWeb_Visualizor.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "FollowWeb_Visualizor": [
            "*.py",
        ],
    },
    keywords=[
        "social network analysis",
        "graph theory",
        "network visualization",
        "community detection",
        "centrality analysis",
        "instagram analysis",
        "follower analysis",
        "network metrics",
        "social media analytics",
        "graph algorithms",
        "network science",
        "social graphs",
    ],
    project_urls={
        "Bug Reports": "https://github.com/followweb/followweb-visualizor/issues",
        "Source": "https://github.com/followweb/followweb-visualizor",
        "Documentation": "https://followweb-visualizor.readthedocs.io/",
        "Contributors": "https://github.com/followweb/followweb-visualizor/blob/main/docs/attribution/CONTRIBUTORS.md",
        "Dependencies": "https://github.com/followweb/followweb-visualizor/blob/main/docs/attribution/DEPENDENCIES_ATTRIBUTION.md",
        "License Notices": "https://github.com/followweb/followweb-visualizor/blob/main/docs/attribution/LICENSE_NOTICES.md",
    },
)
