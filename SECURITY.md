# Security Policy — CrimeLens AI

## Reporting a vulnerability

If you discover a security issue, please report it privately.

- Do **not** open a public GitHub issue for vulnerabilities that expose data, credentials, or remote code execution paths.
- Prefer emailing the maintainers listed in the repository (or your agency security contact) with steps to reproduce, impact, and any suggested fix.

## Secrets policy

- Never commit `.env`, API keys, JWT secrets, database passwords, or private certificates.
- Use `.env.example` for variable names and empty placeholders only.
- Rotate any credential that may have been exposed in chat logs, screenshots, or accidental commits.

## Responsible use

CrimeLens AI is a decision-support system. Model outputs must not be treated as sole grounds for enforcement action without human review and applicable policy.
