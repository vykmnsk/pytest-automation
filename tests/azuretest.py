import anytest
from os import makedirs, path
from azure.storage.file import FileService


def getCosmosDocById(config, client, docid):
    query = f"SELECT * from c WHERE c.id = '{docid}'"
    return waitReadOneCosmosDoc(config, client, query)


def waitReadOneCosmosDoc(config, client, query):
    return anytest.retryOnFailure(
        _toReadOneCosmosDoc(config, client, query), 10, 2)


def _toReadOneCosmosDoc(config, client, query):
    collection = config['COSMOSDB_COLL_PATH']

    def read():
        resultsIter = client.QueryDocuments(collection, query, { 'enableCrossPartitionQuery': True })
        results = list(resultsIter)
        assert len(results) == 1, f'expected 1 doc in results="{results}"'
        return results[0]
    return read


def downloadStoredFiles(config, accountKey, sourceDir, targetDir):
    fs = FileService(account_name=config['STORAGE_ACCOUNT'], account_key=accountKey)
    storageLoc = config['STORAGE_LOCATION']
    if not path.exists(targetDir):
        makedirs(targetDir)
    print(f'\nFileService: reading files from Azure Storage location="{storageLoc}" directory="{sourceDir}"')
    if not fs.exists(storageLoc, sourceDir):
        return
    dirsFiles = fs.list_directories_and_files(storageLoc, sourceDir)
    fileNames = [df.name for df in dirsFiles if df.name.endswith('.txt') or df.name.endswith('.csv')]
    for fname in fileNames:
        if path.exists(path.join(targetDir, fname)):
            print(f'already got file={fname}')
        else:
            print(f'downloading file={fname}')
            fs.get_file_to_path(storageLoc, sourceDir, fname, path.join(targetDir, fname))


def downloadCacheStoredFiles(metafunc, config, storeDir, targetDir):
    if not hasattr(metafunc.config, 'filesDownloadedTo'):
        storeKey = metafunc.config.getoption('storekey')
        downloadStoredFiles(config, storeKey, storeDir, targetDir)
        metafunc.config.filesDownloadedTo = targetDir
    return metafunc.config.filesDownloadedTo
