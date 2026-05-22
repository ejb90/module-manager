#!/bin/bash

uv run module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.7.0 \
  --prefix /private/tmp/module-manager-tools \
  --module-root /private/tmp/module-manager-modulefiles \
  --execute-install

module use /private/tmp/module-manager-modulefiles
module load gitconductor/0.1.0
gitconductor --help