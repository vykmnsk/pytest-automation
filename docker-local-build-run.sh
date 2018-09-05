rm -rf tests/__pycache__
docker build . -t ubu-py-mssql-ta
docker run -e PYTEST_ADDOPTS -e HTTPS_PROXY -e HTTP_PROXY -it --rm ubu-py-mssql-ta -v c:/tmp/docker-output:/workdir/resultsvolume ubu-py-mssql-ta