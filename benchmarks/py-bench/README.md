# PySemBridge Python Benchmarks

This directory contains the Python CVE benchmark projects used to evaluate PySemBridge and analyzer backends such as YASA.

## Layout

Benchmark directories in `py-bench/` are self-contained. Depending on the sample, a benchmark may include:

- `vulnerable_project/` or `original_files/`: the local source tree scanned by YASA
- `poc/`: a small runtime trigger
- `yasa/`: `manifest.json` and rule files for baseline / sembridge replay
- `pysembridge/`: `bridge.json` and, when available, compiled `yasa-facts.json`

Generated analyzer outputs should stay outside this directory, typically under `experiments/results/`, which is ignored by git.

## Legacy Benchmarks

These older benchmarks keep the original repository-oriented layout:

| Benchmark | Focus |
| --- | --- |
| `cve-2023-4033-mlflow` | command injection flow through MLflow prediction entrypoints |
| `cve-2023-24816-ipython` | terminal title command execution flow |
| `cve-2024-27758-rpyc` | dynamic object protocol and pickle-related flow |
| `cve-2024-36039-pymysql` | SQL query construction and formatting flow |
| `cve-2025-55156-pyload` | boundary method to database sink flow |
| `cve-2026-24486-python-multipart` | parser callback and file path flow |

## Semantic-Minimized CVE Set

The repository now also includes twenty self-contained CVE samples focused on Python dynamic semantics and static-analysis flow breaks.

### Command Injection

- `cve-2022-24065-cookiecutter`
- `cve-2023-5752-pip`
- `cve-2024-32027-kohya-ss`
- `cve-2024-52803-llamafactory`
- `cve-2024-6345-setuptools`
- `cve-2025-12763-pgadmin4`
- `cve-2025-49835-gpt-sovits`
- `cve-2025-54072-ytdlp`
- `cve-2026-45369-python-utcp`

### Path Traversal / Arbitrary File Write

- `cve-2025-47273-setuptools`
- `cve-2026-40576-excel-mcp`

### SQL Injection

- `cve-2022-28346-django`
- `cve-2023-47128-piccolo`
- `cve-2023-49736-superset`
- `cve-2024-9774-python-sql`
- `cve-2025-59681-django`
- `cve-2025-64104-langgraph`
- `cve-2025-67644-langgraph`
- `cve-2026-29080-rucio`
- `cve-2026-41490-dagster-snowflake`

## Summary Tables

For the cross-sample comparison table, see:

- `cve20_yasa_summary_table.md`
- `cve20_yasa_summary_table.csv`
