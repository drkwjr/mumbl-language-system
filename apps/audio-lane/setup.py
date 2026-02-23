from setuptools import find_packages, setup

setup(
    name="mumbl-audio-lane",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.6.0",
        "mumbl-data-contracts",
        "mumbl-storage",
        "yt-dlp>=2024.0.0",
        "openai>=1.0.0",
        "pyannote.audio>=3.0.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.0",
        "numpy>=1.24.0",
    ],
    python_requires=">=3.10",
)
