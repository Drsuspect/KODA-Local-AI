from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer


class ChromaRetriever:
    def __init__(
        self,
        chunks: list[dict],
        db_dir: str = "chroma_db",
        collection_name: str = "koda_docs",
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        reset_collection: bool = False,
    ):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)

        self.collection_name = collection_name
        self.model = SentenceTransformer(model_name)

        self.client = chromadb.PersistentClient(path=str(self.db_dir))

        if reset_collection:
            try:
                self.client.delete_collection(name=self.collection_name)
                print("Eski ChromaDB collection silindi.")
            except Exception:
                print("Silinecek mevcut ChromaDB collection bulunamadÄ±.")

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "KODA Secure LLM document memory"}
        )

        self._index_chunks(chunks)

    def _index_chunks(self, chunks: list[dict]):
        if not chunks:
            print("Ä°ndekslenecek chunk bulunamadÄ±.")
            return

        existing_count = self.collection.count()

        if existing_count > 0:
            print(f"ChromaDB hazÄ±r. Mevcut kayÄ±t sayÄ±sÄ±: {existing_count}")
            return

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            source = str(chunk.get("source", "unknown"))
            chunk_id = int(chunk.get("chunk_id", 0))
            text = str(chunk.get("text", "")).strip()

            if not text:
                continue

            ids.append(f"{source}::chunk_{chunk_id}")
            documents.append(text)

            metadatas.append({
                "source": source,
                "file_name": str(chunk.get("file_name", "")),
                "file_type": str(chunk.get("file_type", "")),
                "content_type": str(chunk.get("content_type", "unknown")),
                "subject": str(chunk.get("subject", "unknown")),
                "chunk_id": chunk_id,
            })

        if not documents:
            print("BoÅŸ olmayan dokÃ¼man/chunk bulunamadÄ±.")
            return

        embeddings = self.model.encode(
            documents,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        print(f"ChromaDB indeksleme tamamlandÄ±. Yeni kayÄ±t: {len(ids)}")

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.10,
        subject: str | None = None
    ) -> str:
        result = self.retrieve_with_sources(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            subject=subject
        )

        return result["context"]

    def retrieve_with_sources(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.10,
        subject: str | None = None
    ) -> dict:
        import re
        import unicodedata

        query = query.strip()

        if not query:
            return {
                "context": "",
                "sources": []
            }

        if self.collection.count() == 0:
            return {
                "context": "",
                "sources": []
            }

        def normalize_text(text: str) -> str:
            text = text.casefold()
            turkish_map = str.maketrans({
                "\u0131": "i",
                "\u011f": "g",
                "\u00fc": "u",
                "\u015f": "s",
                "\u00f6": "o",
                "\u00e7": "c",
            })

            text = text.translate(turkish_map)
            text = unicodedata.normalize("NFKD", text)
            text = "".join(
                char for char in text
                if not unicodedata.combining(char)
            )

            return text

        def tokenize(text: str) -> list[str]:
            return re.findall(
                r"[a-z0-9]+",
                normalize_text(text)
            )

        stop_words = {
            "ve", "veya", "ile", "bir", "bu", "su",
            "nedir", "neresidir", "nelerdir", "neler", "hangileri", "hangileridir", "say", "acikla", "anlat",
            "hakkinda", "icin", "olan", "olarak",
            "mi", "midir", "dir",
            "nin", "nin", "nun",
            "ni", "nu",
        }

        query_tokens = [
            token
            for token in tokenize(query)
            if len(token) > 2 and token not in stop_words
        ]

        factor_query_tokens = {
            "faktor", "faktorler",
            "etken", "etkenler",
            "neden", "nedenler",
            "sebep", "sebepler",
            "sart", "sartlar",
            "kosul", "kosullar",
            "destekleyen", "destekledi",
            "kolaylastiran", "kolaylastirdi",
            "etkileyen",
        }

        is_factor_query = any(
            token in factor_query_tokens
            for token in query_tokens
        )

        normalized_query = normalize_text(query)

        list_query_markers = (
            "hangileri",
            "hangileridir",
            "neler",
            "nelerdir",
        )

        is_list_query = any(
            marker in normalized_query
            for marker in list_query_markers
        )

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()

        candidate_k = max(
            top_k * 20,
            300 if (is_factor_query or is_list_query) else 100
        )

        query_kwargs = {
            "query_embeddings": query_embedding,
            "n_results": candidate_k,
            "include": ["documents", "metadatas", "distances"]
        }

        if subject:
            query_kwargs["where"] = {"subject": subject}

        results = self.collection.query(**query_kwargs)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        ranked = []

        normalized_query = normalize_text(query)

        for doc, meta, distance in zip(
            documents,
            metadatas,
            distances
        ):
            similarity = 1 / (1 + float(distance))

            if similarity < min_similarity:
                continue

            normalized_doc = normalize_text(doc)
            doc_tokens = set(tokenize(doc))

            matched_tokens = 0

            for token in query_tokens:
                if token in doc_tokens:
                    matched_tokens += 1
                    continue

                if len(token) >= 5:
                    prefix = token[:5]

                    if any(
                        len(candidate) >= 5
                        and candidate.startswith(prefix)
                        for candidate in doc_tokens
                    ):
                        matched_tokens += 1

            lexical_coverage = (
                matched_tokens / len(query_tokens)
                if query_tokens
                else 0.0
            )

            phrase_bonus = 0.0

            meaningful_phrases = [
                " ".join(query_tokens[i:i + 2])
                for i in range(len(query_tokens) - 1)
            ]

            for phrase in meaningful_phrases:
                if phrase and phrase in normalized_doc:
                    phrase_bonus += 0.08

            exact_token_bonus = 0.0

            for token in query_tokens:
                if len(token) >= 5 and token in doc_tokens:
                    exact_token_bonus += 0.03

            hybrid_score = (
                similarity
                + (lexical_coverage * 0.35)
                + phrase_bonus
                + exact_token_bonus
            )

            # Faktor / neden / kosul tipi sorularda bolum niyetini
            # ayrica degerlendir.
            intent_bonus = 0.0

            if is_factor_query and meta.get("content_type") == "reading":
                title_match = re.search(
                    r"(?m)^\s*title:\s*(.+?)\s*$",
                    doc
                )

                if title_match:
                    title_tokens = set(
                        tokenize(title_match.group(1))
                    )

                    intent_hits = len(
                        title_tokens & factor_query_tokens
                    )

                    if intent_hits > 0:
                        intent_bonus = min(
                            intent_hits * 0.20,
                            0.40
                        )

            list_intent_bonus = 0.0

            if (
                is_list_query
                and not is_factor_query
                and meta.get("content_type") == "reading"
            ):
                title_match = re.search(
                    r"(?m)^\s*title:\s*(.+?)\s*$",
                    doc
                )

                if title_match:
                    title_tokens = set(
                        tokenize(title_match.group(1))
                    )

                    topic_tokens = [
                        token
                        for token in query_tokens
                        if token not in list_query_markers
                    ]

                    title_topic_hits = 0

                    for token in topic_tokens:
                        if token in title_tokens:
                            title_topic_hits += 1
                            continue

                        if len(token) >= 5:
                            prefix = token[:5]

                            if any(
                                len(title_token) >= 5
                                and title_token.startswith(prefix)
                                for title_token in title_tokens
                            ):
                                title_topic_hits += 1

                    if title_topic_hits > 0:
                        list_intent_bonus = min(
                            title_topic_hits * 0.30,
                            0.60
                        )

            # Dogrudan bilgi sorularinda, ayni bilgiyi ogretici
            # Reading kaynagi destekliyorsa kucuk bir kaynak-turu
            # tercihi uygula. Factor ve list routing'e dokunmaz.
            direct_fact_bonus = 0.0

            if (
                not is_factor_query
                and not is_list_query
                and meta.get("content_type") == "reading"
            ):
                direct_fact_bonus = 0.05

            final_score = (
                hybrid_score
                + intent_bonus
                + list_intent_bonus
                + direct_fact_bonus
            )

            ranked.append({
                "doc": doc,
                "meta": meta,
                "similarity": similarity,
                "lexical_coverage": lexical_coverage,
                "hybrid_score": hybrid_score,
                "intent_bonus": intent_bonus,
                "list_intent_bonus": list_intent_bonus,
                "direct_fact_bonus": direct_fact_bonus,
                "final_score": final_score,
            })

        ranked.sort(
            key=lambda item: item["final_score"],
            reverse=True
        )

        selected_items = ranked[:top_k]

        if is_factor_query:
            intent_candidates = [
                item
                for item in ranked
                if item["meta"].get("content_type") == "reading"
                and item.get("intent_bonus", 0.0) > 0.0
            ]

            if intent_candidates:
                anchor = intent_candidates[0]
                anchor_meta = anchor["meta"]
                anchor_doc = anchor["doc"]

                anchor_source = anchor_meta.get("source")
                anchor_chunk = anchor_meta.get("chunk_id")

                anchor_title_match = re.search(
                    r"(?m)^\s*title:\s*(.+?)\s*$",
                    anchor_doc
                )

                anchor_title = (
                    normalize_text(anchor_title_match.group(1).strip())
                    if anchor_title_match
                    else ""
                )

                def same_section(item):
                    if item["meta"].get("source") != anchor_source:
                        return False

                    title_match = re.search(
                        r"(?m)^\s*title:\s*(.+?)\s*$",
                        item["doc"]
                    )

                    if not title_match:
                        return False

                    return (
                        normalize_text(title_match.group(1).strip())
                        == anchor_title
                    )

                previous_item = None
                next_item = None

                if isinstance(anchor_chunk, int):
                    previous_item = next(
                        (
                            item
                            for item in ranked
                            if item["meta"].get("chunk_id")
                            == anchor_chunk - 1
                            and same_section(item)
                        ),
                        None
                    )

                    next_item = next(
                        (
                            item
                            for item in ranked
                            if item["meta"].get("chunk_id")
                            == anchor_chunk + 1
                            and same_section(item)
                        ),
                        None
                    )

                if previous_item is not None:
                    selected_items = [
                        previous_item,
                        anchor
                    ]
                elif next_item is not None:
                    selected_items = [
                        anchor,
                        next_item
                    ]
                else:
                    selected_items = [
                        anchor
                    ]


        # Liste tipi bilgi sorularinda, soru konusuyla eslesen
        # Reading bolumunu anchor olarak sec ve ayni section'daki
        # komsu chunk ile birlikte getir.
        if is_list_query and not is_factor_query:
            list_candidates = [
                item
                for item in ranked
                if item["meta"].get("content_type") == "reading"
                and item.get("list_intent_bonus", 0.0) > 0.0
            ]

            if list_candidates:
                anchor = list_candidates[0]
                anchor_meta = anchor["meta"]
                anchor_doc = anchor["doc"]

                anchor_source = anchor_meta.get("source")
                anchor_chunk = anchor_meta.get("chunk_id")

                anchor_title_match = re.search(
                    r"(?m)^\s*title:\s*(.+?)\s*$",
                    anchor_doc
                )

                anchor_title = (
                    normalize_text(
                        anchor_title_match.group(1).strip()
                    )
                    if anchor_title_match
                    else ""
                )

                def same_list_section(item):
                    if item["meta"].get("source") != anchor_source:
                        return False

                    if item["meta"].get("content_type") != "reading":
                        return False

                    title_match = re.search(
                        r"(?m)^\s*title:\s*(.+?)\s*$",
                        item["doc"]
                    )

                    if not title_match:
                        return False

                    return (
                        normalize_text(
                            title_match.group(1).strip()
                        )
                        == anchor_title
                    )

                previous_item = None
                next_item = None

                if isinstance(anchor_chunk, int):
                    previous_item = next(
                        (
                            item
                            for item in ranked
                            if item["meta"].get("chunk_id")
                            == anchor_chunk - 1
                            and same_list_section(item)
                        ),
                        None
                    )

                    next_item = next(
                        (
                            item
                            for item in ranked
                            if item["meta"].get("chunk_id")
                            == anchor_chunk + 1
                            and same_list_section(item)
                        ),
                        None
                    )

                if previous_item is not None:
                    selected_items = [
                        previous_item,
                        anchor
                    ]
                elif next_item is not None:
                    selected_items = [
                        anchor,
                        next_item
                    ]
                else:
                    selected_items = [
                        anchor
                    ]


        # Quiz sorusu chunk sinirinda ikiye bolunmusse,
        # soru parcasi ile dogru cevap/aciklama parcasini birlikte getir.
        # Factor/Reading routing davranisina dokunmaz.
        if not is_factor_query and selected_items:
            quiz_anchor = selected_items[0]
            quiz_meta = quiz_anchor["meta"]
            quiz_doc = quiz_anchor["doc"]

            if (
                quiz_meta.get("content_type") == "quiz"
                and "question_text:" in quiz_doc
                and "correct_choice:" not in quiz_doc
            ):
                quiz_source = quiz_meta.get("source")
                quiz_chunk = quiz_meta.get("chunk_id")

                quiz_next = None

                if isinstance(quiz_chunk, int):
                    quiz_next = next(
                        (
                            item
                            for item in ranked
                            if item["meta"].get("content_type") == "quiz"
                            and item["meta"].get("source") == quiz_source
                            and item["meta"].get("chunk_id") == quiz_chunk + 1
                            and "correct_choice:" in item["doc"]
                        ),
                        None
                    )

                if quiz_next is not None:
                    selected_items = [
                        quiz_anchor,
                        quiz_next
                    ]

        context_parts = []
        sources = []

        for item in selected_items:
            doc = item["doc"]
            meta = item["meta"]
            similarity = item["similarity"]

            source = meta.get("source", "unknown")
            chunk_id = meta.get("chunk_id", "unknown")

            context_parts.append(
                f"[Kaynak: {source} | "
                f"TÃ¼r: {meta.get('content_type', 'unknown')} | "
                f"Ders: {meta.get('subject', 'unknown')} | "
                f"Chunk: {chunk_id} | "
                f"Benzerlik: {similarity:.3f} | "
                f"Hibrit: {item['hybrid_score']:.3f}]\n"
                f"{doc}"
            )

            sources.append({
                "source": source,
                "chunk_id": chunk_id,
                "similarity": round(similarity, 3),
                "hybrid_score": round(
                    item["hybrid_score"],
                    3
                ),
                "lexical_coverage": round(
                    item["lexical_coverage"],
                    3
                ),
                "content_type": meta.get(
                    "content_type",
                    "unknown"
                ),
                "subject": meta.get(
                    "subject",
                    "unknown"
                ),
                "file_name": meta.get(
                    "file_name",
                    ""
                )
            })

        return {
            "context": "\n\n---\n\n".join(context_parts),
            "sources": sources
        }

