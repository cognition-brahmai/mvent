from setuptools import setup, find_packages

setup(
    name="mvent",
    version="0.1.0-a",
    packages=find_packages(),
    install_requires=[],
    author="BRAHMAI",
    author_email="open-source@brahmai.in",
    description="A shared memory event system for Python",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cognitive-brahmai/mvent",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)