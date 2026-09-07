# KODA Local AI Security

## Status

KODA Local AI is currently a research prototype.

It must not be treated as a production security boundary.

## Intended Environment

The current development version is intended for trusted local environments.

Do not expose the current FastAPI service directly to the public Internet.

Authentication, authorization, rate limiting, upload limits, and production hardening are not yet complete.

## PromptGuard

The current PromptGuard implementation uses basic rule-based keyword filtering.

It is designed as an experimental first layer only.

It may produce false positives and false negatives.

It must not be relied upon as the sole protection against prompt injection, data exfiltration, or malicious input.

## Document API

The current API can load, upload, list, reindex, and delete local documents.

These operations are currently intended for trusted development use.

Before untrusted or multi-user deployment, the document endpoints must be protected by authentication and authorization controls.

## Audit Logging

The research prototype can create local audit logs containing interaction information.

Development audit files are excluded from the Git repository.

Do not use real production student data, private educational records, or other sensitive personal data in development audit logs.

Audit logging is planned to become explicitly opt-in before production use.

## Sensitive Data

Never commit the following to the repository:

- .env files
- passwords
- API keys
- access tokens
- private keys
- production databases
- private user documents
- student records
- audit logs
- raw participant voice recordings
- restricted model weights
- proprietary datasets without permission

The repository .gitignore is designed to exclude common local secrets, logs, model files, vector databases, and audio data.

Always inspect Git status before committing.

## Local Models

Model files are not distributed through this repository.

Users are responsible for obtaining models from their legitimate source and complying with the relevant model license.

The current research baseline references Gemma 3 4B through a local Ollama runtime.

KODA does not claim ownership of third-party model weights.

## RAG and Retrieved Content

Retrieved documents must be treated as untrusted input.

Future versions should add stronger controls against malicious document instructions, retrieval poisoning, and prompt injection.

The deterministic KODA application layer must remain authoritative over application state and educational workflow.

## Network Exposure

The current local Ollama endpoint is expected to run on:

http://127.0.0.1:11434

The KODA Local AI API should also remain bound to localhost during research testing unless a secure deployment architecture is implemented.

## Reporting Security Issues

Do not publish sensitive vulnerability details in public issues.

Security reports should be communicated privately to the project maintainer.

## Research Principle

Local execution improves privacy characteristics, but local execution alone does not guarantee security.

Security depends on the complete system, including model runtime, API configuration, operating system, document handling, logging, permissions, and application architecture.
