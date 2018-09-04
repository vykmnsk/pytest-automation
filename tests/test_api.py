import pytest
import requests
import anytest
import apitest


ENDPOINT = 'posts'


@pytest.fixture(scope='module')
def apiUrl(apiBaseUrl, envName):
    anytest.ensureSupportedEnv(envName, ['local'])
    return f'{apiBaseUrl}/{ENDPOINT}'


def test_GET(config, apiUrl):
    resp = requests.get(apiUrl)
    apitest.verifyResponse(resp, isJson=True, respCodeRange=(200, 299), respEmptyOk=True)


@pytest.mark.parametrize("req", ['TEST'])
def test_POST(config, apiUrl, req):
    resp = requests.post(apiUrl, req)
    apitest.verifyResponse(resp, isJson=False, respCodeRange=(200, 299))
