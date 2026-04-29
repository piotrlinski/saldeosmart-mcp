<!-- Thanks for sending a pull request! Please fill in this template. -->

## Summary

<!-- One or two sentences. What does this PR do, and why? -->

## Related issue

<!-- Closes #N, or "n/a" if there's no tracking issue. -->

## Test plan

- [ ] `make lint` — ruff + mypy clean
- [ ] `make test` — pytest green
- [ ] (if you have credentials) `python scripts/smoke_test.py` — read endpoints still work
- [ ] (if a new tool was added) docstring follows the contract in `CONTRIBUTING.md` (one-line purpose, "Use this when…", per-arg, return shape, error path)
- [ ] (if a new tool was added) `README.md` tool table updated and the "Choosing the right tool" section reflects any disambiguation

## Architecture

- [ ] No upward imports across layers (`config → errors → http → models → tools → server`). The architecture test enforces this — confirm it's still green locally.
- [ ] No direct `print()` to stdout (the MCP transport owns it); logging goes through the file logger only.
- [ ] No `str()`/`repr()` of `SecretStr` and no inline tokens in URLs/log messages.

## Screenshots / output (optional)

<!-- Paste a snippet of MCP Inspector / Claude Desktop output, or relevant log lines. Redact tokens. -->

## Checklist

- [ ] I have read [`CONTRIBUTING.md`](../CONTRIBUTING.md).
- [ ] I agree my contribution will be licensed under the project's [MIT License](../LICENSE).
