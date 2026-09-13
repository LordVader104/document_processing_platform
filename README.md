# Document Processing Platform

A document processing platform that combines a search engine with
asynchronous task processing and worker-based document indexing.

This project is the evolution of two independent projects:

- [Key Phrase Finder](https://github.com/LordVader104/key_phrase_finder) —
  the original document search and information retrieval engine.
- [TaskFlow](https://github.com/LordVader104/taskflow) —
  the task queue and worker execution system developed to provide
  asynchronous background processing.

The platform integrates both systems into a single FastAPI application,
providing document management, asynchronous indexing, persistent task
tracking, and full-text search through a unified interface.

---

## Overview

Document Processing Platform provides a complete workflow for uploading,
processing, indexing, and searching PDF and TXT documents.

The platform separates the HTTP request lifecycle from potentially
expensive document indexing operations. When a document is uploaded,
the API creates an `index_document` task and places it into the TaskFlow
priority queue instead of performing the indexing operation directly
inside the HTTP request.

A pool of worker threads continuously consumes tasks from the queue and
executes the registered task functions. The indexing task is connected
directly to the search engine through an `IndexingService`, allowing the
worker to extract, index, and persist documents in the background.

Task state is persisted in PostgreSQL, allowing the platform to track
tasks independently from the HTTP request that created them.

The resulting architecture consists of:

- Document management
- Asynchronous task processing
- Priority-based task queue
- Worker-based task execution
- PDF/TXT document extraction
- Inverted index
- TF-IDF and BM25 ranking
- Persistent search index
- Persistent task state
- Web-based search interface

---

## Architecture

The application runs as a single FastAPI process while internally
combining the search engine and TaskFlow components.

```text
                         Browser
                            │
                            ▼
              ┌──────────────────────────┐
              │   FastAPI Application    │
              │                          │
              │  Document API            │
              │  Search API              │
              │  Task API                │
              └────────────┬─────────────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
      Document Upload              Search Engine
             │                           │
             ▼                           │
        TaskFlow                         │
     Priority Queue                      │
             │                           │
             ▼                           │
        Worker Pool                      │
             │                           │
             ▼                           ▼
      IndexingService              Inverted Index
             │                           │
             └──────────────┬────────────┘
                            │
                            ▼
                       PostgreSQL
 
 
