import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ledgerlinker",
    version="1.1.0",
    author="LedgerLinker",
    author_email="help@ledgerlinker.com",
    description="Syncronize your financial institution data to plain text accounting ledgers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ledgerlinker/ledgerlinker",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'ledgerlinker = ledgerlinker.client:main'
        ]
    },
    install_requires=[
        'requests',
        'commentjson',
    ],
    extras_require={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.7',
)
