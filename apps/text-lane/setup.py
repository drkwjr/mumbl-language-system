from setuptools import find_packages, setup

setup(
    name="mumbl-text-lane",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.6.0",
        "mumbl-data-contracts",
        "mumbl-storage",
    ],
    python_requires=">=3.9",
)
