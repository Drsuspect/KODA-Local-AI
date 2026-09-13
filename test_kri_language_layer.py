import json

from services.routing_language_service import (
    RoutingLanguageService
)

questions = [
    "\u00dclkemizin iklim \u00f6zellikleri nelerdir?",
    "T\u00fcrkiye'nin iklim \u00f6zellikleri nelerdir?",
    "Orhun Yaz\u0131tlar\u0131n\u0131n T\u00fcrk tarihi a\u00e7\u0131s\u0131ndan \u00f6nemi nedir?",
    "Orhun kitabelerini kim yazm\u0131\u015ft\u0131r?",
    "Lozan Bar\u0131\u015f Antla\u015fmas\u0131n\u0131n \u00f6nemi nedir?",
    "Atat\u00fcrk'\u00fcn T\u00fcrk tarihi a\u00e7\u0131s\u0131ndan \u00f6nemi nedir?",
    "Rasyonel say\u0131lar nedir?",
    "Kelimede anlam nedir?",
    "Paragraf sorular\u0131 nas\u0131l \u00e7\u00f6z\u00fcl\u00fcr?",
]

service = RoutingLanguageService()

try:
    for q in questions:
        result = service.analyse(q)

        print("\n" + "=" * 78)
        print("SORU:", q)
        print("LEMMAS:", result["lemmas"])
        print("CANONICAL:", result["canonical"])
        print("ROUTE_KEYS:", result["route_keys"])

        for route in result["routes"]:
            print(
                "ROUTE:",
                route["route_key"],
                "|",
                route["subject"],
                "|",
                route["title"]
            )

finally:
    service.close()
