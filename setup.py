from setuptools import find_packages, setup


setup(
    name="buscemi",
    version="0.0.0",

    description="python library for interacting with uci",
    license="MIT",
    url="https://github.com/numberoverzero/buscemi",

    author="Joe Cross",
    author_email="joe.mcross@gmail.com",

    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=[]),
    include_package_data=True,

    python_requires=">=3.6",
)
