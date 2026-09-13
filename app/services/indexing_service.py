class IndexingService:

    def __init__(self, search_index, index_path, index_lock):
        self.search_index = search_index
        self.index_path = index_path
        self.index_lock = index_lock

    def index_document(self, document_path: str):

        from pathlib import Path
        import time

        from app.search.loader import load_document

        file_path = Path(document_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Document not found: {document_path}"
            )

        start = time.perf_counter()

        documents = load_document(file_path)

        extraction_time = time.perf_counter() - start

        with self.index_lock:

            start = time.perf_counter()

            self.search_index.remove_documents_by_filename(
                file_path.name
            )

            remove_time = time.perf_counter() - start

            start = time.perf_counter()

            self.search_index.add_documents(documents)

            indexing_time = time.perf_counter() - start

            start = time.perf_counter()

            self.search_index.save(self.index_path)

            save_time = time.perf_counter() - start

        total_time = (
            extraction_time
            + remove_time
            + indexing_time
            + save_time
        )

        print(
            f"[Indexing] {file_path.name} | "
            f"extract={extraction_time:.2f}s | "
            f"remove={remove_time:.2f}s | "
            f"index={indexing_time:.2f}s | "
            f"save={save_time:.2f}s | "
            f"total={total_time:.2f}s"
        )

        return {
            "document": document_path,
            "status": "indexed",
            "documents_added": len(documents),
            "timings": {
                "extraction": round(extraction_time, 2),
                "remove": round(remove_time, 2),
                "indexing": round(indexing_time, 2),
                "save": round(save_time, 2),
                "total": round(total_time, 2)
            }
        }