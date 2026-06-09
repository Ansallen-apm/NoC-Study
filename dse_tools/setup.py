from setuptools import setup, find_packages

setup(
    name="dse_tools",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "networkx",
        "pyyaml",
        "pandas",
        "scipy"
    ],
)
