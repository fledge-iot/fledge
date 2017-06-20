from setuptools import setup

setup(
    name='FogLAMP',
    version='0.1',
    description='FogLAMP',
    url='http://github.com/foglamp/FogLAMP',
    author='OSIsoft, LLC',
    author_email=' ? @osisoft.com',
    license='Apache 2.0',
    packages=['foglamp'],
    entry_points={
        'console_scripts': [
            'foglamp = foglamp_start:main',
            'foglampd = foglamp_daemon:main',
        ],
    },
    zip_safe=False
)
