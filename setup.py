import os
from setuptools import setup, find_packages


def get_version() -> str:
    pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))  # noqa
    filepath = os.path.join(pkg_root, "version.py")
    with open(filepath) as fh:
        return eval(fh.read().strip())

install_requires = [line.rstrip() for line in open(os.path.join(os.path.dirname(__file__), "requirements.txt"))]

setup(
    name="terra_workflow_scale_test_tools",
    version=get_version(),
    description="Tools for GA4GH DRS data access scale testing using Terra workflows.",
    author="Michael Baumann",
    author_email="mbaumann@broadinstitute.org",
    url="https://github.com/mbaumann-broad/terra-workflow-scale-test-tools",
    license="3-Clause BSD",
    packages=find_packages(),
    include_package_data=True,
    package_data={"": ["*.sh", "*.ipynb"]},
    install_requires=install_requires,
    platforms=["MacOS X", "Posix"],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: 3-Clause BSD",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Natural Language :: English",
    ],
    python_requires=">=3.7"
)
