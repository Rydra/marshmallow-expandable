#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='marshmallow-expandable',
      version='0.1.0',
      description='A mixin to add REST resource expansion capabilities to your APIs with Marshmallow',
      url='https://github.com/Rydra/marshmallow-expandable',
      author='David Jiménez (Rydra)',
      author_email='davigetto@gmail.com',
      license='MIT',
      keywords='rest expansion resource expand marshmallow api',
      packages=find_packages(),
      classifiers=[
          'Development Status :: 3',
          'Programming Language :: Python'
      ],
      install_requires=[
          "marshmallow"
      ],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      include_package_data=True,
      zip_safe=False)
