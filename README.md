# pytest-automation

## Local setup (Windows)

1. Download and run Miniconda with Python 3.6 64-bit exe installer from https://conda.io/miniconda.html

1. Create/activate/deactivate python virtual environment
    ```
    conda create --name pytestauto
    activate pytestauto
    <do some work> ...
    deactivate
    ```

1. Upgrade to the latests pip
    ```
    python -m pip install --upgrade pip
    ```

1. Install required Python Libraries
    ```
    cd <project_dir>
    pip install -r requirements.txt
    ```

1. Set test env and run all tests (with verbose output, print and reason for skips)
    ```
    set PYTEST_ADDOPTS='--env=dev-local --apicode=secret1 --dbuid=secret2 --dbpwd=secret3 --ftpuid=secret4 --ftppwd=secret5 --cosmoskey=secret6 --storekey=secret7'
    set HTTPS_PROXY=
    set HTTP_PROXY=

    pytest -svvrs ./tests
    ```


## Docker CI

#### Docker Image
ensure contains:
- Python 3.6
- MS ODBC driver 17 for SQL Server (https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-2017)
- unixODBC development headers
- pyodbc (may be required to download from https://pypi.org/project/pyodbc/#files

#### Dockerfile:
- copy project source files
- install dependencies
- run tests and genarate JUnit XML report
    ```
    COPY resources/ resources/
    COPY tests/ tests/
    COPY config.yml
    COPY requirements.txt
    RUN pip install -r requirements.txt
    CMD pytest -svvlrs ./tests --junitxml=results.xml
    ```

#### CI host (agent):

build and run the docker container and:
- pass PYTEST_ADDOPTS env variable with secret key=value arguments
- mount a host directory into the container to see the test results
    ```
    export PYTEST_ADDOPTS='--env=tst-cloud --apicode=secret1 --dbuid=secret2 --dbpwd=secret3 --ftpuid=secret4 --ftppwd=secret5 --cosmoskey=secret6 --storekey=secret7'
    export HTTPS_PROXY=
    export HTTP_PROXY=

    docker run -e PYTEST_ADDOPTS -e HTTPS_PROXY -e HTTP_PROXY -it --rm ubu-py-mssql-ta -v /host/dir:/docker/results/dir ubu-py-mssql-ta
    ```