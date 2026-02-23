from setuptools import find_packages, setup

setup(
    name="mumbl-radio-ingestion",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.6.0",
        "mumbl-data-contracts",
        "mumbl-storage",
        "openai>=1.0.0",
        "requests>=2.31.0",
        "psycopg[binary]>=3.1.0",
        "structlog>=24.1.0",
    ],
    python_requires=">=3.10",
)
