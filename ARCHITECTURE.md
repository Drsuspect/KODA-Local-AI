# KODAAI Local AI Architecture

## Design Principle

The language model is not the controller of the KODAAI application.

The deterministic KODAAI application layer controls:

- application state
- authentication
- navigation
- lesson flow
- quiz flow
- exam flow
- accessibility rules

The AI layer acts as a bounded assistant.

## KODAAI Math Engine V1.0

KODAAI Math Engine is the deterministic mathematical reasoning layer of KODAAI Local AI.

Supported mathematical requests are handled before semantic retrieval and generative-model fallback.

The language model is not the mathematical authority for expressions supported by the Math Engine.

### Request Routing

User Question
    |
    v
Math Intent / Routing
    |
    +--> Algebra Engine
    |
    +--> Arithmetic Evaluator
    |
    +--> Percentage Engine
    |
    +--> Ratio Engine
    |
    +--> Unsupported / Non-Math
              |
              v
        RAG / Local LLM

The active MathService routing order is:

1. algebra
2. unsupported x-equation guard
3. explicit arithmetic
4. percentage
5. ratio
6. RAG / LLM fallback

A mathematical request handled by the deterministic engine is returned directly without retrieved context.

### Algebra Pipeline

Equation
    |
    v
Parse
    |
    v
Normalize
    |
    v
Equation Classification
    |
    v
Deterministic Solver
    |
    v
Explanation Steps
    |
    v
Verification

The V1.0 algebra baseline supports:

- one-variable linear equations
- two-sided linear equations
- positive and negative coefficients
- decimal coefficients
- division forms
- parentheses
- distributive-property expressions
- explicit and implicit multiplication
- reverse equation forms
- zero-coefficient equations

Equation results are classified as:

- unique_solution
- no_solution
- infinite_solutions

### Deterministic Boundary

The Math Engine does not use a generative model to determine the authoritative mathematical result.

For supported expressions, calculation and equation classification are deterministic.

The generated result may include:

- normalized expression
- mathematical classification
- result or solution
- deterministic explanation steps
- verification state
- accessibility-oriented answer text

Unsupported expressions are not silently forced through another deterministic mathematical engine. They remain available to the wider KODAAI Local AI routing and fallback architecture.

### V1.0 Stable Baseline

KODAAI Math Engine V1.0 was promoted unchanged from the V0.13 final hardening baseline.

Validation completed before promotion:

- 47 / 47 final regression tests passed
- 3 / 3 API closure tests passed
- stable source snapshot compiled successfully
- SHA-256 integrity manifest generated and verified

Immutable reference:

    _references/MATH_ENGINE_V1_0_STABLE

The V1.0 snapshot is the official stable baseline for the Math Engine.

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

KODAAI Education Engine
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
KODAAI Intent / State Engine
  |
  +--> deterministic command --> KODAAI
  |
  +--> explanation request --> Local AI
                                |
                                v
                       Accessibility Layer
                                |
                                v
                              Voice
