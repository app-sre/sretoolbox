SRE Toolbox
===========

Set of libraries commonly used by multiple SRE projects:

- ``container.Image``: class for container image inspection.
- ``container.Skopeo``: wrapper around
  `Skopeo <https://github.com/containers/skopeo>`_.
- ``utils.retry``: decorator to add resilience to function calls.

Install
-------

From PyPI::

    $ pip install sretoolbox

From source::

    $ python setup.py install


Use
---

Just import the library you want. Example::


    >>> from sretoolbox import container
    >>> image = container.Image('fedora')
    >>> if image:
    ...     print('Image exists!')
    ...
    Image exists!
    >>>

Develop
-------

Install the development requirements::

    $  make develop


Run the code checks and tests::

    $  make check

