from services.direct_knowledge_service import (
    DirectKnowledgeService
)

questions = [
    "Ülkemizin iklim özellikleri nelerdir?",
    "Türkiye'nin iklim özellikleri nelerdir?",
    "Orhun Yazıtlarının Türk tarihi açısından önemi nedir?",
    "Orhun kitabelerini kim yazmıştır?",
    "Lozan Barış Antlaşmasının önemi nedir?",
    "Rasyonel sayılar nedir?",
    "Kelimede anlam nedir?",
    "Paragraf soruları nasıl çözülür?",
]

service = DirectKnowledgeService()

try:

    for q in questions:

        result = service.search(
            q,
            limit=3
        )

        print()
        print("=" * 80)
        print("SORU:", q)

        print(
            "ROUTE:",
            result.get("route")
        )

        print(
            "ROUTE_KEY:",
            result.get("route_key")
        )

        print(
            "TITLE:",
            result.get("title")
        )

        print(
            "ROUTE_MS:",
            result.get("route_ms")
        )

        print(
            "SQL_MS:",
            result.get("sql_ms")
        )

        print(
            "TOTAL_MS:",
            result.get("total_ms")
        )

        print(
            "TOKENS:",
            result.get("tokens")
        )

        print(
            "INTENT:",
            result.get("intent")
        )

        print(
            "CONFIDENCE:",
            result.get("direct_confidence")
        )

        print(
            "ANSWERABLE:",
            result.get("answerable")
        )

        for no, item in enumerate(
            result.get("results", []),
            1
        ):

            print()
            print(
                f"SONUC {no}"
            )

            print(
                "TYPE:",
                item["content_type"]
            )

            print(
                "FILE:",
                item["file_path"]
            )

            print(
                "JSON_PATH:",
                item["json_path"]
            )

            print(
                "RANK:",
                item["rank"],
                "| QUALITY:",
                item.get("quality_score"),
                "| INTENT_SCORE:",
                item.get("intent_score"),
                "| DIRECT_CONF:",
                item.get("direct_confidence"),
                "| SELECT:",
                item.get("selection_score")
            )

            text = (
                item["text"]
                .replace("\n", " ")
            )

            print(
                "TEXT:",
                text[:700]
            )

finally:
    service.close()


