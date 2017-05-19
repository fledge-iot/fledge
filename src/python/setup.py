from setuptools import setup

setup(
    name='FogLAMP',
    version='0.1',
    description='FogLAMP',
    url='http://github.com/foglamp/FogLAMP',
    author='DB Software Inc.',
    author_email='info@scaledb.com',
    license='MIT',
    packages=['foglamp'],
    entry_points={
        'console_scripts': [
            'foglamp = src.python.foglamp:main',
        ],
    },
    zip_safe=False
)
