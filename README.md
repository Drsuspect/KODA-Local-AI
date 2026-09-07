# KODA Local AI

**Local-first Turkish AI research for accessible, voice-first education.**

KODA Local AI is an experimental local artificial intelligence layer developed as part of the KODA R&D ecosystem.

The project explores how locally running language models, semantic retrieval, and controlled AI assistance can support accessible and voice-first educational systems without handing control of the application flow to a generative model.

> Status: Research Preview - v0.1

## Goals

KODA Local AI focuses on:

- local-first AI execution
- Turkish language interaction
- semantic document retrieval
- Retrieval-Augmented Generation (RAG)
- controlled educational explanations
- accessibility-oriented AI interaction
- privacy-conscious local processing
- future voice-first integration

## Current Technology Baseline

- Gemma 3 4B
- Ollama local runtime
- sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- ChromaDB
- FastAPI
- PyMuPDF
- python-docx

The current Gemma model is a baseline model and has not been fine-tuned by KODA.

Fine-tuning and LoRA experiments are planned as a separate research stage.

## Current RAG Pipeline

Documents
    |
    v
TXT / PDF / DOCX
    |
    v
Document Loader
    |
    v
Text Chunker
    |
    v
Multilingual Embeddings
    |
    v
ChromaDB
    |
    v
Semantic Retrieval
    |
    v
Gemma 3 4B via Ollama
    |
    v
Controlled Turkish Response

## Educational AI

The experimental API includes a tutor explanation flow that works with structured educational information including:

- lesson code
- question ID
- question text
- answer choices
- correct answer
- student answer
- lesson passage
- explanation hints

The language model does not control the educational application.

KODA's deterministic application layer remains authoritative for navigation, lesson flow, quizzes, exams, and accessibility behaviour.

The AI layer is intended for bounded assistance such as:

- explaining why an answer is correct
- explaining a subject another way
- responding when a learner says they did not understand
- producing a simpler example

## Accessibility Direction

Future research is planned to connect KODA Local AI with KODA's accessibility work, including:

- accessible Turkish reading rules
- mathematical speech representation
- voice-first interaction
- local speech recognition
- controlled educational dialogue

## Privacy

The architecture is designed for local operation.

The current research prototype can create local audit logs during development. These logs remain on the local machine and are excluded from the repository.

Audit logging is planned to become explicitly opt-in before production use.

No telemetry service is required by the current core architecture.

## Security Notice

KODA Local AI is currently a research prototype.

The current PromptGuard is a basic rule-based experimental filter and must not be considered a complete security boundary.

The development API is intended for trusted local environments only.

Do not expose the current API directly to the public Internet.

See SECURITY.md for additional information.

## Repository Structure

KODA-Local-AI/
|-- audit/
|-- common/
|-- data/
|   `-- documents/        # local runtime documents, ignored by Git
|-- examples/
|   `-- documents/        # safe public sample documents
|-- experiments/
|   `-- legacy/
|-- llm_core/
|-- rag/
|-- security/
|-- .env.example
|-- api_server.py
|-- main.py
|-- requirements.txt
|-- ARCHITECTURE.md
|-- SECURITY.md
`-- README.md

## Research Roadmap

### v0.1 - Local RAG Baseline

- Gemma 3 4B
- Ollama
- multilingual embeddings
- ChromaDB
- semantic RAG
- local FastAPI prototype

### v0.2 - Education RAG

- structured educational content
- tutor explanation evaluation
- grounding tests
- Turkish answer quality benchmarks

### v0.3 - Accessibility Layer

- KODA Reading rules
- KODA MathSpeak rules
- accessible response transformation

### v0.4 - Voice

- local speech recognition integration
- voice-first educational interaction
- controlled speech input/output pipeline

### v0.5 - KODA Model Research

- dataset preparation
- baseline evaluation
- LoRA / fine-tuning experiments
- comparison with small local models

## Project Status

This repository represents active research and development.

Interfaces, models, and architecture may change significantly.

It should not yet be considered production-ready.

## KODA

KODA is an accessibility-focused, voice-first education research and development initiative.

Project website: https://kodaai.com.tr

---

Designed and developed by Murat GUNEY LARRANAGA.

Copyright 2026 KODA AI

## License and Usage

Copyright 2026 KODA AI / Murat GUNEY LARRANAGA.

This repository is published for research, evaluation, and collaboration purposes.

No license is currently granted for commercial use, redistribution, sublicensing, or incorporation into commercial products without prior written permission.

For collaboration or commercial licensing inquiries:
https://kodaai.com.tr
