import pytest
import time
import yaml
import os
import random
import inspect


ID = 'pytest'


def ensureSupportedEnv(thisEnv, supportedEnvs, why=''):
    if (thisEnv.lower() not in supportedEnvs):
        caller = inspect.stack()[1][3]
        if why:
            why = " - " + why
        pytest.skip(f'{caller}: only {supportedEnvs} environments supported but not env={thisEnv}' + why)


def retryOnFailure(func, maxTries, sleepSeconds):
    for i in range(1, maxTries + 1):
        if i > 1:
            print("start sleep {i}")
            time.sleep(sleepSeconds)
            print("end sleep {i}")
        try:
            return func()
        except AssertionError as err:
            print(f'Tried {i} - {err}')

    pytest.fail(f"Exhausted {maxTries} attempts for previous errors")


def readCacheEnvConfig(metafunc):
    if hasattr(metafunc.config, 'envConfig'):
        envConfig = metafunc.config.envConfig
    else:
        envName = metafunc.config.getoption('env')
        envConfig = loadEnvConfig(envName)
        metafunc.config.envConfig = envConfig
    return envConfig


def readCacheTextFiles(metafunc, dirPath):
    if hasattr(metafunc.config, 'fileContents'):
        fileContents = metafunc.config.fileContents
    else:
        fileContents = [(f, readFileLines(os.path.join(dirPath, f))) for f in findTextFiles(dirPath)]
        metafunc.config.fileContents = fileContents
    return fileContents


def loadEnvConfig(name):
    configAll = yaml.load(open('config.yml'))
    return configAll['env'][name]


def findOneMatchingRoot(srcFile, otherFiles):
    rootName = os.path.splitext(srcFile)[0]
    matches = [f for f in otherFiles if f.startswith(rootName.upper())]
    assert len(matches) == 1, f'expected to find one file starting with "{rootName}" in files={otherFiles}'
    return matches[0]


def findTextFiles(directory):
    def isTextFile(fpath):
        return os.path.isfile(fpath) and fpath.endswith('.txt')

    fnames = [f for f in os.listdir(directory) if isTextFile(os.path.join(directory, f))]
    return fnames


def readFileLines(fpath):
    with open(fpath) as f:
        print(f"reading {fpath}")
        fileLines = f.read().splitlines()
    return fileLines


def randomDigits(count):
    digits = random.sample(range(10), count)
    return ''.join(map(str, digits))
