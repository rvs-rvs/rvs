from setuptools import setup, find_packages
import os

# Read the README file for long description
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="rvs",
    version="2.1.0",
    description="Robust Versioning System - Git-style version control built for universal compatibility",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="rvs-rvs",
    author_email="mailto.rvs@usa.com",
    url="https://github.com/rvs-rvs/rvs",
    project_urls={
        "Bug Reports": "https://github.com/rvs-rvs/rvs/issues",
        "Source": "https://github.com/rvs-rvs/rvs",
        "Documentation": "https://github.com/rvs-rvs/rvs#readme",
    },
    packages=find_packages(),
    install_requires=[
        # Add any dependencies here if needed
    ],
    entry_points={
        "console_scripts": [
            "rvs=rvs.cli:main",
        ],
    },
    python_requires=">=3.6",
    keywords="python git version-control python-3 pypi rvs vcs cli robust portable",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Environment :: Console",
        "Operating System :: OS Independent",
    ],
)
