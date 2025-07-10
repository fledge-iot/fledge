from setuptools import setup, find_packages

setup(
    name='Fledge',
    python_requires='>=3.6.9',
    version='3.1.0',
    description='Fledge, the open source platform for the Internet of Things',
    url='https://github.com/fledge-iot/fledge',
    author='OSIsoft, LLC; Dianomic Systems Inc.',
    author_email='info@dianomic.com',
    license='Apache 2.0',
    # TODO: list of excludes (tests)
    packages=find_packages(),
    entry_points={
        'console_scripts': [],
    },
    zip_safe=False
)
