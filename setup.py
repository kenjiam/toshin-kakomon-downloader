from setuptools import find_packages, setup

setup(
    name="toshin-kakomon-downloader",
    version="0.3.0",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4",
        "requests",
        "toml"
    ],
    entry_points={
        "console_scripts": [
            "tkdl=tkdl.main:main",
        ],
    },
    include_package_data=True
)
