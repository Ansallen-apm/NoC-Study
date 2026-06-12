from setuptools import setup, find_packages

setup(
    name="noc_python_model",
    version="0.1.0",
    packages=["noc_python_model"],
    package_dir={"noc_python_model": "."},
    install_requires=[
        "numpy",
        "networkx"
    ],
)
