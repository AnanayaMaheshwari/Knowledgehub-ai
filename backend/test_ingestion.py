
from getpass import getpass

from app.services.supabase_service import get_user_supabase_client
from app.services.document_ingestion_service import process_document

DOCUMENT_ID = "ca3581dd-a6e2-4bb9-b23e-79169446777b"


def main():
    access_token = getpass("Enter your Supabase access token: ")

    supabase = get_user_supabase_client(access_token)

    result = process_document(supabase, DOCUMENT_ID)

    print("\nProcessing result:")
    print(result)


if __name__ == "__main__":
    main()
