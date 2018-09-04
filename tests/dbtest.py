import anytest


def waitReadOneRow(cursor, query):
    return anytest.retryOnFailure(_toReadOneRow(cursor, query), 10, 2)


def readOneRow(cursor, query):
    return _toReadOneRow(cursor, query)()


def _toReadOneRow(cursor, query):
    def read():
        cursor.execute(query)
        rows = cursor.fetchall()
        assert len(rows) == 1, f'Expected 1 but found records={len(rows)} query={query}'
        return rows[0]
    return read


def addColumnNames(row, cursor):
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))
