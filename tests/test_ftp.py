import pytest


@pytest.mark.parametrize('remoteDirKey', ['FTP_REMOTE_DIR',])
def test_listRemoteFiles(ftp, config, remoteDirKey):
    remoteDir = config[remoteDirKey]
    ftp.cwd(remoteDir)
    print('\n--FTP remote LIST start: --\n')
    ftp.retrlines('LIST')
    print('\n--FTP remote LIST end: --\n')
