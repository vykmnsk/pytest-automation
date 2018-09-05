import pytest
import re
import os
import datetime
import anytest
import azuretest
import dbtest


SECTION_PREFIX_START = 'START OF '
SECTION_PREFIX_END = 'END OF '
STORAGE_PREFIX = 'STORAGE_LOCATION='
ENERGY_TYPE = 'ENERGY'
SERVICE_TYPES = {
    'RAISE6SEC':  ['BATTGENID'],
    'RAISE60SEC': ['BATTGENID'],
    'RAISE5MIN':  ['BATTGENID'],
    ENERGY_TYPE:  ['BATTGENID', 'BATTLOADID'],
    'LOWER6SEC':  ['BATTLOADID'],
    'LOWER60SEC': ['BATTLOADID'],
    'LOWER5MIN':  ['BATTLOADID'],
}
BID_REASON_CODES = [
    'COMMS FAULT',
    'BATTERY IN ISLANDING STATE',
    'LOCAL LIMIT CHANGE',
    'LOCAL LIMIT CHANGE',
    'CHANGE IN LOCAL MIN REQUIREMENT',
    'SOC CHANGE',
    'CHANGE IN AEMO DISPATCH 30/5 SETTLEMENT',
    '010 UNEXPECTED/PLANT LIMITS',
]


def pytest_generate_tests(metafunc):
    if ('bidFile' in metafunc.fixturenames and
            'lines' in metafunc.fixturenames):
        envConfig = anytest.readCacheEnvConfig(metafunc)

        configPath = envConfig['BID_FILES_DIR']
        if configPath.startswith(STORAGE_PREFIX):
            storeDir = extractStoreDir(configPath, STORAGE_PREFIX)
            fromPath = azuretest.downloadCacheStoredFiles(
                metafunc, envConfig, storeDir, localPath(storeDir))
        else:
            fromPath = configPath

        fnamesLines = anytest.readCacheTextFiles(metafunc, fromPath)
        metafunc.parametrize("bidFile,lines", fnamesLines)


def extractStoreDir(configPath, storagePrefix):
    storeTo = configPath[len(storagePrefix):]
    assert storeTo, f'storage download dir is not conigured'
    if storeTo.upper() == 'TODAY':
        return datetime.datetime.today().strftime('%Y/%m/%d')
    else:
        return storeTo


def localPath(storeDir):
    return os.path.join('tmp', storeDir)


def extractRootName(fname):
    name = os.path.splitext(fname)[0]
    parts = name.split('_')
    return '_'.join(parts[:4])


def test_gotAEMOResponse(envName, bidFile, lines, config):
    if 'NOT_SUPPORTED' == config['STORAGE_LOCATION'].upper():
        pytest.skip(f'only runs when Azure Storage is available')
    configPath = config['BID_FILES_DIR']
    storeDir = extractStoreDir(configPath, STORAGE_PREFIX)

    def isResponse(fname):
        return 'ACK' in fname or 'CPT' in fname

    allResponses = [f for f in os.listdir(localPath(storeDir)) if isResponse(f)]
    anytest.findOneMatchingRoot(bidFile, allResponses)


def test_filename(bidFile, lines):
    errCtx = f'file={bidFile}: filename '
    assert len(bidFile) <= 40, errCtx + 'is too long'

    name = os.path.splitext(bidFile)[0]
    nameParts = name.split('_')
    assert len(nameParts) == 4, errCtx + 'must have 4 parts'

    participant, bidType, dateStr, version = nameParts
    assert len(participant) > 0, errCtx + 'must contain a participant'
    assert 'OFFER' in bidType, errCtx + 'must contain "OFFER"'
    assert version.isnumeric() and len(version) == 3, errCtx + 'must have 3 digit version'
    startVer = 2
    assert int(version) >= startVer, errCtx + f'version must start with {startVer} for auto bids'
    verifyDate(dateStr, "%Y%m%d", errCtx + 'part')


def test_firstLine(bidFile, lines):
    errCtx = f'file={bidFile}: first line '
    assert len(lines) > 0, errCtx + ' is empty'
    line1 = str(lines[0])
    assert isBidComment(line1), errCtx


def test_sectionsPresent(bidFile, lines):
    errCtx = f'file={bidFile}: sections: '
    stack = []
    sectionsFound = []
    for line in lines:
        if line.startswith(SECTION_PREFIX_END):
            last = stack.pop(0)
            _, suffixStart = last.split(SECTION_PREFIX_START)
            _, suffixEnd = line.split(SECTION_PREFIX_END)
            assert suffixStart == suffixEnd, errCtx + 'expected "{last}" to match "{line}"'
            sectionsFound.append(suffixStart)

        elif line.startswith(SECTION_PREFIX_START):
            stack.insert(0, line)
    assert len(stack) == 0, errCtx + 'unclosed sections {stack}'
    sectionsExpected = [
        'BID FILE',
        'BID',
        'BAND AVAILABILITY',
        'DISPATCHABLE UNIT',
        'FAST START PROFILE',
        'PRICE BANDS',
        'UNIT LIMITS',
    ]
    assert set(sectionsExpected) == set(sectionsFound), errCtx + 'expected sections set'


def test_section_BID_FILE(bidFile, lines):
    secName = 'BID FILE'
    errCtx = f'file={bidFile} section={secName}: '
    fields = {
        'To': verifyEquals('AEMO'),
        'From': verifyEquals('BATTSITE'),
        'Issued on': verifyDateFmt('%d/%m/%Y %H:%M'),
        'Version No': verifyDigits(1, 3),
        'Authorised by': verifyEquals('AUTOBID'),
    }
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) == 1, errCtx + f'expected only 1 {secName} section but found {len(sections)}'

    secLines = sections[0]
    verifyFields(secLines, fields, errCtx)

    sectionsOfBid = readSectionsWithName(bidFile, lines, 'BID')
    assert len(sectionsOfBid) > 0, errCtx + f'expected 1 or more BID sections but found {len(sectionsOfBid)}'

    fieldName = 'Version No'
    nameNoExt = os.path.splitext(bidFile)[0]
    verFName = nameNoExt.split('_')[-1]
    verInside = readField(secLines, fieldName, errCtx)
    assert int(verInside) == int(verFName), errCtx + f'field={fieldName}: does not match Filename'


def test_section_BID(bidFile, lines):
    secName = 'BID'
    errCtx = f'file={bidFile} section={secName}: '
    fields = {
        'Service Type': verifyServiceType(),
        'Trading Date': verifyDateFmt('%d/%m/%Y')
    }
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) >= 1, errCtx + f'1 or more {secName} sections but found {len(sections)}'
    for secLines in sections:
        verifyFields(secLines, fields, errCtx)
        subSecNames = findAllSectionNames(secLines)
        minSubSecNames = ['DISPATCHABLE UNIT']
        assert set(minSubSecNames).issubset(set(subSecNames)), \
           errCtx + f'expected to find at least these sub-sections={minSubSecNames}'


def test_DUID_serviceType(bidFile, lines, envName):
    parentSecName = 'BID'
    secName = 'DISPATCHABLE UNIT'
    errCtx = f'file={bidFile} section={secName}: '
    parentSections = readSectionsWithName(bidFile, lines, parentSecName)
    for parentSecLines in parentSections:
        serviceType = readField(parentSecLines, 'Service Type', f'file={bidFile} section={parentSecName}: ')
        sections = readSectionsWithName(bidFile, parentSecLines, secName)
        for secLines in sections:
            duid = readField(secLines, 'Dispatchable Unit Id', errCtx)
            # print(f'serviceType={serviceType} duid={duid}')
            assert duid in SERVICE_TYPES[serviceType], errCtx + \
                f'duid={duid} is not registered for serviceType={serviceType}'


def test_section_DISPATCHABLE_UNIT_mandatoryFields(bidFile, lines):
    secName = 'DISPATCHABLE UNIT'
    errCtx = f'file={bidFile} section={secName}: '
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) >= 1, errCtx + f'1 or more {secName} sections but found {len(sections)}'

    fields = {
        'Dispatchable Unit Id': verifyAlphaNumeric(),
        'Reason': verifyReasonFmt()
    }
    for secLines in sections:
        verifyFields(secLines, fields, errCtx)
        subSecNames = findAllSectionNames(secLines)
        minSubSecNames = {'UNIT LIMITS', 'PRICE BANDS', 'BAND AVAILABILITY'}
        assert minSubSecNames.issubset(set(subSecNames)), \
           errCtx + f'expected to find at least these sub-sections={minSubSecNames} in {subSecNames}'


def test_section_DISPATCHABLE_UNIT_optionalFields(bidFile, lines):
    secName = 'DISPATCHABLE UNIT'
    errCtx = f'file={bidFile} section={secName}: '
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) >= 1, errCtx + f'1 or more {secName} sections but found {len(sections)}'

    for secLines in sections:
        duid = readField(secLines, 'Dispatchable Unit Id', errCtx)
        if 'BATTLOADID' == duid:  # Load DUID
            fieldsOptional = {
                'Daily Energy Constraint': verifyPosInt(),
                'MR Offer Price Scaling Factor': verifyEquals('')
            }
        else:
            fieldsOptional = {
                'Daily Energy Constraint': verifyPosInt(),
                'MR Offer Price Scaling Factor': verifyDecimals(4)
            }
        verifyFields(secLines, fieldsOptional, errCtx + f'DUID={duid} ', optional=True)
        subSecNames = findAllSectionNames(secLines)
        maxSubSecNames = {'UNIT LIMITS', 'PRICE BANDS', 'BAND AVAILABILITY', 'FAST START PROFILE'}
        assert set(subSecNames).issubset(maxSubSecNames), \
            f'file={bidFile} section={secName} expected to find sub-sections within={maxSubSecNames}'


def extractSettleDate(config):
    SQL_UTC6 = 'CAST(dateadd(hh, 6, GETUTCDATE()) AS date)'
    configPath = config['BID_FILES_DIR']
    if configPath.startswith(STORAGE_PREFIX):
        storeTo = configPath[len(STORAGE_PREFIX):]
        assert storeTo, f'storage download dir is not conigured'
        if storeTo.upper() == 'TODAY':
            settleDate = SQL_UTC6
        else:
            settleDate = "'" + storeTo.replace("/", "-") + "'"
    else:
        settleDate = SQL_UTC6
        print("BID_FILES_DIR has no date, running with MR Factor for today")
    return settleDate


def test_section_FAST_START_PROFILE(bidFile, lines):
    secName = 'FAST START PROFILE'
    errCtx = f'file={bidFile} section={secName}: '
    fields = {
        'Fast Start Min Load': verifyPosInt(),
        'FS Time at Zero (T1)': verifyPosInt(),
        'FS Time to Min Load (T2)': verifyPosInt(),
        'FS Time at Min Load (T3)': verifyPosInt(),
        'FS Time to zero (T4)': verifyPosInt(),
    }
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) >= 1, errCtx + f'1 or more {secName} section but found {len(sections)}'
    for secLines in sections:
        verifyFields(secLines, fields, errCtx)


def test_section_PRICE_BANDS(bidFile, lines):
    secName = 'PRICE BANDS'
    errCtx = f'file={bidFile} section={secName}: '
    expectedHeaders = ['Price Band', 'PB1', 'PB2', 'PB3', 'PB4', 'PB5', 'PB6', 'PB7', 'PB8', 'PB9', 'PB10']
    headerRowPrefix = expectedHeaders[0] + ' '
    dataRowPrefix = 'Price($/MWh)'
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) >= 1, errCtx + f'expected 1 or more {secName} sections but found {len(sections)}'

    for secLines in sections:
        headerLines = [ln for ln in secLines if ln.startswith(headerRowPrefix)]
        assert len(headerLines) == 1, \
            errCtx + 'expected 1 table header "{headerRowPrefix}" but found {len(headerLines)}'

        assert expectedHeaders == re.split(r'\s\s+', headerLines[0]), errCtx + 'expected column headers'

        dataLines = [ln for ln in secLines if ln.startswith(dataRowPrefix)]
        assert len(dataLines) == 1, \
            errCtx + 'expected 1 Price Band table data row but found {len(dataLines)}'

        pbValues = [v.strip() for v in dataLines[0].split()][1:]
        assert len(pbValues) == 10, errCtx + 'number of columns'

        verifyMoney = verifyDecimals(2, negativeOk=True)
        for v in pbValues:
            verifyMoney(v, errCtx + 'Price Band price=')


def test_section_BAND_AVAILABILITY(bidFile, lines):
    secName = 'BAND AVAILABILITY'
    errCtx = f'file={bidFile} section={secName}: '
    headerRowPrefix1 = 'Trading'
    expectedHeaders = ['Interval', 'PB1', 'PB2', 'PB3', 'PB4', 'PB5', 'PB6', 'PB7', 'PB8', 'PB9', 'PB10']
    expectedDataRowsCount = 48
    headerRowPrefix2 = expectedHeaders[0] + ' '
    sections = readSectionsWithName(bidFile, lines, secName)
    assert len(sections) >= 1, errCtx + f'expected 1 or more {secName} sections but found {len(sections)}'

    for secLines in sections:
        for headerRowPrefix in [headerRowPrefix1, headerRowPrefix2]:
            headerLines = [ln for ln in secLines if ln.startswith(headerRowPrefix)]
            assert len(headerLines) == 1, \
                errCtx + f'expected 1 table header "{headerRowPrefix}" but found {len(headerLines)}'
        assert expectedHeaders == headerLines[0].split(), errCtx + f'expected column headers'

        dataLines = filterLines(secLines, headerRowPrefix1, headerRowPrefix2)
        assert len(dataLines) == expectedDataRowsCount, \
            errCtx + f'expected {expectedDataRowsCount} table data rows but found {len(dataLines)}'

        assertTradeIntervals(readColumn(0, dataLines), errCtx)
        for dline in dataLines:
            vals = dline.split()
            assert len(expectedHeaders) == len(vals), errCtx + f'wrong values count in data row {dline}'
            for v in vals[1:]:
                assertPosInt(v, errCtx + f'value in {vals}')


def test_section_UNIT_LIMITS(bidFile, lines):
    secName = 'UNIT LIMITS'
    parentSecName ='DISPATCHABLE UNIT'
    grandParentSecName = 'BID'

    errCtxGrand = f'file={bidFile} section={grandParentSecName}'
    grandParentSections = readSectionsWithName(bidFile, lines, grandParentSecName)
    for grandParentSecLines in grandParentSections:
        serviceType = readField(grandParentSecLines, 'Service Type', f'file={bidFile} section={grandParentSecName}')
        if serviceType == ENERGY_TYPE:
            expectedHeaders = [
                ('Trading', 'Interval'),
                ('Max Availability', 'Loading'),
                ('ROC-UP', ''),
                ('ROC-DOWN', ''),
                ('Fixed', ''),
                ('PASA Availability', ''),
                ('MR Capacity', '')]
        elif serviceType in SERVICE_TYPES.keys():
            expectedHeaders = [
                ('Trading', 'Interval'),
                ('Max Availability', 'Loading'),
                ('Enablement', 'Min'),
                ('Low', 'Break Pt'),
                ('Enablement', 'Max'),
                ('High', 'Break Pt')]
        else:
            pytest.fail(errCtxGrand + ': unknown service type={serviceType}')

        headerRow1Prefix = expectedHeaders[0][0] + ' '
        headerRow2Prefix = expectedHeaders[0][1] + ' '
        expectedDataRowsCount = 48

        errCtxParent = errCtxGrand + f'/{parentSecName}'
        parentSections = readSectionsWithName(bidFile, grandParentSecLines, parentSecName)
        for parentSecLines in parentSections:
            mrOffer = readField (parentSecLines, 'MR Offer Price Scaling Factor', errCtxParent, optional=True)
            sections = readSectionsWithName(bidFile, parentSecLines, secName)
            errCtx = errCtxParent + f'/{secName}'
            assert len(sections) >= 1, f'file={bidFile}: expected 1 or more {secName} section in {grandParentSecName} but found {len(sections)}'

            for secLines in sections:
                header1Lines = [ln for ln in secLines if ln.startswith(headerRow1Prefix)]
                assert len(header1Lines) == 1, \
                        errCtx + f'expected 1 table header starting with "{headerRow1Prefix}" but found {len(header1Lines)}'
                header2Lines = [ln for ln in secLines if ln.startswith(headerRow2Prefix)]
                assert len(header2Lines) == 1, \
                        errCtx + f'expected 1 table header starting with "{headerRow2Prefix}" but found {len(header2Lines)}'
                colPositions = findColumnPositions(header1Lines[0], expectedHeaders)
                assert all([hp[1] >= 0 for hp in colPositions]), \
                    errCtx + f'some column headers not found {colPositions}'

                dataLines = filterLines(secLines, headerRow1Prefix, headerRow2Prefix)
                assert len(dataLines) == expectedDataRowsCount, \
                    f'file={bidFile} section={secName}: expected {expectedDataRowsCount} table data rows but found {len(dataLines)}'

                tradeIntervals = []
                errors = []
                for dline in dataLines:
                    row = readValuesByColumnWidths(dline, colPositions)
                    tradeInterval = row[('Trading', 'Interval')]
                    errCtxRow = f'row={tradeInterval} '
                    tradeIntervals.append(tradeInterval)

                    if serviceType == ENERGY_TYPE:
                        for colName in [
                                ('Max Availability', 'Loading'),
                                ('ROC-UP', ''),
                                ('ROC-DOWN', ''),
                                ('PASA Availability', ''), ]:
                            checkPosInt(row[colName], errors, errCtxRow + f' column={colName}')
                        pasaAvail = row[('PASA Availability', '')]
                        maxAvail = row[('Max Availability', 'Loading')]

                        if pasaAvail.isdigit() and maxAvail.isdigit() and int(pasaAvail) < int(maxAvail):
                            errors.append(errCtxRow +
                                f"'PASA Availability'={pasaAvail} should be no less than 'Max Avail. Loading'={maxAvail}")

                        fixed = row[('Fixed', '')]
                        if fixed:
                            checkPosInt(fixed, errors, errCtxRow + f'column=Fixed')
                            if fixed.isdigit() and int(fixed) > int(maxAvail):
                                errors.append(errCtxRow +
                                    f'Fixed={fixed} cannot be greater than "Max Availability Loading"={maxAvail}')

                        mrCapacity = row[('MR Capacity', '')]
                        if mrOffer:
                            checkPosInt(mrCapacity, errors, errCtxRow + f'column="MR Capacity"')
                        else:
                            if mrCapacity:
                                errors.append(errCtxRow + f'MR Capacity={mrCapacity} expected black if MR Offer is blank')

                        if mrCapacity.isdigit() and int(mrCapacity) > 0:
                            if not fixed == '0' or fixed == '':
                                errors.append(errCtxRow +
                                    f'If the MR Capacity={mrCapacity} is an integer > 0 then Fixed={fixed} must be zero or blank')

                        if mrCapacity.isdigit() and maxAvail.isdigit() and int(mrCapacity) > int(maxAvail):
                            errors.append(errCtxRow +
                                f'"MR Capacity"={mrCapacity} should not be greater than "Max Availability Loading"={maxAvail}.')

                        rocDown = row[('ROC-DOWN', '')]
                        if mrCapacity.isdigit() and int(mrCapacity) > int(rocDown) * 30:
                            errors.append(errCtxRow +
                                f'"MR Capacity"={mrCapacity} cannot be greater than 30 times ROC-DOWN={rocDown}')

                    elif serviceType in SERVICE_TYPES.keys():
                        for colName in [
                                ('Trading', 'Interval'),
                                ('Max Availability', 'Loading'),
                                ('Enablement', 'Min'),
                                ('Low', 'Break Pt'),
                                ('Enablement', 'Max'),
                                ('High', 'Break Pt')]:
                            checkPosInt(row[colName], errors, errCtxRow + f' column={colName}')

                        highBreak = row[('High', 'Break Pt')]
                        enableMax = row[('Enablement', 'Max')]
                        if True and highBreak.isdigit() and enableMax.isdigit() and int(highBreak) > int(enableMax):
                            errors.append(errCtxRow +
                                f"'High Break Pt'={highBreak} must not exceed Enablement Max={enableMax}")

                    else:
                        pytest.fail(f'file={bidFile} section={grandParentSecName}: unknown service type={serviceType}')

                assertTradeIntervals(tradeIntervals, errCtx)
                assert not errors, f'{errCtx} errors found: {errors}'


# --- Helper functions ---


def isBidComment(line):
    return line.startswith('-') or len(line) == 0 or line.isspace()


def filterLines(lines, exceptStarts1, exceptStarts2):
    return [ln for ln in lines if not (
        isBidComment(ln) or
        ln.startswith(exceptStarts1) or
        ln.startswith(exceptStarts2))]


def readSectionsWithName(fname, lines, name):
    readBody = False
    section = []
    allSections = []
    for line in lines:
        if isBidComment(line):
            pass
        elif line == SECTION_PREFIX_START + name:
            line = None  # to skip reading section header
            readBody = True
        elif line == SECTION_PREFIX_END + name:
            readBody = False
            allSections.append(section)
            section = []
        elif readBody and line:
            section.append(line)
        else:
            # dbg# print('skipping: ' + line)
            pass
    return allSections


def findAllSectionNames(lines):
    return [line.split(SECTION_PREFIX_START)[1] for line in lines if line.startswith(SECTION_PREFIX_START)]


def readField(lines, name, errCtx, optional=False):
    label = name + ":"
    matches = [line for line in lines if line.startswith(label)]
    if optional and len(matches) == 0:
        return None
    assert len(matches) == 1, errCtx + f': expected exactly 1 field="{name}" but found {len(matches)}'
    fieldLine = matches[0]
    _, value = fieldLine.split(label)
    return value.strip()


def findColumnPositions(line, headers):
    positions = []
    idx = 0
    for header in headers:
        idx = line.find(header[0], idx)
        positions.append((header, idx))
    return positions


def readValuesByColumnWidths(line, headers):
    values = {}
    prevHeader, prevIdx = headers[0]
    for header, idx in headers[1:]:
        value = line[prevIdx:idx].strip()
        values[prevHeader] = value
        prevIdx = idx
        prevHeader = header
    valueLast = line[idx:].strip()
    values[header] = valueLast
    return values


def readColumn(colIdx, lines):
    rows = [line.split() for line in lines]  # space delimeted
    return [row[colIdx] for row in rows]


# --- Verify helpers ---

def verifyFields(secLines, fieldsVals, errCtx, optional=False):
    for name, verify in fieldsVals.items():
        value = readField(secLines, name, errCtx, optional)
        if optional and not value:
            continue
        verify(value, errCtx + f'field="{name}"')


def verifyEquals(expected):
    def verify(value, errCtx):
        assert str(value) == expected, errCtx
    return verify


def verifyFloatEquals(expected):
    def verify(value, errCtx):
        assert float(value) == pytest.approx(expected, 0.1), errCtx
    return verify


def verifyLenMax(maxLen):
    def verify(value, errCtx):
        assert len(value) <= maxLen, errCtx
    return verify


def verifyDigits(minLen, maxLen):
    def verify(value, errCtx):
        assert str(value).isnumeric() and minLen <= len(value) <= maxLen, errCtx + f' expected {minLen}-{maxLen} digits in "{value}"'
    return verify


def verifyAlphaNumeric():
    def verify(value, errCtx):
        assert str(value).isalnum(), errCtx
    return verify


def isPosInt(value):
    return value.isdigit() and int(value) >= 0


def verifyPosInt():
    def verify(value, errCtx):
        assert isPosInt(value), errCtx + f' expected positive int'
    return verify


def assertPosInt(value, errCtx):
    verifyPosInt()(value, errCtx)


def checkPosInt(value, errors, errCtx=''):
    if not isPosInt(value):
        errors.append(errCtx + f'expected positive int but got "{value}"')


def verifyDecimals(count, negativeOk=False):
    def verify(value, errCtx):
        reAbs = r"\d+(?:\.\d{1," + str(count) + "})?"
        if negativeOk:
            reAll = f"^-?{reAbs}$"
        else:
            reAll = f"^{reAbs}$"
        assert re.match(reAll, value), \
            errCtx + f' value="{value}": expected a float with up to {count} decimals, negativeOk={negativeOk}`'
    return verify


def verifyDate(dateStr, fmt, errCtx):
    try:
        datetime.datetime.strptime(dateStr, fmt)
    except ValueError:
        pytest.fail(errCtx + f' date="{dateStr}" should be in {fmt} format')


def verifyServiceType():
    def verify(value, errCtx):
        assert(value in SERVICE_TYPES.keys()), errCtx + f' allowed Service Types={SERVICE_TYPES.keys()}'
    return verify


def verifyDateFmt(fmt):
    def verify(dateStr, errCtx):
        verifyDate(dateStr, fmt, errCtx)
    return verify


def verifyReasonFmt():
    def verify(value, errCtx):
        sep = '~'
        parts = value.split(sep)
        assert len(parts) >= 3, errCtx + \
            f' expected 3 parts separated by "{sep}" in "{value}"'
        _assertReasonTime(parts[0], errCtx)
        _assertReasonEntity(parts[1], errCtx)
        _assertReasonCode(parts[2], errCtx)

    return verify


def _assertReasonTime(time, errCtx):
    assert len(time) == 4 and time.isdigit(), errCtx + \
        f' expected "hhmm" format in time part="{time}"'
    assert int(time) <= 2400, errCtx + \
        f'expected 0000-2400 in "hhmm" format in time part="{time}"'
    assert int(time[2:]) <= 59, errCtx + \
        f'expected 00-59 minutes in "hhmm" format in time part="{time}"'


def _assertReasonEntity(entity, errCtx):
    allowed = ['A', 'P']
    assert entity in allowed, errCtx + \
        f'expected entity={entity} to be in allowed={allowed}'


def _assertReasonCode(code, errCtx):
    allowed = BID_REASON_CODES
    assert code.upper() in allowed, errCtx + \
        f'expected code="{code}" to be in allowed={allowed}'


def assertAllUnique(vals, errCtx):
    assert len(vals) == len(set(vals)), \
        errCtx + f'expected all values to be unique'


def assertTradeIntervals(vals, errCtx):
    errCtx = errCtx + ' column="Trade Intervals" '
    assert2digits = verifyDigits(2, 2)
    for v in vals:
        assert2digits(v, errCtx)
        assert 1 <= int(v) <= 48, errCtx + ' outside of range'
    assert sorted(vals) == vals, errCtx + f'expected consecutive order'
    assertAllUnique(vals, errCtx)
