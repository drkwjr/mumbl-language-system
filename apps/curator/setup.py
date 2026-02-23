from setuptools import find_packages, setup

setup(
    name="mumbl-curator",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.6.0",
        "mumbl-data-contracts",
        "mumbl-storage",
        "sentence-transformers>=2.0.0",
        "numpy>=1.24.0",
    ],
    python_requires=">=3.10",
)
