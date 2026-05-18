# PySemBridge Python Benchmarks

This directory contains the six Python CVE benchmark projects used to evaluate PySemBridge and analyzer backends such as YASA.

## Included Benchmarks

| Benchmark | Focus |
| --- | --- |
| `cve-2023-4033-mlflow` | command injection flow through MLflow prediction entrypoints |
| `cve-2023-24816-ipython` | terminal title command execution flow |
| `cve-2024-27758-rpyc` | dynamic object protocol and pickle-related flow |
| `cve-2024-36039-pymysql` | SQL query construction and formatting flow |
| `cve-2025-55156-pyload` | boundary method to database sink flow |
| `cve-2026-24486-python-multipart` | parser callback and file path flow |

Each benchmark keeps its local `poc/` driver and reduced project source tree. Generated analyzer outputs should stay outside this directory, typically under `experiments/results/`, which is ignored by git.
