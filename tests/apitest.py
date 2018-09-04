import pytest
import json
import os.path
import requests


def postJson(url, data, msg='POST ', expectError=False):
    # print(f'\n{msg}: request={data}')
    resp = requests.post(url, json=data)
    # print(f"got resp={resp._code}: {resp.text}")
    if expectError:
        expCodeRange = (400, 499)
    else:
        expCodeRange = (200, 299)
    return verifyResponse(resp, isJson=True, respCodeRange=expCodeRange)


def verifyResponse(resp, errCtx='', isJson=True, respCodeRange=(200, 300), respEmptyOk=False):
    errCtx = errCtx + f'response={resp.text[0:1000]}'
    codeMin, codeMax = respCodeRange
    assert codeMin <= resp.status_code <= codeMax, \
        f'response code={resp.status_code} out of range={respCodeRange} {errCtx}'
    if not respEmptyOk:
        assert resp.content, f'empty response {errCtx}'
    if not isJson:
        result = resp.content
    else:
        expectedContTypes = ['application/json', 'application/json; charset=utf-8', 'text/json; charset=utf-8']
        assert resp.headers['Content-Type'].lower() in expectedContTypes, errCtx
        try:
            result = json.loads(resp.content)
        except ValueError:
            pytest.fail(f'response is not JSON: {errCtx}')

    return result


def readJsonFromFile(path, fname):
    fpath = os.path.join(path, fname)
    with open(fpath) as f:
        content = f.read()

    return json.loads(content)
