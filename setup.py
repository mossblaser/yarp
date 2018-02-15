from setuptools import setup, find_packages

with open("yarp/version.py", "r") as f:
    exec(f.read())

setup(
    name="yarp",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/mossblaser/yarp",
    author="Jonathan Heathcote",
    description="Yet Another Reactive(-ish) Programming library.",
    license="GPLv2",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="asyncio reactive functional",

    # Requirements
    install_requires=["sentinel>=0.1.1"],
)
