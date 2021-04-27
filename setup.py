import os

from setuptools import setup, find_packages


BASE_PATH = os.path.dirname(__file__)


def get_readme_content():
    with open(os.path.join(BASE_PATH, 'README.rst'), 'r') as readme:
        return readme.read()


def get_version():
    with open(os.path.join(BASE_PATH, 'VERSION'), 'r') as version:
        return version.read().strip()


setup(name='sretoolbox',
      packages=find_packages(),
      version=get_version(),
      author='Red Hat Application SRE Team',
      author_email="sd-app-sre@redhat.com",
      url='https://github.com/app-sre/sretoolbox',
      description='Set of libraries commonly used by multiple SRE projects',
      long_description=get_readme_content(),
      python_requires='>=3.6',
      license="Apache-2.0",
      classifiers=
      [
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: Apache Software License',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3.6',
            'Topic :: Software Development :: Libraries',
      ],
      install_requires=[
          'requests~=2.22',
          'semver~=2.13',
      ]
      )
