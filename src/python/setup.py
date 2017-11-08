from setuptools import setup, find_packages

setup(
    name='FogLAMP',
    version='0.1',
    description='FogLAMP',
    url='http://github.com/foglamp/FogLAMP',
    author='OSIsoft, LLC',
    author_email='info@dianomic.com',
    license='Apache 2.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'foglamp = foglamp.core.server:main'
        ],
    },
    zip_safe=False
)
