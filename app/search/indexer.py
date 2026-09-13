import math
import pickle
from pathlib import Path

from app.search.tokenizer import tokenize


class InvertedIndex:

    def __init__(self):
        self.index = {}
        self.documents = {}

    def add_document(self, doc_id, document):

        if isinstance(document, str):
            document = {
                "page": None,
                "text": document
            }

        self.documents[doc_id] = document

        tokens = tokenize(document["text"])

        for token in tokens:

            if token not in self.index:
                self.index[token] = set()

            self.index[token].add(doc_id)

    def add_documents(self, documents):

        for doc_id, document in documents.items():
            self.add_document(doc_id, document)

    def remove_document(self, doc_id):

        if doc_id not in self.documents:
            return

        tokens = tokenize(
            self.documents[doc_id]["text"]
        )

        for token in tokens:

            if token in self.index:
                self.index[token].discard(doc_id)

                if not self.index[token]:
                    del self.index[token]

        del self.documents[doc_id]

    def remove_documents_by_filename(self, filename):

        doc_ids = [
            doc_id
            for doc_id in self.documents
            if doc_id == filename
               or doc_id.startswith(f"{filename}#page=")
        ]

        for doc_id in doc_ids:
            self.remove_document(doc_id)

    def save(self, file_path):

        file_path = Path(file_path)
        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(file_path, "wb") as file:
            pickle.dump(
                {
                    "index": self.index,
                    "documents": self.documents
                },
                file
            )

    def load(self, file_path):

        file_path = Path(file_path)

        if not file_path.exists():
            return False

        with open(file_path, "rb") as file:
            data = pickle.load(file)

        self.index = data["index"]
        self.documents = data["documents"]

        return True

    def term_frequency(self, doc_id, term):

        tokens = tokenize(
            self.documents[doc_id]["text"]
        )

        if not tokens:
            return 0

        return tokens.count(
            term.lower()
        ) / len(tokens)

    def inverse_document_frequency(self, term):

        total_documents = len(self.documents)

        document_frequency = len(
            self.index.get(
                term.lower(),
                set()
            )
        )

        if document_frequency == 0:
            return 0

        return math.log(
            total_documents / document_frequency
        )

    def tf_idf(self, doc_id, term):

        tf = self.term_frequency(
            doc_id,
            term
        )

        idf = self.inverse_document_frequency(
            term
        )

        return tf * idf