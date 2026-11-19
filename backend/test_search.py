
from getpass import getpass

from app.services.supabase_service import get_user_supabase_client
from app.services.search_service import search_documents


def main():
    access_token = getpass("Enter your Supabase access token: ")

    supabase = get_user_supabase_client(access_token)

    query = input("\nAsk a question about your documents: ")

    results = search_documents(
        supabase=supabase,
        query=query,
        match_count=5
    )

    print("\nSearch Results")
    print("=" * 60)

    if not results:
        print("No relevant document chunks found.")
        return

    for index, result in enumerate(results, start=1):
        print(f"\nResult {index}")
        print("Similarity:", round(result["similarity"], 4))
        print("Document ID:", result["document_id"])
        print("Page:", result["page_number"])
        print("Content:", result["content"])


if __name__ == "__main__":
    main()
