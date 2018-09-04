import pytest
import requests
import anytest
import apitest


GET_ENDPOINT = 'GetStatus'
SET_ENDPOINT = 'SetStatus'


@pytest.fixture(scope='module')
def getStatusUrl(apiBaseUrl, apiCode):
    return f'{apiBaseUrl}/{GET_ENDPOINT}?code={apiCode}'


@pytest.fixture(scope='module')
def setStatusUrl(apiBaseUrl, apiCode):
    return f'{apiBaseUrl}/{SET_ENDPOINT}?code={apiCode}'


def test_getStatus(getStatusUrl):
    resp = requests.get(getStatusUrl)
    jresp = apitest.verifyResponse(resp, isJson=True, respCodeRange=(200, 299))
    expectedFields = [
        'Status',
        'CreatedAt',
        'CreatedBy',
        'Reason',
        # comes from CosmosDB
        'DataSetType',
        '_ts',
    ]
    print(f"\ngot status={jresp}")
    assert set(expectedFields) == set(jresp.keys()), f'resp={resp.text}'


@pytest.fixture(scope='function')
def apiStatus(getStatusUrl, setStatusUrl):
    # read, remember current status
    resp = requests.get(getStatusUrl)
    jresp = apitest.verifyResponse(resp, isJson=True, respCodeRange=(200, 299))
    beforeStatus = jresp['Status']
    restoreData = {
        'Status': beforeStatus,
        'CreatedBy': anytest.ID,
        'Reason': 'Restore after test'
    }
    yield beforeStatus

    setStatus(setStatusUrl, restoreData, 'Restore status back')


def test_setStatusToggle(apiStatus, getStatusUrl, setStatusUrl):
    newStatus = not apiStatus
    creator = anytest.ID
    statusData = {
        'Status': newStatus,
        'CreatedBy': creator,
        'Reason': 'Test'
    }
    jresp = setStatus(setStatusUrl, statusData, 'Change status')

    # verify new status in response
    assert jresp['Status'] is newStatus, f'resp={jresp}'
    assert jresp['CreatedBy'] == creator, f'resp={jresp}'

    # verify new status in a separate API call
    respGet = requests.get(getStatusUrl)
    jrespGet = apitest.verifyResponse(respGet, isJson=True, respCodeRange=(200, 299))
    assert jrespGet['Status'] is newStatus, f'respGet={jrespGet}'
    assert jrespGet['CreatedBy'] == creator, f'respGet={jrespGet}'


def setStatus(setStatusUrl, statusData, msg='Set status'):
    print(f'\n{msg}: request={statusData}')
    resp = requests.post(setStatusUrl, json=statusData)
    # print(f"got resp={resp.status_code}: {resp.text}")
    return apitest.verifyResponse(resp, isJson=True, respCodeRange=(200, 299))
