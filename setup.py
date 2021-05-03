# Copyright 2021 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
