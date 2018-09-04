import pytest
import dbtest


@pytest.mark.parametrize("tableName", ['Table1', ])
def test_sqlDBTableNotEmpty(dbConn, tableName):
    cursor, prefix = dbConn
    query = f'SELECT Top 1 * FROM {tableName}'
    dbtest.readOneRow(cursor, query)


def test_cosmosDBCollectionExists(config, cosmosClient):
    sql = f"SELECT * from c where c.id = 'i-dont-exist'"
    resultsIter = cosmosClient.QueryDocuments(config['COSMOSDB_COLL_PATH'], sql)
    results = list(resultsIter)
    assert len(results) == 0
