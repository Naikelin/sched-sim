#!/bin/bash

for nombre in "$@"; do
    docker run --rm -v "$(pwd)":/sched-sim sched-sim robin schedulers/$nombre.yaml
done