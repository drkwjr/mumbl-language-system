from setuptools import setup, find_packages

setup(
    name="mumbl-tts-trainer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.6.0",
        "mumbl-data-contracts",
        "mumbl-storage",
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
    ],
    python_requires=">=3.10",
)

