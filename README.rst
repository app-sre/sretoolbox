SRE Toolbox
===========

Set of tools used by multiple projects.

Install
-------

From PyPI::

    $ pip install sretoolbox

From source::

    $ python setup.py intall


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
