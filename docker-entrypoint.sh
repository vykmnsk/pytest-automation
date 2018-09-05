#!/usr/bin/env bash

echo "Starting docker-entrypoint.sh"

echo "building list of expected variables"
EXPECTED_VARS=( \
    "${PYTEST_ADDOPTS}" \
)

echo "Expected variables are: "
echo $EXPECTED_VARS

echo "Validating expected variables: "
for var in "${EXPECTED_VARS[@]}"; do
    echo "The value: ${var} has been passed to the container."
    if [ -z "${var}" ]; then
        echo "Error! One or more required variables are not set."
        echo "Exiting..."
        exit 2
    fi
done

pytest -svvrs --tb=short ./tests --junitxml=results.xml

cp ./results.xml ./resultsvolume/
chmod a+rw ./resultsvolume/results.xml
echo "Test results volume content:"
ls -l ./resultsvolume

if [[ "$?" -ne "0" ]]; then
    exit 101
fi

