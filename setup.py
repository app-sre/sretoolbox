from setuptools import setup, find_packages


setup(name='sretoolbox',
      packages=find_packages(),
      version=open('VERSION').read().strip(),
      author='Red Hat Application SRE Team',
      author_email="sd-app-sre@redhat.com",
      python_requires='>=3.6',
      license="GPLv2+",
      install_requires=['requests~=2.22'])
