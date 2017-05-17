from setuptools import setup

setup(name='foglamp',
      version='0.1',
      description='Foglamp',
      url='http://github.com/foglamp',
      author='Scaledb',
      author_email='info@scaledb.com',
      license='MIT',
      packages=['foglamp'],
      install_requires=[
          'aiocoap'
          # , 'aiohttp'
          , 'aiopg'
          , 'cbor2'
          , 'linkheader'
          , 'sqlalchemy'
      ],
      zip_safe=False)
      