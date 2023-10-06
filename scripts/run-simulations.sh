#!/bin/bash

# Recorre todos los argumentos pasados al script
for nombre in "$@"; do
    nix-shell shell.nix --run "robin schedulers/$nombre.yaml"
done