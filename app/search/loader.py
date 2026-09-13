from pathlib import Path
from app.search.pdf_loader import load_pdf_pages


def load_documents(directory):
    documents = {}
    directory_path = Path(directory)

    for file_path in directory_path.iterdir():

        if file_path.suffix.lower() == ".txt":
            with open(file_path, "r", encoding="utf-8") as file:
                documents[file_path.name] = {
                    "page": None,
                    "text": file.read()
                }

        elif file_path.suffix.lower() == ".pdf":
            pages = load_pdf_pages(file_path)

            for page in pages:
                document_id = f"{file_path.name}#page={page['page']}"

                documents[document_id] = {
                    "page": page["page"],
                    "text": page["text"]
                }

    return documents


def load_document(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".txt":
        with open(file_path, "r", encoding="utf-8") as file:
            return {
                file_path.name: {
                    "page": None,
                    "text": file.read()
                }
            }

    elif file_path.suffix.lower() == ".pdf":
        pages = load_pdf_pages(file_path)

        return {
            f"{file_path.name}#page={page['page']}": {
                "page": page["page"],
                "text": page["text"]
            }
            for page in pages
        }

    return {}