
# SRE Toolbox

Set of libraries commonly used by multiple SRE projects:

- ``container.Image``: class for container image inspection.
- ``container.Skopeo``: wrapper around [Skopeo](https://github.com/containers/skopeo).
- ``utils.replace_values``: deep replace of object values according to values map.
- ``utils.retry``: decorator to add resilience to function calls.

## Install

From PyPI:

```bash
pip install sretoolbox
```

From source:

```bash
python setup.py install
```

## Usage

Just import the library you want. Example:

```python
>>> from sretoolbox import container
>>> image = container.Image('fedora')
>>> if image:
...     print('Image exists!')
...
Image exists!
>>>
```

## Development

Install the development requirements:

```bash
make develop
```

Run the code checks and tests:

```bash
make check
```

## Release

Bump the version number in `pyproject.toml`. Submit a pull
request to master. When it is merged, create a tag and push it to
`app-sre/sretoolbox`.

This will trigger a CI job that will publish the package on pypi.

## License

The default license of the code in this repository is
[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
That applies for most of the code here, as they were written from scratch,
but exceptions exist. In any case, each module carries the corresponding
licensing information.
