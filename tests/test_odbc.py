import pytest
import anytest


def test_deleteInsertSelect(envName, dbConn):
    anytest.ensureSupportedEnv(envName, ['dev-local'])

    if (envName.lower() != 'dev-local'):
        pytest.skip(f'only "dev-local" environment supported but not env={envName}')
    cursor, _ = dbConn
    table = 'Table1'
    dbColumn = 'name'
    expectedValue = 'Yuri'

    cursor.execute(f'DELETE FROM {table}')
    cursor.execute(f"INSERT INTO {table}({dbColumn}) VALUES('{expectedValue}')")
    cursor.execute(f'SELECT * FROM {table}')
    rows = cursor.fetchall()

    assert len(rows) == 1
    autoId, name = rows[0]
    assert autoId > 0
    assert name == expectedValue
