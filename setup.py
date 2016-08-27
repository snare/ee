from setuptools import setup

setup(
    name="ee",
    version="0.4",
    author="snare",
    author_email="snare@ho.ax",
    description=("A wrapper for dd"),
    license="Buy snare a beer",
    keywords="dd wrapper",
    url="https://github.com/snare/ee",
    packages=['ee'],
    install_requires=['blessed'],
    entry_points={'console_scripts': ['ee=ee:main']}
)
