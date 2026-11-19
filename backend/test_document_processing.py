
from getpass import getpass

from app.services.supabase_service import get_user_supabase_client
from app.services.document_processor import extract_document_text
from app.services.text_chunker import create_document_chunks

BUCKET_NAME = "knowledgehub-documents"

DOCUMENT_ID = "ca3581dd-a6e2-4bb9-b23e-79169446777b"


def main():
    access_token = getpass("Enter your Supabase access token: ")

    supabase = get_user_supabase_client(access_token)

    # 1. Retrieve document metadata
    response = (
        supabase.table("documents")
        .select("id, filename, file_type, storage_path")
        .eq("id", DOCUMENT_ID)
        .single()
        .execute()
    )

    document = response.data

    print("\nDocument:", document["filename"])

    # 2. Download original file from private Storage
    file_bytes = (
        supabase.storage
        .from_(BUCKET_NAME)
        .download(document["storage_path"])
    )

    print("File downloaded successfully.")

    # 3. Extract text
    extracted_text = extract_document_text(
        file_bytes,
        document["file_type"]
    )

    print("Text extraction completed.")
    print("Extracted characters:", len(extracted_text))

    # 4. Split extracted text into chunks
    chunks = create_document_chunks(extracted_text)

    print("Total chunks:", len(chunks))

    # 5. Display first chunk
    if chunks:
        print("\nFirst chunk:")
        print(chunks[0]["content"])

        print("\nChunk metadata:")
        print({
            "chunk_index": chunks[0]["chunk_index"],
            "page_number": chunks[0]["page_number"]
        })


if __name__ == "__main__":
    main()
