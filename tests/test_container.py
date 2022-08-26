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
from unittest.mock import patch, MagicMock

import pytest
import requests
from requests.exceptions import HTTPError

from sretoolbox.container import Image

TAG = ('a61f590')
A_SHA = (
  'sha256:bc1ed82a75f2ca160225b8281c50b7074e7678c2a1f61b1fb298e545b455925e')
PARSER_DATA = [
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
        image = Image("quay.io/foo/bar:latest", response_cache={},
                      auth_token="atoken")
        other = image['current']
        assert image.response_cache is other.response_cache
        assert other.auth_token is image.auth_token
        assert other.tag == 'current'


@patch.object(Image, '_request_get', spec=Image)
@patch.object(Image, '_should_cache', spec=Image)
class TestGetManifest:

    def test_empty_cache_should_cache(self, should_cache, getter):
        should_cache.return_value = True
        i = Image(f"quay.io/foo/bar:latest", response_cache={})
        r = requests.Response()
        r.status_code = 200
        r.headers['Docker-Content-Digest'] = 'sha256:asha'
        r._content = b'{"key": "value"}'
        getter.return_value = r
        m = i._get_manifest()
        getter.assert_any_call(
            "https://quay.io/v2/foo/bar/manifests/latest", requests.head
        )
        getter.assert_any_call("https://quay.io/v2/foo/bar/manifests/latest")
        assert m == r
        assert i.response_cache == {"sha256:asha": r}

    def test_empty_cache_should_not_cache(self, should_cache, getter):
        should_cache.return_value = False
        i = Image(f"quay.io/foo/bar:latest", response_cache={})
        r = requests.Response()
        r.status_code = 200
        r.headers['Docker-Content-Digest'] = 'sha256:asha'
        r._content = b'{"key": "value"}'
        getter.return_value = r
        m = i._get_manifest()
        getter.assert_any_call(
            "https://quay.io/v2/foo/bar/manifests/latest", requests.head
        )
        getter.assert_any_call("https://quay.io/v2/foo/bar/manifests/latest")
        assert m == r
        assert i.response_cache == {}

    def test_already_cached(self, should_cache, getter):
        r = requests.Response()
        r.status_code = 200
        r.headers['Docker-Content-Digest'] = 'sha256:asha'
        r._content = b'{"key": "value"}'
        cache = {"sha256:asha": r}
        i = Image(f"quay.io/foo/bar:latest", response_cache=cache)
        getter.return_value = r
        m = i._get_manifest()
        assert m == r
        getter.assert_called_once_with(
            "https://quay.io/v2/foo/bar/manifests/latest", requests.head
        )
        should_cache.assert_not_called()

    def test_no_cache(self, should_cache, getter):
        r = requests.Response()
        r.status_code = 200
        r.headers['Docker-Content-Digest'] = 'sha256:asha'
        r._content = b'{"key": "value"}'
        i = Image(f"quay.io/foo/bar:latest", response_cache=None)
        getter.return_value = r
        m = i._get_manifest()
        assert m == r
        getter.assert_called_once_with(
            "https://quay.io/v2/foo/bar/manifests/latest"
        )
        should_cache.assert_not_called()


@patch.object(Image, '_parse_www_auth')
@patch.object(Image, '_get_auth')
class TestRequestGet:
    def test_username_and_password_ok(self, getauth, parseauth):
        r = requests.Response()
        r.status_code = 200
        method = MagicMock(return_value=r)
        i = Image("quay.io/foo/bar:latest", username="user", password="pass")
        i._request_get.__wrapped__(i, "http://www.google.com", method=method)
        method.assert_called_once()
        c = method.call_args_list[0]

        assert c[0] == ('http://www.google.com', )
        assert 'Authorization' not in c[1]['headers']
        assert c[1]['auth'] == i.auth
        getauth.assert_not_called()
        parseauth.assert_not_called()

    def test_username_and_password_reauthenticate(self, getauth, parseauth):
        r = requests.Response()
        r.status_code = 401
        r.headers['Www-Authenticate'] = 'something something'
        gets = [r]
        r = requests.Response()
        r.status_code = 200
        gets.append(r)
        method = MagicMock(side_effect=gets)
        r = requests.Response()
        r.status_code = 200
        i = Image("quay.io/foo/bar:latest", username="user", password="pass")
        getauth.return_value = "anauthtoken"
        parseauth.return_value = "aparsedauth"
        i._request_get.__wrapped__(i, "http://www.google.com", method=method)
        parseauth.assert_called_once_with('something something')
        assert method.call_count == 2
        assert i.auth_token == 'anauthtoken'

    def test_persistent_failure(self, getauth, parseauth):
        r = requests.Response()
        r.status_code = 401
        r.headers['Www-Authenticate'] = 'something something'
        method = MagicMock(return_value=r)
        r = requests.Response()
        r.status_code = 200
        i = Image("quay.io/foo/bar:latest", username="user", password="pass")
        getauth.return_value = "anauthtoken"
        parseauth.return_value = "aparsedauth"
        with pytest.raises(requests.exceptions.HTTPError):
            i._request_get.__wrapped__(i, "http://www.google.com", method=method)
            getauth.assert_called_once()
            parseauth.assert_called_once()


class TestImageComparision:
    @pytest.fixture
    def v1_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v1-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/v1-image/manifests/latest',
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/v1-image:latest',
        }

    @pytest.fixture
    def v2_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/v2-image/manifests/latest',
            headers={'Content-Type':
                'application/vnd.docker.distribution.manifest.v2+json'},
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/v2-image:latest',
        }

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

    @pytest.fixture
    def oci_image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/oci-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/oci-image/manifests/latest',
            headers={'Content-Type':
                'application/vnd.oci.image.manifest.v1+json'},
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/oci-image:latest',
        }


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
    @pytest.fixture
    def image_mock(self, requests_mock):
        with open('tests/fixtures/manifests/v2-image.json') as f:
            manifest = f.read()

        requests_mock.get(
            'https://registry.io/v2/test/image/manifests/latest',
            headers={
                'Content-Type': \
                    'application/vnd.docker.distribution.manifest.v2+json',
                'Docker-Content-Digest': 'sha256:xxxx',
            },
            content=manifest.encode(),
        )

        return {
            'mock': requests_mock,
            'url': 'docker://registry.io/test/image:latest',
        }

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

    @pytest.fixture
    def image_with_digest_mock(self, requests_mock):
        requests_mock.get(
            'https://registry.io/v2/test/image/manifests/latest',
        )

        return {
            'mock': requests_mock,
            'url': f'docker://registry.io/test/image@{A_SHA}',
        }

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
