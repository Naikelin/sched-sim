#!/bin/bash

for nombre in "$@"; do
    docker run --rm -v "$(pwd)":/sched-sim tanaxer/pybatsim robin schedulers/$nombre.yaml
done