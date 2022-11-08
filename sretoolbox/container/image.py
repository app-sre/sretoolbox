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

"""
Abstractions around container images.
"""

import json
import logging
import re
from http import HTTPStatus

import requests

from requests.exceptions import HTTPError

from sretoolbox.utils import retry


_LOG = logging.getLogger(__name__)

SCHEMA1_MANIFEST_MEDIA_TYPE = \
    'application/vnd.docker.distribution.manifest.v1+json'
SCHEMA1_SIGNED_MANIFEST_MEDIA_TYPE = \
    'application/vnd.docker.distribution.manifest.v1+prettyjws'
SCHEMA2_MANIFEST_MEDIA_TYPE = \
    'application/vnd.docker.distribution.manifest.v2+json'
SCHEMA2_MANIFEST_LIST_MEDIA_TYPE = \
    'application/vnd.docker.distribution.manifest.list.v2+json'
OCI_MANIFEST_MEDIA_TYPE = 'application/vnd.oci.image.manifest.v1+json'
OCI_IMAGE_INDEX_MEDIA_TYPE = 'application/vnd.oci.image.index.v1+json'

SINGLE_ARCH_MEDIA_TYPES = [SCHEMA2_MANIFEST_MEDIA_TYPE,
                           OCI_MANIFEST_MEDIA_TYPE]
MULTI_ARCH_MEDIA_TYPES = [SCHEMA2_MANIFEST_LIST_MEDIA_TYPE,
                          OCI_IMAGE_INDEX_MEDIA_TYPE]


class ImageComparisonError(Exception):
    """
    Used when the comparison between images is not possible.
    """


class ImageContainsError(Exception):
    """
    Used when the determining if one image contains other is not possible.
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
    :param response_cache: (optional) Provide a response cache that acts
                           as a dict
    :param ssl_verify: (optional) Whether to verify the SSL certificate
    """

    # This is a method dispatcher to handle how to handle responses that are
    # already present in the response_cache
    _HANDLE_RESPONSE_CACHE_METHODS = {
        "docker.io": "_handle_docker_content_digest",
        "quay.io": "_handle_docker_content_digest",
        "gcr.io": "_handle_docker_content_digest",
        "registry.access.redhat.com": "_handle_conditional_request",
    }

    def __init__(self, url, tag_override=None, username=None, password=None,
                 auth_server=None, response_cache=None, auth_token=None,
                 ssl_verify=True):
        image_data = self._parse_image_url(url)
        self.scheme = image_data['scheme']
        self.registry = image_data['registry']
        self.repository = image_data['repository']
        self.image = image_data['image']
        self.response_cache = response_cache
        self.ssl_verify = ssl_verify

        self.auth_token = auth_token
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
        self._cache_content_type = None

        if self.response_cache is not None:
            self.response_cache_hits = self.response_cache_misses = 0
        else:
            self.response_cache_hits = self.response_cache_misses = None

    def _can_response_be_cached(self):
        # Determines if we have a method to handle response cache entries for
        # the given registry
        return self.registry in self._HANDLE_RESPONSE_CACHE_METHODS

    @property
    def content_type(self):
        """
        Property to return the Content-Type header from the manifest retrieval.
        It caches the result.
        """
        if self._cache_content_type is None:
            _ = self.manifest

        if self._cache_content_type is None:
            raise HTTPError('Content-Type header not found.')

        return self._cache_content_type

    @property
    def digest(self):
        """
        Property to return the Docker-Content-Digest header from the manifest
        retrieval. It caches the result.
        """
        if self._cache_digest is None:
            _ = self.manifest

        if self._cache_digest is None:
            raise HTTPError('Docker-Content-Digest header not found.')

        return self._cache_digest

    @retry(exceptions=(HTTPError, requests.ConnectionError), max_attempts=5)
    def _do_request(self, url, method=requests.get, headers=None):
        # Use any cached tokens, they may still be valid
        request_headers = {
            'Accept': ",".join([
                SCHEMA1_MANIFEST_MEDIA_TYPE,
                SCHEMA1_SIGNED_MANIFEST_MEDIA_TYPE,
                SCHEMA2_MANIFEST_MEDIA_TYPE,
                SCHEMA2_MANIFEST_LIST_MEDIA_TYPE,
                OCI_MANIFEST_MEDIA_TYPE,
                OCI_IMAGE_INDEX_MEDIA_TYPE,
            ])
        }

        if headers:
            request_headers.update(headers)

        if self.auth_token:
            request_headers['Authorization'] = self.auth_token
            auth = None
        else:
            auth = self.auth

        response = method(url, headers=request_headers, auth=auth,
                          verify=self.ssl_verify)

        # Unauthorized, meaning we have to acquire a new token
        if response.status_code == 401:
            auth_specs = response.headers.get('Www-Authenticate')
            if auth_specs is None:
                self._raise_for_status(response)

            www_auth = self._parse_www_auth(auth_specs)

            # Try again, with the new Authorization header
            self.auth_token = self._get_auth(www_auth)
            request_headers['Authorization'] = self.auth_token
            response = method(url, headers=request_headers)

        self._raise_for_status(response)
        return response

    def _get_cache_key(self, url):
        # Returns the cache key. It uses the username as entries in the cache
        # may have been added by a different user with different permissions.
        return (url, self.username)

    def _get_manifest(self):
        # Retrieve the image manifest from the internet or from the response
        # cache if it exists.
        url = f'{self.registry_api}/v2'
        if self.repository is not None:
            url += f'/{self.repository}'
        # NOTE(efried): This should never go to the network. If the image was
        # initialized by digest, the `digest` property uses that value.
        reference = self.tag or self.digest
        # NOTE(efried): At least for quay, this returns schemaVersion 1 by tag
        # and 2 by digest.
        url += f'/{self.image}/manifests/{reference}'

        if self.response_cache is None or not self._can_response_be_cached():
            return self._do_request(url)

        key = self._get_cache_key(url)
        if key in self.response_cache:
            # We use a dispatch table to handle how different registries handle
            # responses that are already present in the response cache. We will
            # favor proper conditional requests if the registry supports it.
            self.response_cache[key] = getattr(
                self, self._HANDLE_RESPONSE_CACHE_METHODS[self.registry]
            )(url)
        else:
            _LOG.debug("CACHE_MISS %s", url)
            self.response_cache_misses += 1
            self.response_cache[key] = self._do_request(url)

        return self.response_cache[key]

    def _get_tags(self):
        """
        Goes to the internet to retrieve all the image tags.
        """
        tags_per_page = 50

        url = f'{self.registry_api}/v2'
        if self.repository is not None:
            url += f'/{self.repository}'
        url += f'/{self.image}/tags/list?n={tags_per_page}'

        response = self._do_request(url)
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
            response = self._do_request(url)

            tags = response.json()['tags']
            all_tags.extend(tags)

        return all_tags

    def _handle_conditional_request(self, url):
        # Handle response cache entries using conditional requests.
        headers = {}
        key = self._get_cache_key(url)
        cached_response = self.response_cache[key]

        etag = cached_response.headers.get("ETag")
        if etag is not None:
            headers["If-None-Match"] = etag

        last_mod = cached_response.headers.get("Last-Modified")
        if last_mod is not None:
            headers["If-Modified-Since"] = last_mod

        rsp = self._do_request(url, headers=headers)

        if rsp.status_code == HTTPStatus.NOT_MODIFIED:
            _LOG.debug("CACHE_HIT %s", url)
            self.response_cache_hits += 1
            return cached_response

        _LOG.debug("CACHE_MISS %s", url)
        self.response_cache_misses += 1
        return rsp

    def _handle_docker_content_digest(self, url):
        # Handle response cache entries using Docker-Content-Digest header.
        # This method has been inspired by DockerHub, which doesn't support
        # proper conditional requests but doesn't count HEAD requests towards
        # quota. See https://docs.docker.com/docker-hub/download-rate-limit/
        # to have more details.
        key = self._get_cache_key(url)
        cached_response = self.response_cache[key]
        header = "Docker-Content-Digest"

        rsp = self._do_request(url, requests.head)

        if header not in rsp.headers:
            _LOG.debug("CACHE_MISS %s", url)
            self.response_cache_misses += 1
            return self._do_request(url)

        if rsp.headers.get(header) != cached_response.headers.get(header):
            _LOG.debug("CACHE_MISS %s", url)
            self.response_cache_misses += 1
            return self._do_request(url)

        _LOG.debug("CACHE_HIT %s", url)
        self.response_cache_hits += 1
        return cached_response

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

    def is_part_of(self, other):
        """
        Checks if this single-arch image is part of the given multi-arch
        image

        :param other: The multi-arch image to check against
        :type other: Image
        :raises ImageContainsError: if this image is not a single-arch
             image or other is not a multi-arch image
        :return: True if this single-arch image is part of the other
        :rtype: bool
        """
        if self.content_type not in SINGLE_ARCH_MEDIA_TYPES:
            raise ImageContainsError(
                f"Unsupported image content type in {self}: "
                f"'{self.content_type}'"
            )

        if other.content_type not in MULTI_ARCH_MEDIA_TYPES:
            raise ImageContainsError(
                f"Unsupported image content type in {other}: "
                f"'{other.content_type}'"
            )

        for manifest in other.manifest['manifests']:
            if manifest['digest'] == self.digest:
                return True

        return False

    @property
    def manifest(self):
        """
        Property to return the manifest. It caches the result.
        """
        if self._cache_manifest is None:
            manifest = self._get_manifest()
            self._cache_manifest = manifest.json()
            self._cache_content_type = manifest.headers.get('Content-Type')
            self._cache_digest = manifest.headers.get('Docker-Content-Digest')

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
        www_authenticate = {}
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
            manifest_content_type = self.content_type
            other_manifest_content_type = other.content_type

            if manifest_content_type != other_manifest_content_type:
                return False

            if manifest_content_type in SINGLE_ARCH_MEDIA_TYPES:
                layers_key = 'layers'
            elif manifest_content_type in MULTI_ARCH_MEDIA_TYPES:
                layers_key = 'manifests'
            else:
                raise ImageComparisonError(
                    f"Found unsupported content type {manifest_content_type} "
                    "while comparing"
                )

        if manifest[layers_key] == other_manifest[layers_key]:
            return True

        return False

    def __getitem__(self, item):
        return Image(url=str(self), tag_override=str(item),
                     username=self.username, password=self.password,
                     auth_server=self.auth_server,
                     response_cache=self.response_cache,
                     auth_token=self.auth_token)

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
