from setuptools import setup, find_packages

setup(
    name="mumbl-utils",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.6.0",
        "unicodedata2>=15.0.0",  # Better Unicode handling
    ],
    python_requires=">=3.9",
)

