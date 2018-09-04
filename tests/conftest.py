import pytest
import yaml
import pyodbc
import pydocumentdb.document_client as docDbClient
from azure.storage.file import FileService
from ftplib import FTP
import anytest
import struct


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="local",
        help="provide SUT environment to test: [local | nprod]")
    parser.addoption("--apicode", action="store",
        help="provide key code for API")
    parser.addoption("--cosmoskey", action="store",
        help="provide master key code for Azure Cosmos DB")
    parser.addoption("--storekey", action="store",
        help="provide storage account key for Azure File Service")
    parser.addoption("--dbuid", action="store",
        help="provide UID for SQLServer")
    parser.addoption("--dbpwd", action="store",
        help="provide PWD for SQLServer")
    parser.addoption("--dbinfo-uid", action="store",
        help="provide UID for SQLServer")
    parser.addoption("--dbinfo-pwd", action="store",
        help="provide PWD for SQLServer")
    parser.addoption("--ftpuid", action="store",
        help="provide User for FTP server")
    parser.addoption("--ftppwd", action="store",
        help="provide Password for FTP server")


def readVerifyOptVal(request, opt, verify=True):
    val = request.config.getoption(opt)
    if verify:
        assert val, f'pytest: {opt} custom option is required'
    return val


@pytest.fixture(scope="module", autouse=True)
def sessionRun(envName):
    yield
    print(f"\n\nSuT Env: {envName}")


@pytest.fixture(scope='session')
def envName(request):
    return readVerifyOptVal(request, "--env", verify=False)


@pytest.fixture(scope='session')
def config(envName):
    config = yaml.load(open('config.yml'))
    envConfig = config['env'][envName.lower()]
    return envConfig


@pytest.fixture(scope='session')
def apiBaseUrl(config, envName):
    baseUrl = config['API_BASE_URL']
    if baseUrl.endswith('/'):
        return baseUrl[:-1]
    else:
        return baseUrl


@pytest.fixture(scope='session')
def apiCode(request, envName):
    anytest.ensureSupportedEnv(envName, ['nprod-azure', ])
    return readVerifyOptVal(request, "--apicode")


@pytest.fixture(scope='session')
def dbConn(request, config):
    dbUid = readVerifyOptVal(request, "--dbuid")
    dbPwd = readVerifyOptVal(request, "--dbpwd")
    connStr = config['DB_CONN'] + f' UID={dbUid}; PWD={dbPwd};'
    print(f'connStr={connStr}')
    conn = pyodbc.connect(connStr)
    conn.add_output_converter(-155, handle_datetimeoffset)
    cursor = conn.cursor()
    prefix = config.get('DB_PREFIX', '')
    return cursor, prefix


def handle_datetimeoffset(dto_value):
    # ref: https://github.com/mkleehammer/pyodbc/issues/134#issuecomment-281739794
    tup = struct.unpack("<6hI2h", dto_value)  # e.g., (2017, 3, 16, 10, 35, 18, 0, -6, 0)
    tweaked = [tup[i] // 100 if i == 6 else tup[i] for i in range(len(tup))]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:07d} {:+03d}:{:02d}".format(*tweaked)


@pytest.fixture(scope='session')
def cosmosClient(request, config):
    key = readVerifyOptVal(request, "--cosmoskey")
    return docDbClient.DocumentClient(config['COSMOSDB_URL'], {'masterKey': key})


@pytest.fixture(scope='session')
def ftp(request, config, envName):
    anytest.ensureSupportedEnv(envName, ['local'])
    usr = readVerifyOptVal(request, "--ftpuid")
    pwd = readVerifyOptVal(request, "--ftppwd")
    ftp = FTP()
    ftp.connect(config['FTP_HOST'], config['FTP_PORT'])
    ftp.login(usr, pwd)
    yield ftp
    ftp.quit()


@pytest.fixture(scope='session')
def fileService(request, config, envName):
    anytest.ensureSupportedEnv(envName, ['nprod-azure', 'nprod-outside'])
    key = readVerifyOptVal(request, "--storekey")
    return FileService(account_name=config['STORAGE_ACCOUNT'], account_key=key)

