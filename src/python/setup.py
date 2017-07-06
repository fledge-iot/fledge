from setuptools import setup

setup(
    name='FogLAMP',
    version='0.1',
    description='FogLAMP',
    url='http://github.com/foglamp/FogLAMP',
    author='OSIsoft, LLC',
    author_email='info@dianomic.com',
    license='Apache 2.0',
    packages=['foglamp'],
    entry_points={
        'console_scripts': [
            'foglamp = foglamp.server:run',
            'foglampd = foglamp.server:main',
        ],
    },
    zip_safe=False
)
