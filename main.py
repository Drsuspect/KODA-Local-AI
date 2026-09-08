from llm_core.local_model import LocalLLM
from audit.audit_logger import AuditLogger
from security.prompt_guard import PromptGuard

from rag.document_loader import DocumentLoader
from rag.chunker import TextChunker
from rag.chroma_retriever import ChromaRetriever
from common.text_cleaner import clean_llm_output


APP_VERSION = "0.1.0"
DEFAULT_USER_ROLE = "research"

EXIT_COMMANDS = {
    "exit",
    "quit",
    "q",
    "çıkış",
    "cikis",
    "kapat",
}


def build_retriever(reset_collection: bool = False):
    print("📄 Dokümanlar yükleniyor...")

    loader = DocumentLoader(docs_dir="data/documents")
    documents = loader.load_documents()

    chunker = TextChunker(
        chunk_size=600,
        overlap=100
    )
    chunks = chunker.chunk_documents(documents)

    retriever = ChromaRetriever(
        chunks,
        reset_collection=reset_collection
    )

    print(f"✅ Yüklenen doküman sayısı: {len(documents)}")
    print(f"✅ Oluşturulan chunk sayısı: {len(chunks)}\n")

    return retriever


def main():
    print(f"🛡️ KODA Local AI v{APP_VERSION} started.")
    print("Çıkmak için: exit / quit / çıkış / q")
    print("ChromaDB yeniden indekslemek için: reindex\n")

    audit = AuditLogger()
    guard = PromptGuard()
    retriever = build_retriever(reset_collection=False)

    llm = LocalLLM(
        model_name="gemma3:4b",
        mode="offline"
    )

    while True:
        try:
            user_input = input("Soru: ").strip()
        except KeyboardInterrupt:
            print("\nKODA Local AI kapatıldı.")
            break

        if not user_input:
            continue

        normalized_input = user_input.lower().strip()

        if normalized_input in EXIT_COMMANDS:
            print("KODA Local AI kapatıldı.")
            break

        if normalized_input == "reindex":
            retriever = build_retriever(reset_collection=True)
            print("🧠 ChromaDB yeniden indekslendi.")
            continue

        safety_result = guard.check(user_input)

        if not safety_result["allowed"]:
            print(f"⛔ Güvenlik engeli: {safety_result['reason']}")
            audit.log_blocked_query(
                question=user_input,
                reason=safety_result["reason"]
            )
            continue

        context = retriever.retrieve(user_input)

        raw_response = llm.generate(
            question=user_input,
            context=context
        )

        response = clean_llm_output(raw_response)

        audit.log_interaction(
            question=user_input,
            response=response,
            user_role=DEFAULT_USER_ROLE
        )

        print("\nKODA:", response)

        if context:
            print("\n📌 Kullanılan kaynak bağlam:")
            print(context[:1000])
        else:
            print(
                "\n⚠️ Doküman bağlamı bulunamadı, "
                "model genel bilgisiyle cevap verdi."
            )

        print("-" * 80)


if __name__ == "__main__":
    main()
