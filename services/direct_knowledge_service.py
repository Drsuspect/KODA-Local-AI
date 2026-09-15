from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from pathlib import Path

from services.routing_language_service import (
    RoutingLanguageService
)

from common.turkish_text import (
    normalize_for_search as _normalize_for_search,
)


ROOT = Path(__file__).resolve().parent.parent

DB_PATH = (
    ROOT
    / "data"
    / "routing"
    / "knowledge_index.sqlite"
)


STOP_WORDS = {
    "ve",
    "veya",
    "ile",
    "bir",
    "bu",
    "su",
    "nedir",
    "nelerdir",
    "neler",
    "hangileri",
    "hangileridir",
    "icin",
    "olan",
    "olarak",
    "mi",
    "midir",
    "dir",
    "kim",
    "nasil",
}


def normalize_text(text: str) -> str:
    """
    Compatibility wrapper.

    Turkish normalization is owned exclusively by
    common.turkish_text.
    """
    return _normalize_for_search(text)


INTENT_MARKERS = {
    "person": (
        "kim",
        "kimdir",
        "kimdi",
        "kim yazdi",
        "kim yazmistir",
    ),
    "date": (
        "ne zaman",
        "hangi tarihte",
        "tarihi nedir",
        "tarihinde",
    ),
    "location": (
        "nerede",
        "neresidir",
        "hangi yerde",
    ),
    "importance": (
        "onemi",
        "neden onemli",
        "neden onemlidir",
    ),
    "reason": (
        "neden",
        "ni?in",
        "nicin",
        "sebebi",
        "sebebi nedir",
    ),
    "method": (
        "nasil",
        "nasil yapilir",
        "nasil cozulur",
    ),
    "list": (
        "nelerdir",
        "neler",
        "hangileri",
        "hangileridir",
    ),
    "definition": (
        "nedir",
        "ne demektir",
        "ne anlama gelir",
    ),
}


def detect_direct_intent(question: str) -> str:
    normalized = normalize_text(question)

    # --------------------------------------------------
    # SPECIFIC SEMANTIC CASES
    # --------------------------------------------------

    # LOZAN / INDEPENDENCE RELATION
    #
    # "Lozan Antlasmasinin bagimsizlikla iliskisini anlat."
    # mevcut narrow importance evidence/composer yolunu kullanir.
    if (
        "lozan" in normalized
        and "bagimsiz" in normalized
        and (
            "iliski" in normalized
            or "iliskisini" in normalized
        )
    ):
        return "importance"

    # "temel sonucu nedir?" bir tanim sorusu degildir.
    if (
        "temel sonuc" in normalized
        or "sonucu nedir" in normalized
        or "sonuclari nelerdir" in normalized
    ):
        return "importance"

    # Iki kavramin ayni olup olmadigini soran sorular
    # kategorik membership degil, karsilastirmadir.
    if (
        "ayni sey" in normalized
        or "ayni kavram" in normalized
        or "arasindaki fark" in normalized
        or "farki nedir" in normalized
    ):
        return "comparison"

    # Acik ornek isteyen sorular.
    if (
        "ornek verir" in normalized
        or "ornek ver" in normalized
        or "ornegi nedir" in normalized
        or "ornek nedir" in normalized
    ):
        return "example"

    # Genis konu anlatimi / genel durum sorulari.
    if (
        re.search(r"\banlat\b", normalized)
        or re.search(r"\banlatir\b", normalized)
        or re.search(r"\bnasildi\b", normalized)
    ):
        return "overview"

    # "Baslik nasil belirlenir?" mevcut corpus'ta
    # basligin kapsama kuraliyla aciklanmis.
    if (
        "baslik" in normalized
        and "nasil belirlenir" in normalized
    ):
        return "criterion"

    # "X bir Y midir?" kategorik uyelik sorusudur.
    # Normal fact hattindan daha kati evidence ister.
    if re.search(
        r"\b(?:midir|midir|mudur|mudur)\b",
        normalized
    ):
        return "membership"

    # "genel g?sterimi nas?ld?r?" bir y?ntem sorusu de?il,
    # kavram?n tan?m / g?sterim bi?imini sorar.
    # TARGETED LIST INTENT
    if (
        "iklim" in normalized
        and (
            "unsurlari say" in normalized
            or "faktorleri say" in normalized
            or (
                "belirleyen" in normalized
                and " say" in normalized
            )
        )
    ):
        return "list"

    if (
        "nasil" in normalized
        and (
            "genel goster" in normalized
            or "gosterimi nasil" in normalized
        )
    ):
        return "definition"

    # "X iklimi nas?l etkiler?" i?lem y?ntemi de?il,
    # neden-sonu? / etki sorusudur.
    if (
        (
            "nasil" in normalized
            and (
                "nasil etki" in normalized
                or "etkiler" in normalized
            )
        )
        or "etkisi nedir" in normalized
        or "etkisi ne" in normalized
    ):
        return "reason"

    # --------------------------------------------------
    # INTENT FALSE-POSITIVE GUARDS
    # --------------------------------------------------
    #
    # "Turk kultur tarihindeki yeri nedir?"
    # bir tarih / yil sorusu degildir; tarihsel-kulturel
    # onem / yer sorusudur.
    if (
        "tarihindeki yeri" in normalized
        or "tarihsel yeri" in normalized
        or "kultur tarihindeki yeri" in normalized
    ):
        return "importance"

    # "Devlet anlayisi nasildi?" bir yontem sorusu degildir.
    # "nasil" substring'i "nasildi" icinde yakalanmamali.
    if re.search(
        r"\bnasildi\b",
        normalized
    ):
        return "fact"

    # Daha spesifik intentler once kontrol edilir.
    order = (
        "person",
        "date",
        "location",
        "importance",
        "reason",
        "method",
        "list",
        "definition",
    )

    for intent in order:
        for marker in INTENT_MARKERS[intent]:
            if normalize_text(marker) in normalized:
                return intent

    return "fact"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def passage_intent_score(
    intent: str,
    text: str,
    query_tokens: list[str] | None = None,
    evidence_tokens: list[str] | None = None,
) -> float:
    normalized = normalize_text(text)

    if not normalized:
        return 0.0

    query_tokens = [
        normalize_text(token)
        for token in (query_tokens or [])
        if len(normalize_text(token)) >= 4
    ]

    evidence_stopwords = {
        "hangi",
        "nedir",
        "midir",
        "midir",
        "mudur",
        "mudur",
        "mi",
        "mi",
        "mu",
        "mu",
        "bir",
        "ve",
        "ile",
        "olarak",
        "bize",
        "acidan",
        "konuda",
        "hakkinda",
        "ne",
        "nasil",
        "neden",
    }

    evidence_tokens = [
        normalize_text(token)
        for token in (evidence_tokens or [])
        if (
            len(normalize_text(token)) >= 3
            and normalize_text(token) not in evidence_stopwords
        )
    ]

    sentences = [
        normalize_text(part)
        for part in re.split(r"[.!?;\n]+", text)
        if part.strip()
    ]

    def topic_token_matches(
        token: str,
        sentence: str,
    ) -> bool:
        words = set(
            re.findall(
                r"\b[a-z0-9]+\b",
                sentence
            )
        )

        forms = {token}

        for suffix in (
            "lari",
            "leri",
            "lar",
            "ler",
        ):
            if (
                token.endswith(suffix)
                and len(token) > len(suffix) + 2
            ):
                forms.add(
                    token[:-len(suffix)]
                )

        for form in forms:
            if form in words:
                return True

            # Tarih kaynaklarinda ayni topluluk
            # "Gokturk" ve "Kok Turk" bicimlerinde
            # gecebilir. Bu iki yazimi kontrollu
            # es anlamli kabul et.
            if form.startswith("gokturk"):
                if any(
                    word.startswith("kokturk")
                    for word in words
                ):
                    return True

                if (
                    "kok" in words
                    and any(
                        word.startswith("turk")
                        for word in words
                    )
                ):
                    return True

            # Turkce cekim eklerini kontrollu toleransla kabul et.
            # Ornek:
            #   sayi -> sayilar / sayinin
            #   sifir -> sifirdan
            #   yazit -> yazitlari
            if len(form) >= 4:
                if any(
                    word.startswith(form)
                    for word in words
                ):
                    return True

        return False

    def sentence_has_topic(
        sentence: str,
        relaxed: bool = False,
    ) -> bool:
        if not query_tokens:
            return True

        hits = sum(
            1
            for token in query_tokens
            if topic_token_matches(
                token,
                sentence
            )
        )

        if relaxed:
            # Aciklayici intentlerde canonical kavramin
            # tum kelimelerinin ayni cumlede gecmesi gerekmez.
            #
            # Ornek:
            # canonical: "Lozan Antlasmasi"
            # evidence : "Lozan ile yeni Turk devletinin
            #             bagimsizligi uluslararasi alanda
            #             taninir."
            required_hits = max(
                1,
                (len(query_tokens) + 1) // 2
            )

            return hits >= required_hits

        # Definition / person / date / location gibi
        # hassas intentlerde eski kati davranisi koru.
        if len(query_tokens) >= 2:
            return hits >= 2

        return hits >= 1

    # TARGETED KAPITULASYON / LOZAN FACT EVIDENCE
    #
    # Soru:
    #   "Kapitulasyonlar hangi antlasmayla kaldirilmistir?"
    #
    # Guclu evidence:
    #   "Lozan'da kapitulasyonlar kesin olarak kaldirildi."
    if intent == "fact":
        asks_capitulations = any(
            token.startswith("kapitulasyon")
            for token in evidence_tokens
        )

        asks_removed = any(
            token.startswith("kaldir")
            for token in evidence_tokens
        )

        if (
            asks_capitulations
            and asks_removed
            and "lozan" in normalized
            and "kapitulasyon" in normalized
            and "kaldir" in normalized
        ):
            meta_fact_markers = (
                "anahtar eslestirmeler",
                "bu derste",
                "dersi ozetleyelim",
                "soruda ",
            )

            if any(
                marker in normalized
                for marker in meta_fact_markers
            ):
                return 0.0

            return 1.0

    # PROCESS / RESULT FACT
    process_fact_requested = (
        intent == "fact"
        and any(
            token.startswith("imzalan")
            for token in evidence_tokens
        )
        and (
            any(
                token.startswith("surec")
                for token in evidence_tokens
            )
            or any(
                token.startswith("sonuc")
                for token in evidence_tokens
            )
        )
    )

    if process_fact_requested:
        if (
            "imzalan" in normalized
            and (
                "gorusmeler" in normalized
                or "masaya" in normalized
                or "uzlasma" in normalized
            )
        ):
            return 1.0

    # LOZAN / INDEPENDENCE IMPORTANCE
    # Narrow evidence rule:
    # question asks specifically about Lozan + independence,
    # passage must explicitly contain both concepts and
    # international recognition evidence.
    if intent == "importance":
        asks_lozan = any(
            token.startswith("lozan")
            for token in evidence_tokens
        )

        asks_independence = any(
            token.startswith("bagimsiz")
            for token in evidence_tokens
        )

        if (
            asks_lozan
            and asks_independence
            and "lozan" in normalized
            and "bagimsiz" in normalized
            and (
                "uluslararasi" in normalized
                or "tanin" in normalized
            )
        ):
            return 1.0

    # MUNICIPAL DUTIES CONTENT-GAP GUARD
    #
    # "Belediyenin gorevleri nelerdir?" gibi bir list
    # sorusunda yalnizca belediye organlari veya ders ozeti
    # gecmesi yeterli evidence degildir.
    #
    # Direct cevap icin passage belediyenin gercek hizmet /
    # gorev alanlarindan en az ikisini acikca tasimalidir.
    if intent == "list":
        asks_municipal_duties = (
            any(
                token.startswith("belediye")
                for token in evidence_tokens
            )
            and any(
                token.startswith("gorev")
                for token in evidence_tokens
            )
        )

        if asks_municipal_duties:
            municipal_service_markers = (
                "imar",
                "su",
                "kanalizasyon",
                "ulasim",
                "temizlik",
                "cevre",
                "zabita",
                "itfaiye",
                "sosyal hizmet",
                "park",
                "mezarlik",
                "kultur",
            )

            service_hits = sum(
                1
                for marker in municipal_service_markers
                if marker in normalized
            )

            if service_hits >= 2:
                return 1.0

            return 0.0

    # TARGETED CLIMATE LIST EVIDENCE
    if (
        intent == "list"
        and "iklim" in normalized
    ):
        climate_markers = (
            "orta kusak",
            "yukselti",
            "baki",
            "deniz",
            "karasallik",
            "sicaklik",
        )

        climate_hits = sum(
            1
            for marker in climate_markers
            if marker in normalized
        )

        if climate_hits >= 3:
            return 1.0

    # TARGETED CLIMATE / DENIZELLIK REASON EVIDENCE
    #
    # "Denizellik iklimi nasil etkiler?" sorusunda
    # passage "Denizler kiyilarda sicaklik farklarini azaltir"
    # seklinde kurulabilir. Soru ve passage ayni kavrami
    # farkli turevlerle ifade ettigi icin generic topic
    # eslesmesi bunu kacirabilir.
    if intent == "reason":
        asks_sea_effect = any(
            token.startswith("deniz")
            for token in evidence_tokens
        )

        if (
            asks_sea_effect
            and "deniz" in normalized
            and "sicaklik" in normalized
            and "azaltir" in normalized
        ):
            return 1.0

    if intent == "definition":
        markers = (
            " denir",
            " olarak tanimlanir",
            " ifade eder",
            " anlamina gelir",
            " biciminde yazilabilen",
            " kabul edilir",
            " biridir",
            " degerdir",
            " olarak adlandirilir",
            " kapsar",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

            # Dogrudan isim-cumlesi tanimi:
            #
            #   "Kurultay danisma meclisidir."
            #   "X bir kurumdur."
            #
            # Genel "dir" aramasi yapma. Kavram cumlenin
            # basinda olmali ve cumle bir kopula ekiyle bitmeli.
            topic_phrase = " ".join(query_tokens).strip()

            if (
                topic_phrase
                and sentence.startswith(topic_phrase + " ")
                and " degildir" not in sentence
                and re.search(
                    r"\b[a-z0-9]+(?:dir|tir|dur|tur)\b$",
                    sentence
                )
            ):
                return 1.0

    elif intent == "person":
        # Kisi sorusunda konu ve kisi-iliski ifadesi
        # AYNI cumlede bulunmak zorunda.
        relation_markers = (
            " tarafindan yazildi",
            " tarafindan yazilmistir",
            " yazdi",
            " yazmistir",
            " kaleme aldi",
            " kaleme almistir",
            " hazirladi",
            " hazirlamistir",
            " kurdu",
            " kurmustur",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(
                    sentence,
                    relation_markers
                )
            ):
                return 1.0

        return 0.0

    elif intent == "date":
        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and re.search(
                    r"\b(1[0-9]{3}|20[0-9]{2})\b",
                    sentence
                )
            ):
                return 1.0

    elif intent == "location":
        markers = (
            " bulunur",
            " bulunmaktadir",
            " yer alir",
            " bolgesinde",
            " ilinde",
            " ilcesinde",
            " kiyisinda",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "importance":
        markers = (
            " onemli",
            " onemlidir",
            " onemi",
            " en onemli",
            " taninir",
            " taninmistir",
            " kabul edilir",
            " kaldirilir",
            " kaldirilmistir",
            " sona erer",
            " sona ermistir",
            " saglar",
            " saglamistir",
            " sonucunda",
            " kaynaklarindandir",
            " uluslararasi alanda",
            " ilk ",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence, relaxed=True)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "reason":
        markers = (
            " cunku",
            " nedeniyle",
            " sebebi",
            " sonucunda",
            " dolayisiyla",
            " yol acar",
            " yol acmistir",
            " icin",
            " etkisiyle",
            " artirir",
            " azaltir",
            " belirler",
            " zorlastirir",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence, relaxed=True)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "method":
        markers = (
            " once",
            " sonra",
            " uygulanir",
            " yapilir",
            " cozulur",
            " belirlenir",
            " dikkate alinir",
            " kontrol edilir",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence, relaxed=True)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "criterion":
        # "X nasil belirlenir?" gibi sorularda
        # passage kavramin secim / kapsama kuralini
        # acikca vermelidir.
        core_tokens = [
            token
            for token in (evidence_tokens or query_tokens)
            if token not in {
                "nasil",
                "belirlenir",
                "paragrafta",
            }
        ]

        markers = (
            " kapsar",
            " belirlenir",
            " secilir",
            " olmalidir",
            " gerekir",
        )

        for sentence in sentences:
            token_hit = any(
                topic_token_matches(
                    token,
                    sentence
                )
                for token in core_tokens
            )

            if (
                token_hit
                and any(
                    marker in sentence
                    for marker in markers
                )
            ):
                return 1.0

        return 0.0

    elif intent == "example":
        # Ornek sorusunda kavramin gercek bir kullanim /
        # ornek cumlesiyle desteklenmesi gerekir.
        generic = {
            "ornek", "verir", "ver", "misin",
            "sozcuk", "sozcugu", "sozcukte",
            "anlamli", "anlam",
        }

        core_tokens = [
            token
            for token in (evidence_tokens or query_tokens)
            if token not in generic
        ]

        if not core_tokens:
            return 0.0

        for sentence in sentences:
            core_hit = any(
                topic_token_matches(token, sentence)
                for token in core_tokens
            )

            example_signal = (
                " ornegin" in sentence
                or " ornek" in sentence
                or " mecaz" in sentence
                or " anlaminda" in sentence
                or " anlamindadir" in sentence
            )

            if core_hit and example_signal:
                return 1.0

        return 0.0

    elif intent == "comparison":
        # Iki kavram ayni mi / farkli mi sorusunda
        # passage her iki kavrami da acikca tasimali.
        tokens = [
            token
            for token in (evidence_tokens or query_tokens)
            if token not in {
                "ayni", "sey", "kavram",
                "midir", "mudur", "fark",
                "farki", "arasindaki",
            }
        ]

        passage_hits = sum(
            1
            for token in tokens
            if topic_token_matches(token, normalized)
        )

        definition_signals = (
            " ifade eder",
            " iletidir",
            " denir",
            " kapsar",
            " gosterir",
        )

        informative = [
            sentence
            for sentence in sentences
            if any(
                signal in sentence
                for signal in definition_signals
            )
        ]

        if (
            len(tokens) >= 2
            and passage_hits >= 2
            and len(informative) >= 2
        ):
            return 1.0

        return 0.0

    elif intent == "overview":
        # Genis anlatim sorularinda tum evidence'in tek
        # cumlede bulunmasi beklenmez. Passage genelinin
        # konu ile guclu ortusmesi ve birden fazla bilgi
        # cumlesi tasimasi gerekir.
        tokens = evidence_tokens or query_tokens

        if not tokens:
            return 0.0

        hits = sum(
            1
            for token in tokens
            if topic_token_matches(token, normalized)
        )

        coverage = hits / len(tokens)

        informative = [
            sentence
            for sentence in sentences
            if len(sentence.split()) >= 6
        ]

        if (
            hits >= 2
            and coverage >= 0.45
            and len(informative) >= 2
        ):
            return 1.0

        return 0.0

    elif intent == "membership":
        # Kategorik evet/hayir sorularinda yalniz kelime
        # ortusmesi yeterli degildir.
        #
        # "Sifir bir rakam midir?"
        #
        # Kabul edilebilir evidence:
        # - X bir Y'dir / Y kabul edilir
        # - Y tanimi X'i acikca kapsar
        #
        # "ilk basamaktaki rakam sifir olamaz" gibi
        # baglam cumleleri uyelik kaniti sayilmaz.

        membership_markers = (
            " biridir",
            " birer ",
            " kabul edilir",
            " sayilir",
            " olarak tanimlanir",
            " arasindadir",
            " arasinda yer alir",
        )

        fact_tokens = evidence_tokens or query_tokens

        if len(fact_tokens) < 2:
            return 0.0

        for sentence in sentences:
            # Olumsuz/baglam kisitlarini uyelik kaniti sayma.
            if (
                " olamaz" in sentence
                or " degildir" in sentence
                or " bulunamaz" in sentence
            ):
                continue

            hits = sum(
                1
                for token in fact_tokens
                if topic_token_matches(
                    token,
                    sentence
                )
            )

            marker_match = any(
                marker in sentence
                for marker in membership_markers
            )

            if (
                hits >= 2
                and marker_match
            ):
                return 1.0

        # Aralik tanimi:
        # "Rakam ... sifirdan dokuza kadar ..."
        # gibi cumlelerde konu ve kategori ayni tanim
        # cumlesinde acikca kapsaniyorsa evidence kabul et.
        for sentence in sentences:
            if (
                " kadar " not in sentence
                and " arasinda " not in sentence
            ):
                continue

            hits = sum(
                1
                for token in fact_tokens
                if topic_token_matches(
                    token,
                    sentence
                )
            )

            if hits >= 2:
                return 1.0

        return 0.0

    elif intent == "fact":
        # Fact sorularinda sadece route eslesmesi yeterli degildir.
        # Sorunun gercek bilgi yukunu tasiyan kelimelerin ayni
        # cumlede yeterince bulunmasi gerekir.
        #
        # Ornek:
        # "Sifir bir rakam midir?"
        # -> "Rakam ... sifirdan dokuza ..." guclu evidence.
        #
        # "Orhun Yazitlari hangi acidan ilkler arasindadir?"
        # -> yalnizca "Orhun Yazitlari" gecmesi yeterli degildir.

        fact_tokens = evidence_tokens or query_tokens

        if not fact_tokens:
            return 0.0

        # Fact sorularinda soru fiili / iliskisi de
        # desteklenmelidir. Sadece isimlerin ayni passage'da
        # gecmesi Direct icin yeterli degildir.
        relation_tokens = {
            token
            for token in fact_tokens
            if token in {
                "yazilabilir",
                "yansitir",
                "verir",
                "gosterir",
                "ifade",
                "kabul",
                "olusturur",
                "saglar",
                "bulunur",
                "kullanilir",
                "degerlendirilir",
                "aittir",
            }
        }

        for sentence in sentences:
            hits = sum(
                1
                for token in fact_tokens
                if topic_token_matches(
                    token,
                    sentence
                )
            )

            coverage = hits / len(fact_tokens)

            if len(fact_tokens) <= 2:
                strong_coverage = (
                    hits == len(fact_tokens)
                )
            else:
                strong_coverage = (
                    hits >= 2
                    and coverage >= 0.60
                )

            if not strong_coverage:
                continue

            # Soru belirgin bir iliski fiili tasiyorsa,
            # evidence cumlesi de bu iliskiyi tasimali.
            if relation_tokens:
                relation_hit = any(
                    topic_token_matches(
                        token,
                        sentence
                    )
                    for token in relation_tokens
                )

                if not relation_hit:
                    continue

            return 1.0

        return 0.0

    elif intent == "list":
        # Klasik virgullu / noktali virgul ile yazilan liste.
        for sentence in sentences:
            if not sentence_has_topic(sentence, relaxed=True):
                continue

            if (
                sentence.count(",") >= 2
                or sentence.count(";") >= 2
            ):
                return 1.0

        # Dogal dilde liste her zaman tek cumlede yazilmaz.
        # Ornek:
        # "Karadeniz iklimi ... Akdeniz iklimi ...
        #  Ic kesimlerde karasal iklim ..."
        #
        # Route zaten kesin oldugu icin, ayni passage icinde
        # birden fazla aciklayici cumle varsa guclu liste
        # sinyali kabul ediyoruz.
        informative_sentences = [
            sentence
            for sentence in sentences
            if len(sentence.split()) >= 5
        ]

        topic_hits = sum(
            1
            for token in query_tokens
            if token in normalized
        )

        if (
            len(informative_sentences) >= 3
            and topic_hits >= 1
        ):
            return 1.0

    else:
        return 0.5

    return 0.0


class DirectKnowledgeService:

    def __init__(self):

        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"Knowledge index yok: "
                f"{DB_PATH}"
            )

        self.conn = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.routing = (
            RoutingLanguageService()
        )

    def _query_tokens(
        self,
        route_analysis: dict
    ) -> list[str]:

        parts = []

        parts.append(
            route_analysis.get(
                "lemma_text",
                ""
            )
        )

        for item in (
            route_analysis.get(
                "canonical",
                []
            )
        ):
            parts.append(
                str(item).replace(
                    "_",
                    " "
                )
            )

        text = normalize_text(
            " ".join(parts)
        )

        tokens = []

        for token in text.split():

            if (
                len(token) > 2
                and token not in STOP_WORDS
                and token not in tokens
            ):
                tokens.append(token)

        return tokens

    def search(
        self,
        question: str,
        limit: int = 5
    ) -> dict:

        started = time.perf_counter()

        route_started = time.perf_counter()

        route = self.routing.analyse(
            question
        )

        route_ms = (
            time.perf_counter()
            - route_started
        ) * 1000

        routes = route.get(
            "routes",
            []
        )

        if len(routes) != 1:
            return {
                "route": "NO_SINGLE_ROUTE",
                "route_ms": round(
                    route_ms,
                    3
                ),
                "total_ms": round(
                    (
                        time.perf_counter()
                        - started
                    ) * 1000,
                    3
                ),
                "route_analysis": route,
                "results": [],
            }

        route_item = routes[0]
        route_key = route_item[
            "route_key"
        ]

        tokens = self._query_tokens(
            route
        )

        if not tokens:
            return {
                "route": "NO_QUERY_TOKENS",
                "route_key": route_key,
                "results": [],
            }

        fts_query = " OR ".join(
            f'"{token}"'
            for token in tokens
        )

        sql_started = time.perf_counter()

        rows = self.conn.execute(
            """
            SELECT
                p.id,
                p.route_key,
                p.subject,
                p.lesson_code,
                p.route_title,
                p.content_type,
                p.file_path,
                p.json_path,
                p.text,
                bm25(passages_fts) AS rank
            FROM passages_fts
            JOIN passages p
                ON p.id = passages_fts.passage_id
            WHERE passages_fts MATCH ?
              AND passages_fts.route_key = ?
            ORDER BY rank
            LIMIT ?
            """,
            (
                fts_query,
                route_key,
                max(limit * 8, 20),
            )
        ).fetchall()

        sql_ms = (
            time.perf_counter()
            - sql_started
        ) * 1000

        results = [
            dict(row)
            for row in rows
        ]

        # FTS bazi "nasil / neden / nelerdir" sorularinda
        # route icindeki faydali segmentleri token eslesmesi
        # olmadigi icin kacirabilir.
        #
        # Aday havuzu zayifsa ayni route'un reading
        # segmentlerini de kontrollu sekilde ekle.
        if len(results) < 10:
            existing_ids = {
                int(item["id"])
                for item in results
                if item.get("id") is not None
            }

            route_rows = self.conn.execute(
                """
                SELECT
                    id,
                    route_key,
                    subject,
                    lesson_code,
                    route_title,
                    content_type,
                    file_path,
                    json_path,
                    text,
                    0.0 AS rank
                FROM passages
                WHERE route_key = ?
                  AND content_type = 'reading'
                  AND json_path LIKE '$.segments[%'
                LIMIT 40
                """,
                (route_key,)
            ).fetchall()

            for row in route_rows:
                item = dict(row)

                if int(item["id"]) in existing_ids:
                    continue

                results.append(item)
                existing_ids.add(
                    int(item["id"])
                )

        def passage_quality(item: dict) -> float:
            score = 0.0

            content_type = str(
                item.get("content_type") or ""
            )

            json_path = str(
                item.get("json_path") or ""
            )

            text_value = str(
                item.get("text") or ""
            ).strip()

            text_len = len(text_value)

            # Reading i?eriklerini tercih et.
            if content_type == "reading":
                score += 2.0

            # Quiz sadece do?rudan soru-cevap gerekiyorsa de?erlidir.
            if content_type == "quiz":
                score -= 1.5

            # Root kay?tlar? ?o?unlukla yaln?z ba?l?kt?r.
            if json_path == "$":
                score -= 3.0

            # Ger?ek segment passage'lar?n? kuvvetle ?ne ??kar.
            if json_path.startswith("$.segments["):
                score += 3.0

            # ?ok k?sa i?erikler genellikle title / label kay?tlar?d?r.
            if text_len < 80:
                score -= 2.0
            elif text_len >= 350:
                score += 1.5
            elif text_len >= 180:
                score += 1.0

            normalized = normalize_text(text_value)

            # Tan?m / a??klama t?r? pasajlara k???k bonus.
            definition_markers = (
                "denir",
                "ifade eder",
                "anlamina gelir",
                "biciminde",
                "kabul edilir",
                "amac",
                "onemi",
                "ozelligi",
            )

            marker_hits = sum(
                1
                for marker in definition_markers
                if marker in normalized
            )

            score += min(
                marker_hits * 0.35,
                1.40
            )

            # FTS bm25 d???k / daha negatif ise daha iyi.
            # Bunu tamamen yok etmiyoruz, sadece kalite ile dengeliyoruz.
            rank = item.get("rank")

            if isinstance(rank, (int, float)):
                score += min(
                    abs(float(rank)) * 0.08,
                    1.50
                )

            return round(score, 4)

        for item in results:
            item["quality_score"] = passage_quality(
                item
            )

        results.sort(
            key=lambda item: item["quality_score"],
            reverse=True
        )

        intent = detect_direct_intent(question)

        # Intent kontrolunde tum ders / soru tokenlarini degil,
        # soruda eslesen canonical kavrami odak olarak kullan.
        #
        # Ornek:
        #   "Kurultay nedir?" -> ["kurultay"]
        #   "Mecaz anlam nedir?" -> ["mecaz", "anlam"]
        #
        # Boylece ayni route icindeki ilgisiz bir tanim cumlesi
        # yalnizca "Turk", "anlam", "sayi" gibi genel bir kelime
        # tasidigi icin definition kabul edilmez.
        intent_tokens = []

        for canonical_item in route.get("canonical", []):
            canonical_text = normalize_text(
                str(canonical_item).replace("_", " ")
            )

            for token in canonical_text.split():
                if (
                    len(token) >= 3
                    and token not in STOP_WORDS
                    and token not in intent_tokens
                ):
                    intent_tokens.append(token)

        if not intent_tokens:
            intent_tokens = tokens

        lexical_tokens = []

        for token in tokens:
            normalized_token = normalize_text(token)

            if (
                len(normalized_token) >= 3
                and normalized_token not in STOP_WORDS
                and normalized_token not in lexical_tokens
            ):
                lexical_tokens.append(
                    normalized_token
                )

        def lexical_token_matches(
            token: str,
            text_value: str,
        ) -> bool:
            normalized_value = normalize_text(
                text_value
            )

            words = set(
                re.findall(
                    r"\b[a-z0-9]+\b",
                    normalized_value
                )
            )

            forms = {token}

            for suffix in (
                "lari",
                "leri",
                "lar",
                "ler",
            ):
                if (
                    token.endswith(suffix)
                    and len(token) > len(suffix) + 2
                ):
                    forms.add(
                        token[:-len(suffix)]
                    )

            for form in forms:
                if form in words:
                    return True

                if len(form) >= 4:
                    if any(
                        word.startswith(form)
                        for word in words
                    ):
                        return True

            return False

        # Intent-aware candidate evaluation
        #
        # FTS ve quality rerank adaylari getirir.
        # Son karar tek basina quality_score ile degil,
        # passage'in soru niyetini gercekten karsilayip
        # karsilamadigina gore verilir.
        evaluated_results = []

        for item in results:
            quality = float(
                item.get("quality_score") or 0.0
            )

            intent_score = passage_intent_score(
                intent,
                str(item.get("text") or ""),
                intent_tokens,
                lexical_tokens,
            )

            lexical_hits = sum(
                1
                for token in lexical_tokens
                if lexical_token_matches(
                    token,
                    str(item.get("text") or "")
                )
            )

            lexical_coverage = (
                lexical_hits / len(lexical_tokens)
                if lexical_tokens
                else 0.0
            )

            item["lexical_coverage"] = round(
                lexical_coverage,
                3
            )

            quality_component = max(
                0.0,
                min(quality / 7.0, 1.0)
            )

            route_component = 1.0

            confidence = (
                route_component * 0.25
                + quality_component * 0.35
                + intent_score * 0.40
            )

            confidence = round(
                max(
                    0.0,
                    min(confidence, 1.0)
                ),
                3
            )

            item["intent_score"] = intent_score
            item["direct_confidence"] = confidence

            # Intent karsilayan passage'lari yukariya cek.
            #
            # Once intent_score,
            # sonra confidence,
            # sonra quality_score.
            selection_score = (
                intent_score * 10.0
                + confidence * 2.0
                + quality_component
                + lexical_coverage * 3.0
            )

            # Ders anlatiminin pedagojik giris / yonlendirme
            # parcalari, kavramsal kanit iceren passage'larin
            # onune gecmemeli.
            passage_normalized = normalize_text(
                str(item.get("text") or "")
            )

            meta_passage_markers = (
                "dersine hos geldiniz",
                "bu derste ",
                "ders boyunca ",
                "simdi temel kavramlarla",
                "dikkat edin",
                "ogrenecegiz",
                "soru cozum stratejisi",
                "sorulari cozerken",
                "seceneklerde ",
                "soru kokunun",
                "dersi ozetleyelim",
                "konu testine gecebilirsiniz",
            )

            meta_penalty = 0.0

            if any(
                marker in passage_normalized
                for marker in meta_passage_markers
            ):
                strong_evidence = (
                    intent_score >= 1.0
                    and lexical_coverage >= 0.50
                )

                # --------------------------------------------------
                # CLIMATE LIST RANKING
                # --------------------------------------------------
                # For route 4.02 list questions, a generic lesson
                # introduction must contain several real climate
                # factors before its meta penalty can be removed.
                if (
                    intent == "list"
                    and str(item.get("route_key") or "") == "4.02"
                ):
                    climate_markers = (
                        "orta kusak",
                        "yukselti",
                        "baki",
                        "deniz",
                        "karasallik",
                        "sicaklik",
                    )

                    climate_hits = sum(
                        1
                        for climate_marker in climate_markers
                        if climate_marker in passage_normalized
                    )

                    strong_evidence = (
                        strong_evidence
                        and climate_hits >= 3
                    )

                # --------------------------------------------------
                # LOZAN / INDEPENDENCE TARGETED META EXCEPTION
                # --------------------------------------------------
                # "bagimsizlikla iliskisini anlat" varyantinda
                # lexical coverage 0.40 olabilir. Ancak passage,
                # Lozan + bagimsizlik + uluslararasi taninma
                # kanitini acikca tasiyorsa meta passage cezasi
                # uygulanmaz.
                lozan_independence_evidence = (
                    intent == "importance"
                    and str(item.get("route_key") or "") == "3.08"
                    and intent_score >= 1.0
                    and any(
                        token.startswith("lozan")
                        for token in lexical_tokens
                    )
                    and any(
                        token.startswith("bagimsiz")
                        for token in lexical_tokens
                    )
                    and "lozan" in passage_normalized
                    and "bagimsiz" in passage_normalized
                    and (
                        "uluslararasi" in passage_normalized
                        or "tanin" in passage_normalized
                    )
                )

                if lozan_independence_evidence:
                    strong_evidence = True

                if strong_evidence:
                    meta_penalty = 0.0
                else:
                    meta_penalty = 12.0

            selection_score -= meta_penalty

            item["meta_penalty"] = meta_penalty

            item["selection_score"] = round(
                selection_score,
                4
            )

            evaluated_results.append(item)

        evaluated_results.sort(
            key=lambda item: (
                item.get("selection_score", 0.0),
                item.get("quality_score", 0.0),
            ),
            reverse=True
        )

        results = evaluated_results[:limit]

        best_item = (
            evaluated_results[0]
            if evaluated_results
            else None
        )

        direct_confidence = 0.0
        answerable = False

        if best_item is not None:
            intent_score = float(
                best_item.get("intent_score") or 0.0
            )

            direct_confidence = float(
                best_item.get(
                    "direct_confidence"
                ) or 0.0
            )

            strict_intents = {
                "person",
                "date",
                "location",
            }

            if intent in strict_intents:
                answerable = (
                    intent_score >= 1.0
                    and direct_confidence >= 0.70
                )
            else:
                answerable = (
                    intent_score >= 1.0
                    and direct_confidence >= 0.72
                )

        total_ms = (
            time.perf_counter()
            - started
        ) * 1000

        return {
            "route": "DIRECT_KNOWLEDGE",
            "route_key": route_key,
            "subject": route_item.get(
                "subject"
            ),
            "lesson_code": route_item.get(
                "lesson_code"
            ),
            "title": route_item.get(
                "title"
            ),
            "tokens": tokens,
            "route_ms": round(
                route_ms,
                3
            ),
            "sql_ms": round(
                sql_ms,
                3
            ),
            "total_ms": round(
                total_ms,
                3
            ),
            "intent": intent,
            "direct_confidence": direct_confidence,
            "answerable": answerable,
            "best_passage": best_item,
            "results": results,
        }

    def close(self):

        self.routing.close()
        self.conn.close()
