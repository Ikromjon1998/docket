# Document Q&A pipeline: from upload to answer

How one user question travels through the backend, from the moment a document is
uploaded to the moment the assistant replies. All paths are relative to `Cases-AI-main/app/`.

## Entry points

| Action | Route | Handler |
|---|---|---|
| Upload a document | `POST /api/v1/files/upload` | `upload_file` in `api/v1/files.py` |
| Approve / train a document | `POST /api/v1/files/{file_id}/train`, `POST /api/v1/files/{file_id}/approve` | `train_file`, `approve_file` in `api/v1/files.py` |
| Ask a question in chat | `POST /api/v1/chat/message` | `send_message` in `api/v1/chat.py` → `ChatService.send_message` (`services/chat_service.py`) → `QAService.answer_chat_question` |

## The six steps

| # | Step | File | Function | What happens |
|---|---|---|---|---|
| 1 | **Ingest** | `services/file_service.py` | `FileService.handle_file_upload` | Validates MIME type, extension and size; writes the bytes to `UPLOAD_DIR` under a UUID filename; inserts a `CaseFile` row with status `DRAFT`. Nothing is parsed yet. |
| 1b | *Approval gate* | `api/v1/files.py` → `services/case_service.py` | `train_file` / `approve_file` → `CaseService.process_file_and_extract_metadata` | Admin approval sets status `APPROVED` and triggers processing. A non-admin "train" only sets `PENDING` via `FileService.request_training`. |
| 2 | **Chunk** | `services/file_service.py` → `utils/pdf_parser.py` → `utils/text_chunker.py` | `FileService.process_file_embeddings_safe` → `extract_text_from_file_path` → `chunk_text` | Text is extracted from the PDF/DOCX on disk, then split by whitespace tokens into 800-word windows with a 100-word overlap. |
| 3 | **Embed** | `services/embedding_service.py` | `EmbeddingService.create_embeddings_for_chunks` → `create_embedding` | One `embeddings.create` call per chunk (sequential, not batched), using `settings.embedding_model`. |
| 4 | **Store** | `services/file_service.py` + `models/embedding.py` | `FileService.process_file_embeddings_safe` (loop) → `Embedding` model | Each `(chunk_text, vector)` pair becomes a row in the `embeddings` table. `vector` is a plain Postgres `float[]`, not pgvector. File status becomes `PROCESSED` and the transaction is committed. |
| 5 | **Retrieve** | `services/qa_service.py` | `QAService._generate_rag_answer` (first half) | Loads **every** `Embedding` row for the case's `PROCESSED` files, embeds the question, scores cosine similarity in NumPy (`_cos_similarities`), adds +0.05 per question keyword found in the chunk, drops chunks below 0.20 similarity, keeps the top 4. |
| 6 | **Answer** | `services/qa_service.py` | `QAService._generate_rag_answer` (second half), called from `answer_chat_question` | Builds a system prompt + chat history + `[SOURCE n]`-labelled chunks + the question; calls `chat.completions.create` with `settings.chat_model`; trims a truncated answer back to its last full sentence; `answer_chat_question` saves the reply as a `ChatMessage`. |

## Things to know

- **Retrieval is in-process, not a vector-DB query.** All embeddings for the case are pulled
  into Python and scored with NumPy. Fine for a handful of documents; cost grows linearly with
  the number of chunks in the case.
- **Not every question reaches retrieval.** `answer_chat_question` first runs an LLM intent
  classifier (`GREETING` / `MEMORY` / `FOLLOW_UP` / `QUESTION`). Only `QUESTION` goes through
  RAG; the other three are answered from chat history alone, with no sources.
- **Upload alone does nothing for Q&A.** Steps 2–4 run only after approval. Until then,
  step 5 finds no `PROCESSED` files and, if a `PENDING` file exists for the case, replies that
  the document is waiting for firm admin approval.
- **Dimension guard.** Before scoring, stored vectors whose length differs from the question
  vector's are discarded, so switching embedding deployments cannot mix incompatible vectors.
- **Meeting transcripts can join the pool.** When the caller passes `include_meetings=True`
  (the `/api/v1/qa/ask` route does), `case_meeting_chunks` from
  `services/meeting_index_service.py` is appended to the embeddings list before scoring, and
  meeting sources are listed under the answer.

## Status lifecycle of a `CaseFile`

```
DRAFT ──(user: train)──▶ PENDING ──(admin: approve)──▶ APPROVED ──▶ PROCESSING ──▶ PROCESSED
  │                                                        │               │
  └──────────(admin: train)────────────────────────────────┘               └──(error / no text)──▶ REJECTED
```

Only `PROCESSED` files are visible to retrieval.

## Definitions

What is embedding? Text extracted into array of number using Model by meaning so by exact meaning will be so more similar arrays
Why do we cut documents into chunks instead of sending the whole file? An embedding extract the document average to one vector and for example if we extract 40 pages document we will get just average of it and by citation we can point more exactly point of the document, so by the whole file we got the result like somewhere there in whole file. And by the hardware we ahve always limitations and that give us boundaries for input and llm also gives the answers in restricted context. so sending the whole file outright or wastes context on not needed pages which costs money and measurable lowers answer quality.