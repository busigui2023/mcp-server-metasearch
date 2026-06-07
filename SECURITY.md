# Security Policy

## Supported Versions

Only the latest release is supported with security updates.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public issue.** Instead, please:

1. Email the maintainer at the address shown in the GitHub profile, or
2. Use GitHub's [private vulnerability reporting](https://github.com/busigui2023/mcp-server-metasearch/security/advisories/new)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days.

## Security Best Practices for Users

- Never commit your `.env` file or API keys to version control
- Store your `~/.config/mcp-server-metasearch/.env` with restrictive permissions (`chmod 600`)
- Keep dependencies up to date (`uv pip install -U mcp-server-metasearch`)
- Review the `.env.example` template — it contains no real credentials
