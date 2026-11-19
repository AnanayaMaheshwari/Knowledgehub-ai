
from getpass import getpass

from app.services.supabase_service import get_user_supabase_client
from app.services.rag_service import answer_question


def main():
    access_token = getpass("Enter your Supabase access token: ")

    supabase = get_user_supabase_client(access_token)

    question = input("\nAsk a question about your documents: ")

    result = answer_question(
        supabase=supabase,
        question=question,
        match_count=5
    )

    print("\n" + "=" * 60)
    print("KNOWLEDGEHUB AI ANSWER")
    print("=" * 60)

    print("\nAnswer:")
    print(result["answer"])

    print("\nSources:")
    for source in result["sources"]:
        print(f"\n{source['source_label']}")
        print("Document:", source["filename"])
        print("Page:", source["page_number"])
        print("Similarity:", source["similarity"])


if __name__ == "__main__":
    main()
