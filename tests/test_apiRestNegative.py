import pytest
import requests
import anytest
import apitest


START_URL = 'https://some-rest-server'
GET_ENDPOINTS = ['get-only-endpoint1', ]
POST_ENDPOINTS = ['post-endpoint1', ]


def pytest_generate_tests(metafunc):
    def generate(fixname, endpoints):
        envConfig = anytest.readCacheEnvConfig(metafunc)
        apiBaseUrl = envConfig['API_BASE_URL']
        if not apiBaseUrl.lower().startswith(START_URL):
            pytest.skip(f'only runs for API URLs starting with "{START_URL}" while this URL={apiBaseUrl}')
        metafunc.parametrize(fixname, endpoints)

    if 'getEndpoint' in metafunc.fixturenames:
        generate('getEndpoint', GET_ENDPOINTS)
    elif 'postEndpoint' in metafunc.fixturenames:
        generate('postEndpoint', POST_ENDPOINTS)


def makeUrl(apiBaseUrl, endpoint, apiCode):
    return f'{apiBaseUrl}/{endpoint}?code={apiCode}'


def test_getUsingPost_notFound(apiBaseUrl, getEndpoint, apiCode):
    url = makeUrl(apiBaseUrl, getEndpoint, apiCode)
    resp = requests.post(url, {})
    apitest.verifyResponse(resp, isJson=False, respCodeRange=(404, 404), respEmptyOk=True)


def test_postUsingGet_notFound(apiBaseUrl, postEndpoint, apiCode):
    url = makeUrl(apiBaseUrl, postEndpoint, apiCode)
    resp = requests.get(url)
    apitest.verifyResponse(resp, isJson=False, respCodeRange=(404, 404), respEmptyOk=True)


@pytest.mark.parametrize("req", ['', 'TEST', '{}', {}, {'unexpected': 'key'}])
def test_postInvalidJson(apiBaseUrl, postEndpoint, apiCode, req):
    url = makeUrl(apiBaseUrl, postEndpoint, apiCode)
    resp = requests.post(url, json=req)
    apitest.verifyResponse(resp, isJson=True, respCodeRange=(400, 400))