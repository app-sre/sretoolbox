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
from unittest.mock import patch, MagicMock, create_autospec
from http import HTTPStatus

import pytest
import requests
from requests.exceptions import HTTPError

from sretoolbox.container.image import Image, ImageContainsError, ImageInvalidManifestError

TAG = ('a61f590')
A_SHA = (
  'sha256:bc1ed82a75f2ca160225b8281c50b7074e7678c2a1f61b1fb298e545b455925e')
PARSER_DATA = [
    ('quay.io/redhat-user-workloads/trusted-content-tenant/exhort-alpha/exhort:latest',
     {'scheme': 'docker://',
      'registry': 'quay.io',
      'repository': 'redhat-user-workloads',
      'image': 'trusted-content-tenant/exhort-alpha/exhort',
      'tag': 'latest'}),
    ('memcached',
     {'scheme': 'docker://',
      'registry': 'docker.io',
      'repository': 'library',
      'image': 'memcached',
      'tag': 'latest'}),
    ('docker.io/memcached',
     {'scheme': 'docker://',
      'registry': 'docker.io',
      'repository': 'library',
      'image': 'memcached',
      'tag': 'latest'}),
    ('library/memcached',
     {'scheme': 'docker://',
      'registry': 'docker.io',
      'repository': 'library',
      'image': 'memcached',
      'tag': 'latest'}),
    ('quay.io/app-sre/qontract-reconcile',
     {'scheme': 'docker://',
      'registry': 'quay.io',
      'repository': 'app-sre',
      'image': 'qontract-reconcile',
      'tag': 'latest'}),
    ('docker://docker.io/fedora:28',
     {'scheme': 'docker://',
      'repository': 'library',
      'registry': 'docker.io',
      'image': 'fedora',
      'tag': '28'}),
    ('example-local.com:5000/my-repo/my-image:build',
     {'scheme': 'docker://',
      'registry': 'example-local.com:5000',
      'port': '5000',
      'repository': 'my-repo',
      'image': 'my-image',
      'tag': 'build'}),
    ('docker://docker.io/tnozicka/openshift-acme:v0.8.0-pre-alpha',
     {'scheme': 'docker://',
      'registry': 'docker.io',
      'repository': 'tnozicka',
      'image': 'openshift-acme',
      'tag': 'v0.8.0-pre-alpha'}),
    # By digest
    (f'quay.io/app-sre/pagerduty-operator-registry@{A_SHA}',
     {'scheme': 'docker://',
      'registry': 'quay.io',
      'repository': 'app-sre',
      'image': 'pagerduty-operator-registry',
      # Importantly, tag is unset for by-digest URIs
      'tag': None,
      'digest': A_SHA}),
]

STR_DATA = [
    ('quay.io/redhat-user-workloads/trusted-content-tenant/exhort-alpha/exhort',
     'docker://quay.io/redhat-user-workloads/trusted-content-tenant/exhort-alpha/exhort:latest'),
    ('memcached',
     'docker://docker.io/library/memcached:latest'),
    ('docker.io/fedora',
     'docker://docker.io/library/fedora:latest'),
    ('docker://docker.io/app-sre/fedora',
     'docker://docker.io/app-sre/fedora:latest'),
    ('docker.io:8080/app-sre/fedora:30',
     'docker://docker.io:8080/app-sre/fedora:30'),
    ('quay.io/app-sre/qontract-reconcile:build',
     'docker://quay.io/app-sre/qontract-reconcile:build'),
    # By digest stringifies with the digest
    (f'quay.io/app-sre/pagerduty-operator-registry@{A_SHA}',
     f'docker://quay.io/app-sre/pagerduty-operator-registry@{A_SHA}'),
    # By digest still defaults stuff
    (f'pagerduty-operator-registry@{A_SHA}',
     f'docker://docker.io/library/pagerduty-operator-registry@{A_SHA}'),
    # Absent tag should insert 'latest' tag
    ('registry.access.redhat.com/ubi8/ubi-minimal',
     'docker://registry.access.redhat.com/ubi8/ubi-minimal:latest'),
    (f'registry.access.redhat.com/ubi8/ubi-minimal:{TAG}',
     f'docker://registry.access.redhat.com/ubi8/ubi-minimal:{TAG}'),
]


TAG_OVERRIDE_DATA = [
    ('memcached:20',
     'latest',
     'docker://docker.io/library/memcached:latest'),
    ('docker.io/fedora:31',
     '30',
     'docker://docker.io/library/fedora:30'),
    ('docker://docker.io/app-sre/fedora',
     '25',
     'docker://docker.io/app-sre/fedora:25'),
    ('docker.io:443/app-sre/fedora:30',
     '31',
     'docker://docker.io:443/app-sre/fedora:31'),
    ('quay.io/app-sre/qontract-reconcile:build',
     'latest',
     'docker://quay.io/app-sre/qontract-reconcile:latest'),
    # By digest allows tag override
    (f'quay.io/app-sre/pagerduty-operator-registry@{A_SHA}',
     'foo',
     'docker://quay.io/app-sre/pagerduty-operator-registry:foo'),
]


class TestContainer:

    @pytest.mark.parametrize('image, expected_struct', PARSER_DATA)
    def test_parser(self, image, expected_struct):
        image = Image(image)
        assert image.scheme == expected_struct['scheme']
        assert image.registry == expected_struct['registry']
        assert image.repository == expected_struct['repository']
        assert image.image == expected_struct['image']
        assert image.tag == expected_struct.get('tag')
        expected_digest = expected_struct.get('digest')
        # Condition this to avoid the network.
        if expected_digest:
            assert image.digest == expected_digest

    @pytest.mark.parametrize('image, expected_image_url', STR_DATA)
    def test_str(self, image, expected_image_url):
        image = Image(image)
        assert str(image) == expected_image_url

    @pytest.mark.parametrize('image, tag, expected_image_url',
                             TAG_OVERRIDE_DATA)
    def test_tag_override(self, image, tag, expected_image_url):
        image = Image(image, tag)
        assert str(image) == expected_image_url

    def test_no_tag(self):
        image = Image(f"quay.io/foo/bar@{A_SHA}")
        with pytest.raises(Exception) as e:
            _ = image.url_tag
        assert e.typename == 'NoTagForImageByDigest'

    def test_getitem(self):
        session = create_autospec(requests.Session)
        timeout = 30
        image = Image("quay.io/foo/bar:latest",
                      response_cache={},
                      auth_token="atoken",
                      session=session,
                      timeout=timeout)
        other = image['current']
        assert image.response_cache is other.response_cache
        assert other.auth_token is image.auth_token
        assert other.tag == 'current'
        assert other.session == session
        assert other.timeout == timeout


@patch("sretoolbox.container.image.requests")
@patch.object(Image, '_parse_www_auth')
@patch.object(Image, '_get_auth')
class TestRequestGet:
    expected_accept_header = (
        "application/vnd.docker.distribution.manifest.v1+json,"
        "application/vnd.docker.distribution.manifest.v1+prettyjws,"
        "application/vnd.docker.distribution.manifest.v2+json,"
        "application/vnd.docker.distribution.manifest.list.v2+json,"
        "application/vnd.oci.image.manifest.v1+json,"
        "application/vnd.oci.image.index.v1+json"
    )

    def test_username_and_password_ok(self, getauth, parseauth, mocked_requests):
        r = requests.Response()
        r.status_code = 200
        mocked_requests.request.return_value = r

        i = Image("quay.io/foo/bar:latest", username="user", password="pass")
        i._do_request.__wrapped__(i, "http://www.google.com")

        mocked_requests.request.assert_called_once_with(
            "GET",
            'http://www.google.com',
            headers={'Accept': self.expected_accept_header},
            auth=('user', 'pass'),
            verify=True,
            timeout=None,
        )
        getauth.assert_not_called()
        parseauth.assert_not_called()

    def test_username_and_password_reauthenticate(self, getauth, parseauth, mocked_requests):
        r = requests.Response()
        r.status_code = 401
        r.headers['Www-Authenticate'] = 'something something'
        gets = [r]
        r = requests.Response()
        r.status_code = 200
        gets.append(r)
        mocked_requests.request.side_effect = gets
        r = requests.Response()
        r.status_code = 200
        getauth.return_value = "anauthtoken"
        parseauth.return_value = "aparsedauth"

        i = Image("quay.io/foo/bar:latest", username="user", password="pass")
        i._do_request.__wrapped__(i, "http://www.google.com")

        parseauth.assert_called_once_with('something something')
        assert mocked_requests.request.call_count == 2
        assert i.auth_token == 'anauthtoken'

    def test_persistent_failure(self, getauth, parseauth, mocked_requests):
        r = requests.Response()
        r.status_code = 401
        r.headers['Www-Authenticate'] = 'something something'
        mocked_requests.request.return_value = r
        getauth.return_value = "anauthtoken"
        parseauth.return_value = "aparsedauth"

        i = Image("quay.io/foo/bar:latest", username="user", password="pass")
        with pytest.raises(requests.exceptions.HTTPError):
            i._do_request.__wrapped__(i, "http://www.google.com")

        getauth.assert_called_once()
        parseauth.assert_called_once()

    def test_with_session(self, getauth, parseauth, mocked_requests):
        r = requests.Response()
        r.status_code = 200
        session = create_autospec(requests.Session)
        session.request.return_value = r

        i = Image("quay.io/foo/bar:latest", username="user", password="pass",
                  session=session, timeout=10)
        i._do_request.__wrapped__(i, "http://www.google.com")

        session.request.assert_called_once_with(
            "GET",
            'http://www.google.com',
            headers={'Accept': self.expected_accept_header},
            auth=('user', 'pass'),
            verify=True,
            timeout=10,
        )
        mocked_requests.request.assert_not_called()
        getauth.assert_not_called()
        parseauth.assert_not_called()

class ImageMocks:
    @classmethod
    @pytest.fixture
    def v1_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v1-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/v1-image/manifests/latest',
            headers={
                'Content-Type':
                    'application/vnd.docker.distribution.manifest.v1+json'
            },
            content=manifest.encode(),
        )
        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/v1-image:latest',
        }

    @classmethod
    @pytest.fixture
    def v2_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/v2-image/manifests/latest',
            headers={
                'Content-Type':
                    'application/vnd.docker.distribution.manifest.v2+json',
                'Docker-Content-Digest': 'sha256:8a22fe7cf283894b7b2a8fad9f950'
                                         '2ad3260db4ee31e609f7ce20d06d88d93c7',
            },
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/v2-image:latest',
        }

    @classmethod
    @pytest.fixture
    def v2_fat_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-fat-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/v2-fat-image/manifests/latest',
            headers={'Content-Type':
                'application/vnd.docker.distribution.manifest.list.v2+json'},
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/v2-fat-image:latest'
        }

    @classmethod
    @pytest.fixture
    def oci_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/oci-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/oci-image/manifests/latest',
            headers={
                'Content-Type':
                    'application/vnd.oci.image.manifest.v1+json',
                'Docker-Content-Digest': 'sha256:1712421fab5a88b1d2b722d0dc112'
                                         '3148adc709a179e310e7bc0e3e9a775e834',
            },
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/oci-image:latest',
        }

    @classmethod
    @pytest.fixture
    def oci_fat_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/oci-fat-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/oci-fat-image/manifests/latest',
            headers={'Content-Type': 'application/vnd.oci.image.index.v1+json'},
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/oci-fat-image:latest',
        }

    @classmethod
    @pytest.fixture
    def no_headers_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/image/manifests/latest',
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/image:latest',
        }

    @classmethod
    @pytest.fixture
    def image_with_digest_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            f'https://registry.io/v2/test/image/manifests/{A_SHA}',
            headers={
                'Content-Type':
                    'application/vnd.docker.distribution.manifest.v2+json',
                'Docker-Content-Digest': f'sha256:{A_SHA}'
            },
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': f'docker://registry.io/test/image@{A_SHA}',
        }

    @classmethod
    @pytest.fixture
    def dockerhub_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-image.json') as f:
            manifest = f.read()

        manifest_url = 'https://registry-1.docker.io/v2/test/image/manifests/latest'
        headers = {
            'Content-Type':
                'application/vnd.docker.distribution.manifest.v2+json',
            'Docker-Content-Digest': 'sha256:8a22fe7cf283894b7b2a8fad9f950'
                                     '2ad3260db4ee31e609f7ce20d06d88d93c7',
        }

        requests_mock.get(
            manifest_url,
            headers=headers,
            content=manifest.encode(),
        )

        requests_mock.head(manifest_url, headers=headers)

        return {
            'mock': requests_mock,
            'url': 'docker://docker.io/test/image:latest',
            'manifest_url': manifest_url,
        }

    @classmethod
    @pytest.fixture
    def redhat_registry_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/ubi8-python39-manifest.json') as f:
            manifest = f.read()

        manifest_url = (
            'https://registry.access.redhat.com/'
            'v2/ubi8/python-39/manifests/latest'
        )

        headers = {
            'Content-Type':
                'application/vnd.docker.distribution.manifest.list.v2+json',
            'ETag': '"672c5deca9a237fbc99de2992de0f178:1666889119.378372"',
            'Last-Modified': 'Thu, 27 Oct 2022 15:33:48 GMT',
        }

        requests_mock.get(
            manifest_url,
            [
                {
                    'headers': headers,
                    'content': manifest.encode(),
                    'status_code': HTTPStatus.OK,
                },
                {
                    'headers': headers,
                    'content': manifest.encode(),
                    'status_code': HTTPStatus.NOT_MODIFIED,
                },
            ]
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.access.redhat.com/ubi8/python-39',
            'manifest_url': manifest_url,
        }

    @classmethod
    @pytest.fixture
    def invalid_image_manifest_mock(self, requests_mock):
        with open('tests/fixtures/manifests/invalid-image-manifest.json') as f:
            manifest = f.read()

        manifest_url = 'https://registry-1.docker.io/v2/test/image/manifests/latest'
        headers = {
            'Content-Type':
                'application/vnd.docker.distribution.manifest.v2+json',
            'Docker-Content-Digest': 'sha256:8a22fe7cf283894b7b2a8fad9f950'
                                     '2ad3260db4ee31e609f7ce20d06d88d93c7',
        }

        requests_mock.get(
            manifest_url,
            headers=headers,
            content=manifest.encode(),
        )

        requests_mock.head(manifest_url, headers=headers)

        return {
            'mock': requests_mock,
            'url': 'docker://docker.io/test/image:latest',
            'manifest_url': manifest_url,
        }

class TestImageManifest:
    dockerhub_image_mock = ImageMocks.dockerhub_image_mock
    redhat_registry_image_mock = ImageMocks.redhat_registry_image_mock

    invalid_image_manifest_mock = ImageMocks.invalid_image_manifest_mock

    def test_dockerhub_manifest_unchanged(self, dockerhub_image_mock):
        cache = {}
        token = "Bearer thisIsOneToken"
        i1 = Image(dockerhub_image_mock['url'], response_cache=cache, auth_token=token)
        m1 = i1.manifest

        assert cache
        assert dockerhub_image_mock['mock'].call_count == 1
        assert i1.response_cache_hits == 0
        assert i1.response_cache_misses == 1

        i2 = Image(dockerhub_image_mock['url'], response_cache=cache, auth_token=token)
        m2 = i2.manifest

        assert m1 == m2
        assert dockerhub_image_mock['mock'].call_count == 2
        assert i2.response_cache_hits == 1
        assert i2.response_cache_misses == 0

    def test_conditional_manifest_unchanged(self, redhat_registry_image_mock):
        cache = {}
        i1 = Image(redhat_registry_image_mock['url'], response_cache=cache)
        m1 = i1.manifest

        assert cache
        assert redhat_registry_image_mock['mock'].call_count == 1
        assert i1.response_cache_hits == 0
        assert i1.response_cache_misses == 1

        i2 = Image(redhat_registry_image_mock['url'], response_cache=cache)
        m2 = i2.manifest

        assert m1 == m2
        assert redhat_registry_image_mock['mock'].call_count == 2
        assert i2.response_cache_hits == 1
        assert i2.response_cache_misses == 0

    def test_dockerhub_manifest_changed(self, dockerhub_image_mock):
        rsp = requests.Response()
        rsp.headers = {'Docker-Content-Digest': 'sha256:abc'}
        username = "username"
        key = (dockerhub_image_mock['manifest_url'], username)
        cache = {key: rsp}

        i = Image(
            dockerhub_image_mock['url'],
            response_cache=cache,
            username=username,
            password="password"
        )
        _ = i.manifest

        assert cache[key] != rsp
        assert dockerhub_image_mock['mock'].call_count == 2
        assert i.response_cache_hits == 0
        assert i.response_cache_misses == 1

    def test_conditional_manifest_changed(self, redhat_registry_image_mock):
        rsp = requests.Response()
        rsp.headers = {
            'ETag': '"57255d4ca9aa3afba99de2992de0f178:1556889119.378372"',
            'Last-Modified': 'Thu, 23 Oct 2022 15:33:48 GMT',
        }
        username = "username"
        key = (redhat_registry_image_mock['manifest_url'], username)
        cache = {key: rsp}

        i = Image(
            redhat_registry_image_mock['url'],
            response_cache=cache,
            username=username,
            password="password"
        )
        _ = i.manifest

        assert cache[key] != rsp
        assert redhat_registry_image_mock['mock'].call_count == 1
        assert i.response_cache_hits == 0
        assert i.response_cache_misses == 1

    def test_invalid_image_manifest(self, invalid_image_manifest_mock):
        image = Image(invalid_image_manifest_mock['url'])
        with pytest.raises(ImageInvalidManifestError):
            _ = image.manifest


class TestImageComparison:
    v1_image_mock = ImageMocks.v1_image_mock
    v2_image_mock = ImageMocks.v2_image_mock
    v2_fat_image_mock = ImageMocks.v2_fat_image_mock
    oci_image_mock = ImageMocks.oci_image_mock
    oci_fat_image_mock = ImageMocks.oci_fat_image_mock

    def test_v1_image_comparisons(self,
                                  v1_image_mock,
                                  v2_image_mock,
                                  v2_fat_image_mock,
                                  oci_image_mock,
                                  oci_fat_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_image = Image(v2_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        oci_image = Image(oci_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])

        assert v1_image == v1_image
        assert v1_image != v2_image
        assert v1_image != v2_fat_image
        assert v1_image != oci_image
        assert v1_image != oci_fat_image


    def test_v2_image_comparisons(self,
                                  v1_image_mock,
                                  v2_image_mock,
                                  v2_fat_image_mock,
                                  oci_image_mock,
                                  oci_fat_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_image = Image(v2_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        oci_image = Image(oci_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])

        assert v2_image == v2_image
        assert v2_image != v1_image
        assert v2_image != v2_fat_image
        assert v2_image != oci_image
        assert v2_image != oci_fat_image

    def test_v2_fat_image_comparisons(self,
                                      v1_image_mock,
                                      v2_image_mock,
                                      v2_fat_image_mock,
                                      oci_image_mock,
                                      oci_fat_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_image = Image(v2_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        oci_image = Image(oci_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])

        assert v2_fat_image == v2_fat_image
        assert v2_fat_image != v1_image
        assert v2_fat_image != v2_image
        assert v2_fat_image != oci_image
        assert v2_fat_image != oci_fat_image

    def test_oci_image_comparisons(self,
                                   v1_image_mock,
                                   v2_image_mock,
                                   v2_fat_image_mock,
                                   oci_image_mock,
                                   oci_fat_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_image = Image(v2_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        oci_image = Image(oci_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])

        assert oci_image == oci_image
        assert oci_image != v1_image
        assert oci_image != v2_image
        assert oci_image != v2_fat_image
        assert oci_image != oci_fat_image

    def test_oci_fat_image_comparisons(self,
                                       v1_image_mock,
                                       v2_image_mock,
                                       v2_fat_image_mock,
                                       oci_image_mock,
                                       oci_fat_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_image = Image(v2_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        oci_image = Image(oci_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])

        assert oci_fat_image == oci_fat_image
        assert oci_fat_image != v1_image
        assert oci_fat_image != v2_image
        assert oci_fat_image != v2_fat_image
        assert oci_fat_image != oci_image


class TestManifestAccessors:
    image_mock = ImageMocks.v2_image_mock
    no_headers_image_mock = ImageMocks.no_headers_image_mock
    image_with_digest_mock = ImageMocks.image_with_digest_mock

    def test_no_content_type(self, no_headers_image_mock):
        image = Image(no_headers_image_mock['url'])
        with pytest.raises(HTTPError) as e:
            _ = image.content_type

    def test_no_digest(self, no_headers_image_mock):
        image = Image(no_headers_image_mock['url'])
        with pytest.raises(HTTPError) as e:
            _ = image.digest

    def test_manifest_cached(self, image_mock):
        image = Image(image_mock['url'])
        for i in range(0, 4):
            _ = image.manifest

        assert image_mock['mock'].call_count == 1

    def test_content_type_cached(self, image_mock):
        image = Image(image_mock['url'])
        for i in range(0, 4):
            _ = image.content_type

        assert image_mock['mock'].call_count == 1

    def test_digest_cached(self, image_mock):
        image = Image(image_mock['url'])
        for i in range(0, 4):
            _ = image.digest

        assert image_mock['mock'].call_count == 1

    def test_manifest_caches_other_headers(self, image_mock):
        image = Image(image_mock['url'])

        _ = image.manifest
        assert image_mock['mock'].call_count == 1

        _ = image.content_type
        assert image_mock['mock'].call_count == 1

        _ = image.digest
        assert image_mock['mock'].call_count == 1

    def test_digest_cached_from_arguments(self, image_with_digest_mock):
        image = Image(image_with_digest_mock['url'])
        _ = image.digest
        assert image_with_digest_mock['mock'].call_count == 0


class TestImageIsPartOf:
    v1_image_mock = ImageMocks.v1_image_mock
    v2_image_mock = ImageMocks.v2_image_mock
    v2_fat_image_mock = ImageMocks.v2_fat_image_mock
    oci_image_mock = ImageMocks.oci_image_mock
    oci_fat_image_mock = ImageMocks.oci_fat_image_mock
    v2_other_image_mock = ImageMocks.image_with_digest_mock

    def test_v2_image_contains(self, v2_image_mock, v2_fat_image_mock):
        v2_image = Image(v2_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        assert v2_image.is_part_of(v2_fat_image)

    def test_oci_image_contains(self, oci_image_mock, oci_fat_image_mock):
        oci_image = Image(oci_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])
        assert oci_image.is_part_of(oci_fat_image)

    def test_image_does_not_contain(self,
                                    v2_other_image_mock,
                                    v2_fat_image_mock):
        image = Image(v2_other_image_mock['url'])
        fat_image = Image(v2_fat_image_mock['url'])
        assert not image.is_part_of(fat_image)

    def test_bad_contains_member(self,
                                 v1_image_mock,
                                 v2_fat_image_mock,
                                 oci_fat_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_fat_image = Image(v2_fat_image_mock['url'])
        oci_fat_image = Image(oci_fat_image_mock['url'])

        with pytest.raises(ImageContainsError):
            v1_image.is_part_of(v2_fat_image)

        with pytest.raises(ImageContainsError):
            v2_fat_image.is_part_of(v2_fat_image)

        with pytest.raises(ImageContainsError):
            oci_fat_image.is_part_of(v2_fat_image)

    def test_bad_contains_collection(self,
                                     v1_image_mock,
                                     v2_image_mock,
                                     oci_image_mock):
        v1_image = Image(v1_image_mock['url'])
        v2_image = Image(v2_image_mock['url'])
        oci_image = Image(oci_image_mock['url'])

        with pytest.raises(ImageContainsError):
            v2_image.is_part_of(v1_image)

        with pytest.raises(ImageContainsError):
            v2_image.is_part_of(v2_image)

        with pytest.raises(ImageContainsError):
            v2_image.is_part_of(oci_image)
