from setuptools import setup

setup(
    name = "ee",
    version = "0.2",
    author = "snare",
    author_email = "snare@ho.ax",
    description = ("A wrapper for dd"),
    license = "Buy snare a beer",
    keywords = "dd wrapper",
    url = "https://github.com/snarez/ee",
    packages=['ee'],
    install_requires = ['blessings'],
    entry_points = {'console_scripts': ['ee = ee:main']}
)
