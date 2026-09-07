# KODA Local AI Architecture

## Design Principle

The language model is not the controller of the KODA application.

The deterministic KODA application layer controls:

- application state
- authentication
- navigation
- lesson flow
- quiz flow
- exam flow
- accessibility rules

The AI layer acts as a bounded assistant.

## Core Pipeline

User Question
    |
    v
Prompt Guard
    |
    v
Semantic Retriever
    |
    +--> Document Loader
    |        |
    |        v
    |      Chunker
    |        |
    |        v
    |     Embeddings
    |        |
    |        v
    |     ChromaDB
    |
    v
Retrieved Context
    |
    v
Local LLM
Gemma 3 4B / Ollama
    |
    v
Output Cleaning
    |
    v
Application

## Local LLM

The current baseline communicates with a local Ollama server.

Default model:

gemma3:4b

Default local endpoint:

http://127.0.0.1:11434

The architecture should allow the model runtime to be replaced in future experiments.

## RAG

The active retrieval implementation uses semantic embeddings and ChromaDB.

Current embedding baseline:

sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

Legacy retrieval experiments are retained under:

experiments/legacy/

They are not part of the active v0.1 retrieval pipeline.

## Educational Tutor

The Tutor API accepts structured question information rather than allowing unrestricted control over the education engine.

This separation is intentional.

The deterministic education engine knows the correct answer and lesson state.

The LLM explains the information supplied to it.

## Accessibility Layer

Planned architecture:

KODA Education Engine
    |
    v
Bounded AI Assistance
    |
    v
Accessibility Transformation
    |
    +--> Reading Rules
    |
    +--> Mathematical Speech Rules
    |
    v
Voice Output

This preserves deterministic accessibility behaviour while allowing natural-language assistance.

## Future Voice Integration

Speech
  |
  v
Local STT
  |
  v
KODA Intent / State Engine
  |
  +--> deterministic command --> KODA
  |
  +--> explanation request --> Local AI
                                |
                                v
                       Accessibility Layer
                                |
                                v
                              Voice
