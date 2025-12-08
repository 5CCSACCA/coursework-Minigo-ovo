#!/bin/bash
set -e

echo "[Test] Installing dependencies..."
pip install pytest requests

echo "[Test] Waiting for system to stabilize..."
sleep 5

echo "[Test] Running system tests..."
pytest -v -s systemtest.py
