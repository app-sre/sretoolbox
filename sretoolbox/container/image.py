"""
Abstractions around container images.
"""

import json
import logging
import re

import requests

from requests.exceptions import HTTPError

from sretoolbox.utils import retry


_LOG = logging.getLogger(__name__)


class ImageComparisonError(Exception):
    """
    Used when the comparison between images is not possible.
    """


class NoTagForImageByDigest(Exception):
    """
    Raised when the Image was constructed with a by-digest URL and an
    operation is attempted that requires a tag.
    """
    def __init__(self, image):
        super().__init__(
            f"Can't determine a unique tag for Image: {str(image)}")


class Image:
    """
    Represents a container image.

    :param url: The image url. E.g. docker.io/fedora
    :param tag_override: (optional) A specific tag to use instead of
                         the tag provided in the url or the default one
    :param username: (optional) The private registry username
    :param password: (optional) The private registry password
    :param auth_server: (optional) The host that the username and password are
                        meant for
    """
    def __init__(self, url, tag_override=None, username=None, password=None,
                 auth_server=None):
        image_data = self._parse_image_url(url)
        self.scheme = image_data['scheme']
        self.registry = image_data['registry']
        self.repository = image_data['repository']
        self.image = image_data['image']

        if tag_override is None:
            self.tag = image_data['tag']
        else:
            self.tag = tag_override

        self._cache_digest = None
        # If the URL was by-digest, we can cache this right away.
        if image_data['digest']:
            self._cache_digest = f"{image_data['digest']}"

        self.username = username
        self.password = password
        if all([username is not None,
                password is not None]):
            self.auth = (username, password)
        else:
            self.auth = None
        # When the auth_server is provided, we must check if
        # it matches the registry, otherwise we don't send the
        # auth headers (to avoid leaking the credentials)
        self.auth_server = auth_server
        if self.auth_server is not None and self.auth_server != self.registry:
            self.auth = None

        if self.registry == 'docker.io':
            self.registry_api = 'https://registry-1.docker.io'
        else:
            self.registry_api = f'https://{self.registry}'

        self._cache_tags = None
        self._cache_manifest = None

    @property
    def digest(self):
        """
        Property to cache the digest returned by get_manifest()
        """
        if self._cache_digest is None:
            manifest = self._get_manifest()
            digest = manifest.headers.get('Docker-Content-Digest')
            if digest is None:
                raise HTTPError('Docker-Content-Digest header not found.')
            self._cache_digest = digest
        return self._cache_digest

    def _get_manifest(self):
        """
        Goes to the internet to retrieve the image manifest.
        """
        url = f'{self.registry_api}/v2'
        if self.repository is not None:
            url += f'/{self.repository}'
        # NOTE(efried): This should never go to the network. If the image was
        # initialized by digest, the `digest` property uses that value.
        reference = self.tag or self.digest
        # NOTE(efried): At least for quay, this returns schemaVersion 1 by tag
        # and 2 by digest.
        url += f'/{self.image}/manifests/{reference}'
        return self._request_get(url)

    def _get_tags(self):
        """
        Goes to the internet to retrieve all the image tags.
        """
        tags_per_page = 50

        url = f'{self.registry_api}/v2'
        if self.repository is not None:
            url += f'/{self.repository}'
        url += f'/{self.image}/tags/list?n={tags_per_page}'

        response = self._request_get(url)
        tags = all_tags = response.json()['tags']

        # Tags are paginated
        while not len(tags) < tags_per_page:
            next_page = response.links.get('next')

            if next_page is None:
                break
            if self.registry_api in next_page["url"]:
                url = next_page["url"]
            else:
                url = f'{self.registry_api}{next_page["url"]}'
            response = self._request_get(url)

            tags = response.json()['tags']
            all_tags.extend(tags)

        return all_tags

    def is_from(self, other):
        """
        Checks if the the other image served as base image for the
        current image.

        :param other: The base image to check against
        :type other: Image
        :return: True if the current image has the other image as base
        :rtype: bool
        """
        for layer in other.manifest['fsLayers']:
            if layer not in self.manifest['fsLayers']:
                return False
        return True

    @property
    def manifest(self):
        """
        Property to cache the manifest returned but get_manifest()
        """
        if self._cache_manifest is None:
            manifest = self._get_manifest()
            self._cache_manifest = manifest.json()
        return self._cache_manifest

    def _get_auth(self, www_auth):
        """
        Generates the authorization string using the token acquired
        from the www_auth endpoint.
        """
        scheme = www_auth.pop("scheme")

        url = f'{www_auth.pop("realm")}?'
        for key, value in www_auth.items():
            url += f'{key}={value}&'

        response = requests.get(url, auth=self.auth)

        if response.status_code == 401:
            # Try again without auth
            response = requests.get(url)

        self._raise_for_status(response, error_msg=f'unable to retrieve auth '
                                                   f'token from {url}')

        data = response.json()["token"]
        return f'{scheme} {data}'

    @staticmethod
    def _parse_image_url(image_url):
        """
        Parser to split the image urls in its multiple components.

        Images are provided as URLs. E.g.:
            - docker.io/fedora
            - docker.io/fedora:31
            - docker://docker.io/user/fedora
            - docker://registry.example.com:5000/repo01/centos:latest

        Regardless of the components provided in the URL, we have to make
        sure that we can properly split each of them and, for those
        not provided, assume safe defaults.

        Example:
            Considering the image URL "quay.io/app-sre/qontract-reconcile"

        The data structure returned will be:
            {'scheme': 'docker://',
             'registry': 'quay.io',
             'repository': 'app-sre',
             'image': 'qontract-reconcile',
             'tag': 'latest'}

        :param image_url: The image url to be parsed.
        :type image_url: str
        :return: A data structure with all the parsed components of
                 the image URL, already filled with the defaults for
                 those not provided.
        :rtype: dict
        """

        default_scheme = 'docker://'
        default_registry = 'docker.io'
        default_tag = 'latest'

        # The image is either specified by digest (...@sha256:xxxx...) or
        # by tag (...:tag-name). We decide based on the presence of the
        # '@' or the ':'. If we find neither, by-tag is assumed,
        # defaulting to 'latest'.
        parsed_image_url = re.search(
            r'(?P<scheme>\w+://)?'  # Scheme (optional) e.g. docker://
            r'(?P<registry>[\w\-]+[.][\w\-.]+)?'  # Registry domain (optional)
            r'(?(registry)(?P<port_colon>[:]))?'  # Port colon (optional)
            r'(?(port_colon)(?P<port>[0-9]+))'  # Port (optional)
            r'(?(registry)(?P<registry_slash>/))'  # Slash after domain:port
            r'(?P<repository>[\w\-]+)?'  # Repository (optional)
            r'(?(repository)(?P<repo_slash>/))'  # Slash, if repo is present
            r'(?P<image>[\w\-.]+)'  # Image path (mandatory)
            # '@' delimiter iff it's a by-digest URI (optional)
            r'(?P<digest_at>@)?'
            # Digest ('sha256:' + 64 lowercase hex chars) iff '@' is present
            r'(?(digest_at)(?P<digest>sha256:[0-9a-f]{64}))'
            # Tag colon if it's a by-digest URI (optional)
            # Not allowed if we found a digest
            r'(?(digest)|(?P<tag_colon>:))?'
            # Tag (if tag colon is present)
            r'(?(tag_colon)(?P<tag>[\w\-.]+))'
            '$', image_url)

        if parsed_image_url is None:
            raise AttributeError(f'Not able to parse "{image_url}"')

        image_url_struct = parsed_image_url.groupdict()

        if image_url_struct.get('scheme') is None:
            image_url_struct['scheme'] = default_scheme

        if image_url_struct.get('registry') is None:
            image_url_struct['registry'] = default_registry

        port = image_url_struct.get('port')
        if port is not None:
            image_url_struct['registry'] += f':{port}'

        if image_url_struct.get('repository') is None:
            if image_url_struct['registry'] == 'docker.io':
                image_url_struct['repository'] = 'library'
            else:
                image_url_struct['repository'] = None

        # By-digest URIs don't use tags; but otherwise default to `latest` if
        # absent
        if all(image_url_struct.get(x) is None for x in ('tag', 'digest')):
            image_url_struct['tag'] = default_tag

        return image_url_struct

    @staticmethod
    def _parse_www_auth(value):
        www_authenticate = dict()
        www_authenticate['scheme'], params = value.split(' ', 1)

        # According to the RFC6750, the scheme MUST be followed by
        # one or more auth-param values.
        # This regex gets the extra auth-params and adds them to
        # the www_authenticate dictionary
        for item in re.finditer('(?P<key>[^ ,]+)="(?P<value>[^"]+)"', params):
            www_authenticate[item.group('key')] = item.group('value')

        return www_authenticate

    def _raise_for_status(self, response, error_msg=None):
        """
        Includes the error messages, important for a registry
        """
        if response.status_code < 400:
            return None

        msg = ''
        if error_msg is not None:
            msg += f'{error_msg}: '

        msg += f'({response.status_code}) {response.reason}'
        try:
            content = response.json()
        except json.decoder.JSONDecodeError as details:
            raise HTTPError(msg) from details

        if "errors" in content:
            for error in content['errors']:
                msg += f', {error["message"]}'
        _LOG.debug('[%s, %s]', str(self), msg)
        raise HTTPError(msg)

    @retry(exceptions=(HTTPError, requests.ConnectionError), max_attempts=5)
    def _request_get(self, url):
        # Try first without 'Authorization' header
        headers = {
            'Accept':
                'application/vnd.docker.distribution.manifest.v1+json,'
                'application/vnd.docker.distribution.manifest.v2+json,'
                'application/vnd.docker.distribution.manifest.v1+prettyjws,'
        }

        response = requests.get(url, headers=headers, auth=self.auth)

        # Unauthorized, meaning we have to acquire a token
        if response.status_code == 401:
            auth_specs = response.headers.get('Www-Authenticate')
            if auth_specs is None:
                self._raise_for_status(response)

            www_auth = self._parse_www_auth(auth_specs)

            # Try again, this time with the Authorization header
            headers['Authorization'] = self._get_auth(www_auth)
            response = requests.get(url, headers=headers)

        self._raise_for_status(response)
        return response

    @property
    def tags(self):
        """
        Returns the list of tags.
        """
        if self._cache_tags is None:
            try:
                self._cache_tags = self._get_tags()
            except HTTPError:
                self._cache_tags = []

        return self._cache_tags

    @property
    def url_digest(self):
        """
        Returns the image url in the digest format.
        """
        url_digest = f'{self.registry}'
        if self.repository is not None:
            url_digest += f'/{self.repository}'
        url_digest += f'/{self.image}@{self.digest}'
        return url_digest

    @property
    def url_tag(self):
        """
        Returns the image url in the tag format.

        If we were constructed with a by-digest URL, this will raise
        NoTagForImageByDigest since there may be more than one tag for a given
        image.
        """
        if self.tag is None:
            raise NoTagForImageByDigest(self)

        url_tag = f'{self.registry}'
        if self.repository is not None:
            url_tag += f'/{self.repository}'
        url_tag += f'/{self.image}:{self.tag}'
        return url_tag

    def __bool__(self):
        try:
            return bool(self.manifest)
        except HTTPError:
            return False

    def __contains__(self, item):
        return item in self.tags

    def __eq__(self, other):
        # Two instances are considered equal if both of their
        # manifests are accessible and first item of the 'history'
        # (the most recent) is the same.
        try:
            manifest = self.manifest
            other_manifest = other.manifest
        except HTTPError as details:
            raise ImageComparisonError(details) from details

        manifest_version = manifest['schemaVersion']
        other_manifest_version = other_manifest['schemaVersion']

        if manifest_version != other_manifest_version:
            return False

        if manifest_version == 1:
            layers_key = 'fsLayers'
        else:
            layers_key = 'layers'

        if manifest[layers_key] == other_manifest[layers_key]:
            return True

        return False

    def __getitem__(self, item):
        return Image(url=str(self), tag_override=str(item),
                     username=self.username, password=self.password,
                     auth_server=self.auth_server)

    def __iter__(self):
        for tag in self.tags:
            yield tag

    def __len__(self):
        return len(self.tags)

    def __repr__(self):
        return f"{self.__class__.__name__}(url='{self}')"

    def __str__(self):
        if self.tag is None:
            url = self.url_digest
        else:
            url = self.url_tag
        return f'{self.scheme}{url}'
