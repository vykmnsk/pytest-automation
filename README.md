# pytest-automation

## Local setup (Windows)

1. Download and run Miniconda with Python 3.6 64-bit exe installer from https://conda.io/miniconda.html

1. Create and activate python virtual environment
    ```
    conda create --name pytestauto
    activate pytestauto
    ```



1. Download and manually install Python 3 from https://www.python.org/downloads/
1. Install python Virtual Environment
    ```
    python -m pip install virtualenv
    ```
1. Activate/deactivate virtual environment
    ```
    env\Scripts\activate
    deactivate
    ```

1. Upgraded to the latests pip
    ```
    python -m pip install --upgrade pip
    ```

1. Install required Python Libraries
    ```
    cd <project_dir>
    pip install -r requirements.txt
    ```

1. Run all tests (with verbose output, print and reason for skips)
    ```
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
    docker run -it --rm -v /host/dir:/docker/volume... -e PYTEST_ADDOPTS='--env=tst-cloud --apicode=secret1 --dbuid=secret2 --dbpwd=secret3 --ftpuid=secret4 --ftppwd=secret5 --cosmoskey=secret6 --storekey=secret7 --dbinfo-uid=secret8 --dbinfo-pwd=secret9'
    ```