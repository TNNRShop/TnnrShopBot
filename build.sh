#!/bin/bash
set -e

export MISE_PYTHON_GITHUB_ATTESTATIONS=false
export PYTHON_GITHUB_ATTESTATIONS=false

# Install Python via mise or system package manager
if command -v mise &> /dev/null; then
  mise install
else
  apt-get update && apt-get install -y python3.11 python3.11-venv python3-pip
fi

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt
