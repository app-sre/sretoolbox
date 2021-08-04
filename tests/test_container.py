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
import requests

from unittest.mock import NonCallableMagicMock, MagicMock, patch, call

import pytest

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

    @pytest.mark.parametrize('image, expected_image_url', STR_DATA)
    @patch.object(Image, '_request_get', autospec=True)
    def test_digest(self, get, image, expected_image_url):
        get.return_value = requests.Response()
        get.return_value.headers = {'Docker-Content-Digest': 'sha256:abcd1234'}
        i = Image(image)
        d = i.digest
        if '@' in image:
            # We got the digest when parsing the URL
            assert d == A_SHA
            get.assert_not_called()
        else:
            assert d == 'sha256:abcd1234'
            get.assert_called_once()


@patch.object(requests, 'head')
@patch.object(requests, 'get')
@patch.object(Image, '_parse_www_auth')
@patch.object(Image, '_get_auth')
class TestRequestGetCached:

    def test_all_fine_no_etag(self, get_auth, parse_www_auth, get, head):
        i = Image(
            'docker://docker.io/library/memcached:latest',
            response_cache={}
        )
        rs = requests.Response()
        rs.status_code = 200
        head.return_value = rs
        get.return_value = rs
        assert i._request_get("myurl") == rs
        head.assert_called_once_with(
            "myurl", headers=i.ACCEPT_HEADERS, auth=i.auth
        )
        get.assert_called_once_with(
            "myurl", headers=i.ACCEPT_HEADERS, auth=i.auth
        )
        parse_www_auth.assert_not_called()
        get_auth.assert_not_called()
        assert i.response_cache == {}

    def test_all_fine_etag_add(self, get_auth, parse_www_auth, get, head):
        i = Image(
            'docker://docker.io/library/memcached:latest',
            response_cache={}
        )
        rs = requests.Response()
        rs.status_code = 200
        rs.headers['etag'] = 'anetag'
        rs._content = b'some content'
        rs.headers['content-length'] = len(rs.content)
        get.return_value = rs
        rs = requests.Response()
        rs.status_code = 200
        rs.headers['etag'] = 'anetag'
        head.return_value = rs
        rs = i._request_get("myurl")
        assert rs.content == b'some content'
        head.assert_called_once()
        get.assert_called_once()
        assert i.response_cache == {'anetag': rs}

    def test_all_fine_already_cached(self, get_auth, parse_www_auth, get, head):
        rs = requests.Response()
        rs.status_code = 200
        rs._content = b'some content'
        rs.headers['etag'] = 'anetag'
        rs.headers['content-length'] = len(rs.content)
        cache = {'anetag': rs}
        i = Image(
            'docker://docker.io/library/memcached:latest',
            response_cache=cache
        )
        rs = requests.Response()
        rs.status_code = 200
        rs.headers['etag'] = 'anetag'
        get.side_effect = Exception("Shouldn't call me")
        head.return_value = rs
        rs = i._request_get("myurl")
        get.assert_not_called()
        assert rs.content == b'some content'
        head.assert_called_once()
        get.assert_not_called()



class TestShouldCache:
    @staticmethod
    def test_should_cache_small():
        r = requests.Response()
        r.headers['etag'] = 'abcdefg'
        r.headers['content-length'] = '42'
        r.status_code = 200
        assert Image._should_cache(r)

    @staticmethod
    def test_should_cache_no_etag():
        r = requests.Response()
        r.headers['content-length'] = 42
        r.status_code = 200
        assert not Image._should_cache(r)

    @staticmethod
    def test_should_cache_humongous():
        r = requests.Response()
        r.headers['etag'] = 'abcd12345'
        r.headers['content-length'] = str(10**10)
        r.status_code = 200
        assert not Image._should_cache(r)

    @staticmethod
    def test_should_cache_no_size():
        r = requests.Response()
        r.headers['etag'] = 'abcd12345'
        r.status_code = 200
        assert not Image._should_cache(r)

    @staticmethod
    def test_should_cache_ko():
        r = requests.Response()
        r.headers['etag'] = 'abcd12345'
        r.headers['content-length'] = 42
        r.status_code = 400
        assert not Image._should_cache(r)


@patch.object(requests, 'get')
class TestRequestsGet:
    @staticmethod
    def request_should_not_cache(get):
        i = Image('docker://docker.io/library/memcached:latest')
        r = requests.Response()
        # We don't want to test all the decorators
        assert i.__wrapped__.__wrapped__('www.google.com') == r
        get.assert_called_once_with('www.google.com')
        assert not i.response_cache

    @staticmethod
    def request_should_cache(get):
        i = Image('docker://docker.io/library/memcached:latest')
        r = requests.Response()
        r.headers['etag'] = 'abcd12345'
        r.headers['content-length'] = 42
        assert i.__wrapped__.__wrapped__('www.google.com') == r
        get.assert_called_once_with('www.google.com')
        assert i.response_cache['abcd12345'] == r
