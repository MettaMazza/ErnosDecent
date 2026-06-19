# Sovereign Storage & CRDT User Guide

This guide details the operations of the Content-Addressable Storage (CAS) engine, document ingestion parser, and Conflict-Free Replicated Data Types (CRDTs).

---

## 1. Sovereign Document Ingestion

Sovereign Document Ingestion allows you to import unstructured text files into your node to populate the local agent's vector database (Retrieval-Augmented Generation / RAG space):
- **Supported Formats**: `.pdf`, `.txt`, `.md`, and `.markdown`.
- **Upload Zone**: You can drag and drop files directly onto the ingestion dashboard card or click the browse link to select a file manually.
- **Processing Flow**:
  1. The node daemon parses the document text.
  2. The text is broken down into semantic chunks.
  3. Embedding vectors are generated for each chunk.
  4. The vectors are saved to the local database, allowing the AI agent to retrieve relevant sections during chat interactions.

---

## 2. Content-Addressable Storage (CAS) (`decent_store/content.ep`)

The underlying storage layer utilizes Content-Addressable Storage (CAS) rather than standard path-based file hierarchies.

### A. Core CAS Principles
- **Immutable Blocks**: Data is divided into smaller chunks. Each chunk is saved as an immutable block identified by the SHA-256 hash of its content. This hash serves as the Content Identifier (CID).
- **Verification**: When loading blocks, the storage engine re-computes the SHA-256 hash and validates it against the block's CID. If the hash does not match, the block is flagged as corrupted.
- **Parameters**: The storage engine enforces a maximum block size of $65,536$ bytes and a default chunk size of $4,096$ bytes for file splits.

### B. Deduplication Ratio
Because files are stored based on their unique content hashes, identical sub-block data segments are only saved to disk once. If you store two files containing identical chunks, the duplicate chunks share the same CID and point to the same physical disk block. The **Deduplicated Ratio** telemetry tracks your disk space savings.

### C. Persistent Storage
All CAS blocks, indices, and content metadata are persisted in the node's local database located at `decent_store/content.db`.

---

## 3. Conflict-Free Replicated Data Types (CRDTs) (`decent_store/crdt.ep`)

To replicate settings, message status, index listings, and document manifests across multiple peers eventually without needing a centralized server, ErnosDecent implements mathematical Conflict-Free Replicated Data Types (CRDTs). All supported CRDTs can merge concurrently updated copies deterministically:

1. **Grow-Only Counter (G-Counter)**:
   - A counter that can only increase.
   - Each peer node (replica) maintains its own positive increment entry. The global counter value is the sum of entries across all replicas.
   - **Merge Rule**: Takes the maximum value for each replica entry.

2. **Positive-Negative Counter (PN-Counter)**:
   - A counter supporting both increments and decrements (e.g. tracking online peer list size).
   - Combines a positive G-Counter (increases) and a negative G-Counter (decreases). The overall value is the positive G-Counter value minus the negative G-Counter value.

3. **Last-Write-Wins Register (LWW-Register)**:
   - Stash register containing a value and an associated update timestamp.
   - **Merge Rule**: Compares the incoming update timestamp against the local register timestamp. The value with the higher timestamp is kept, resolving concurrent edits.

4. **Observed-Remove Set (OR-Set)**:
   - A set allowing elements to be added and removed concurrently.
   - When an element is added, it is assigned a unique tag. When removed, all known tags for that element are moved to a tombstones list.
   - **Merge Rule**: Takes the union of all additions, minus elements whose tags are in the tombstones list.

5. **Multi-Value Register (MV-Register)**:
   - Stores concurrent register updates rather than discarding one.
   - If two updates happen concurrently, the merge retains both values (creating a branch), presenting them to the client to explicitly resolve the conflict.
