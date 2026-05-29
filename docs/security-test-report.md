# PySemBridge Security Test Report

## Scope

This security review covers the self-developed PySemBridge tool code and
supporting scripts:

- `pysembridge/`
- `tests/`
- `experiments/scripts/`
- `docs/`
- `README.md`
- `pyproject.toml`

The review intentionally excludes benchmark projects and the integrated YASA
engine copy because those directories contain external or upstream code:

- `benchmarks/`
- `integrations/`

## Goals

The goal is to confirm that the submitted self-developed code does not contain
intentionally planted malicious behavior, such as backdoors, credential theft,
hidden network beacons, reverse shells, destructive commands, or hard-coded
secrets.

## Checks

### Suspicious API and Shell Pattern Scan

Command:

```bash
rg -n "(eval\(|exec\(|compile\(|__import__\(|importlib\.import_module|pickle\.loads|marshal\.loads|base64\.b64decode|subprocess\.|os\.system|popen\(|socket\.|requests\.|urllib\.request|ftplib|paramiko|telnetlib|chmod|chown|setuid|setgid|rm -rf|curl |wget |nc |netcat|reverse shell|backdoor|password|token|secret|api[_-]?key)" pysembridge tests experiments/scripts docs README.md pyproject.toml
```

Result summary:

- `pysembridge/recognizer/features.py` matches `__import__`,
  `importlib.import_module`, and `pickle.loads` only as static-recognition
  pattern strings. The recognizer records those constructs when they appear in
  analyzed projects; it does not execute them.
- `pysembridge/pipeline/yasa.py` uses `subprocess.run` to invoke the configured
  YASA command with an argument list. This is expected CLI orchestration, not a
  shell backdoor.
- No `eval`, `exec`, `os.system`, socket beaconing, reverse shell, destructive
  `rm -rf`, credential exfiltration, or hard-coded secret pattern was found in
  the reviewed self-developed code.

### Secret Pattern Scan

Command:

```bash
rg -n "BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9_]{36}|github_pat_|xox[baprs]-|sk-[A-Za-z0-9]{20,}" . -g '!benchmarks/**' -g '!integrations/**' -g '!**/__pycache__/**'
```

Result summary:

- No private keys, GitHub tokens, AWS access keys, Slack tokens, or OpenAI-style
  API keys were found in the reviewed scope.

### Executable Permission Scan

Command:

```bash
find pysembridge tests experiments/scripts -type f -not -path '*/__pycache__/*' -perm /111 -print
```

Result summary:

- No unexpected executable Python files or scripts were found in the reviewed
  scope.

### Dependency Surface Review

Command:

```bash
sed -n '1,220p' pyproject.toml
```

Result summary:

- Runtime dependencies are empty.
- `jsonschema` is optional and used only for bridge schema validation.
- The build backend uses `setuptools`.

## Functional Regression Check

Command:

```bash
python3 -m unittest tests.test_recognizer_features
```

Expected result:

```text
Ran 1 test
OK
```

## Conclusion

No evidence of intentionally planted malicious code was found in the reviewed
self-developed PySemBridge code. The only sensitive-pattern matches are
explainable static-analysis recognizer patterns or explicit YASA CLI
orchestration.

For competition submission, cite this report together with the exact commands
above so reviewers can reproduce the same checks.
