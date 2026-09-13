import math
from app.search.tokenizer import tokenize


def dot_product(vector_a, vector_b):
    return sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )


def vector_magnitude(vector):
    return math.sqrt(
        sum(value ** 2 for value in vector)
    )


def cosine_similarity(vector_a, vector_b):
    dot = dot_product(vector_a, vector_b)

    magnitude_a = vector_magnitude(vector_a)
    magnitude_b = vector_magnitude(vector_b)

    if magnitude_a == 0 or magnitude_b == 0:
        return 0

    return dot / (magnitude_a * magnitude_b)


class SearchEngine:
    def __init__(self, index):
        self.index = index

    def get_vocabulary(self):
        return list(self.index.index.keys())

    def build_vector(self, doc_id):
        vocabulary = self.get_vocabulary()

        return [
            self.index.tf_idf(doc_id, term)
            for term in vocabulary
        ]

    def build_query_vector(self, terms):
        vocabulary = self.get_vocabulary()
        total_terms = len(terms)

        if total_terms == 0:
            return []

        vector = []

        for vocabulary_term in vocabulary:
            tf = terms.count(vocabulary_term) / total_terms
            idf = self.index.inverse_document_frequency(vocabulary_term)

            vector.append(tf * idf)

        return vector

    def bm25_score(self, doc_id, query_terms, k1=1.5, b=0.75):

        document = self.index.documents[doc_id]
        document_tokens = tokenize(document["text"])

        document_length = len(document_tokens)

        if document_length == 0:
            return 0

        total_documents = len(self.index.documents)

        average_document_length = (
            sum(
                len(tokenize(text["text"]))
                for text in self.index.documents.values()
            )
            / total_documents
        )

        score = 0

        for term in query_terms:

            term = term.lower()

            document_frequency = len(
                self.index.index.get(term, set())
            )

            if document_frequency == 0:
                continue

            idf = math.log(
                (total_documents - document_frequency + 0.5)
                / (document_frequency + 0.5)
                + 1
            )

            term_frequency = document_tokens.count(term)

            numerator = term_frequency * (k1 + 1)

            denominator = (
                term_frequency
                + k1 * (
                    1
                    - b
                    + b * (
                        document_length
                        / average_document_length
                    )
                )
            )

            score += idf * (numerator / denominator)

        return score

    def search(self, query, algorithm="bm25"):
        tokens = tokenize(query)

        if not tokens:
            return []

        matching_documents = set()

        for token in tokens:
            matching_documents |= self.index.index.get(
                token,
                set()
            )

        results = []

        if algorithm == "bm25":

            for doc_id in matching_documents:
                score = self.bm25_score(
                    doc_id,
                    tokens
                )

                results.append((doc_id, score))

        elif algorithm == "tfidf":

            query_vector = self.build_query_vector(tokens)

            for doc_id in matching_documents:
                document_vector = self.build_vector(doc_id)

                score = cosine_similarity(
                    query_vector,
                    document_vector
                )

                results.append((doc_id, score))

        else:
            raise ValueError(
                f"Unknown ranking algorithm: {algorithm}"
            )

        results.sort(
            key=lambda result: result[1],
            reverse=True
        )

        return results