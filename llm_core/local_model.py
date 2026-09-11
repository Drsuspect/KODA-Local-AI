import json
import urllib.request
import urllib.error
import re


class LocalLLM:
    def __init__(
        self,
        model_name: str = "gemma3:4b",
        mode: str = "offline",
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 180
    ):
        self.model_name = model_name
        self.mode = mode
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, question: str, context: str = "") -> str:
        effective_context = self._filter_factor_context(
            question,
            context
        )

        prompt = self._build_prompt(
            question,
            effective_context
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 512
            }
        }

        try:
            req = urllib.request.Request(
                url=f"{self.base_url}/api/generate",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            answer = data.get("response", "").strip()

            if not answer:
                return "Model boş cevap döndürdü."

            filtered_answer = self._filter_scope_answer(question, answer)

            if filtered_answer:
                return filtered_answer

            if effective_context.strip() and self._is_factor_question(question):
                repaired_answer = self._repair_factor_answer(
                    question,
                    effective_context
                )

                repaired_filtered = self._filter_scope_answer(
                    question,
                    repaired_answer
                )

                if repaired_filtered:
                    return repaired_filtered

            return answer

        except urllib.error.URLError as e:
            return (
                "Ollama API bağlantısı kurulamadı. "
                "Ollama uygulaması açık mı kontrol et. "
                f"Model: {self.model_name}. "
                f"Detay: {e}"
            )

        except json.JSONDecodeError as e:
            return f"Ollama API geçersiz JSON döndürdü. Detay: {e}"

        except Exception as e:
            return f"Beklenmeyen LLM API hatası: {e}"

    def _filter_factor_context(
        self,
        question: str,
        context: str
    ) -> str:
        """
        Neden/faktör/şart/etken sorularında,
        kaynak bağlamındaki bariz kronolojik olay
        cümlelerini modele göndermeden ayıklar.
        """
        if not context.strip():
            return context

        if not self._is_factor_question(question):
            return context

        event_markers = (
            " savaşı ",
            " savaşı.",
            " savaşında ",
            " kazanıldı",
            " fethedildi",
            " fethedilerek",
            " fethi ",
            " fethi.",
            " alındı",
            " başkent yapıldı",
            " tahta çıktı",
        )

        parts = re.split(
            r"(?<=[.!?])\s+",
            context.strip()
        )

        kept = []

        for part in parts:
            normalized = f" {part.casefold().strip()} "

            is_event = any(
                marker in normalized
                for marker in event_markers
            )

            if not is_event:
                kept.append(part.strip())

        filtered = " ".join(
            part for part in kept if part
        ).strip()

        return filtered or context

    def _is_factor_question(self, question: str) -> bool:
        q = question.casefold()

        markers = (
            "neden",
            "faktör",
            "şart",
            "etken",
        )

        return any(marker in q for marker in markers)

    def _repair_factor_answer(
        self,
        question: str,
        context: str
    ) -> str:
        prompt = f"""
Sen bir kaynak-bağlam cevap düzelticisisin.

Görevin:
- Yalnızca verilen kaynak bağlamı kullan.
- Kullanıcı neden, faktör, şart veya etken soruyor.
- Kaynakta bu soruya doğrudan karşılık gelen neden ve faktörleri eksiksiz seç.
- Savaş, fetih, tarih, tahta çıkma ve sonraki kronolojik olayları faktör gibi sunma.
- Yalnızca aynı paragrafta geçtiği için olaylar arasında nedensellik kurma.
- Kısa ve doğrudan Türkçe cevap ver.
- Kaynakta bulunmayan bilgi ekleme.

Kaynak:
{context}

Soru:
{question}

Yalnızca sorunun doğrudan cevabı:
""".strip()

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.8,
                "num_predict": 256
            }
        }

        try:
            req = urllib.request.Request(
                url=f"{self.base_url}/api/generate",
                data=json.dumps(
                    payload,
                    ensure_ascii=False
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(
                req,
                timeout=self.timeout
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8")
                )

            return data.get("response", "").strip()

        except Exception:
            return ""

    def _filter_scope_answer(self, question: str, answer: str) -> str:
        """
        Neden/fakt?r/?art/etken sorular?nda, modelin cevaba
        sonradan ekledi?i bariz kronolojik olay c?mlelerini ay?klar.
        """
        q = question.casefold()

        factor_markers = (
            "neden",
            "faktör",
            "şart",
            "etken",
        )

        if not self._is_factor_question(question):
            return answer

        event_markers = (
            " savaşı ",
            " savaşı.",
            " savaşında ",
            " fethedildi",
            " fethedilerek",
            " fethi ",
            " fethi.",
            " alındı",
            " başkent yapıldı",
            " tahta çıktı",
        )

        sentences = re.split(r"(?<=[.!?])\s+", answer.strip())

        kept = []

        for sentence in sentences:
            normalized = f" {sentence.casefold().strip()} "

            is_event_sentence = any(
                marker in normalized
                for marker in event_markers
            )

            if not is_event_sentence:
                kept.append(sentence.strip())

        filtered = " ".join(
            sentence for sentence in kept if sentence
        ).strip()

        return filtered

    def _build_prompt(self, question: str, context: str = "") -> str:
        has_context = bool(context.strip())

        if has_context:
            context_rule = (
                "- Cevabını verilen kaynak bağlama dayandır.\n"
                "- Kaynakta bulunan kişi, kurum, tarih, olay, sayı, kavram ve neden-sonuç ilişkilerini değiştirme.\n"
                "- Kaynakta açıkça bulunmayan bilgi, özne veya ilişki üretme ve bunları kesin bilgi gibi sunma.\n"
                "- Kullanıcı soru üretmeni isterse soruyu kaynakta açıkça yer alan bilgilerden oluştur.\n"
                "- Soru üretirken kişi ile devlet, olay ile neden, neden ile sonuç gibi ögeleri birbirinin yerine koyma.\n"
                "- Kaynakta hazır bir soru varsa mümkün olduğunca anlamını ve olgusal yapısını koru.\n"
                "- Birden fazla kaynak parçası çelişiyorsa bunları keyfi biçimde birleştirme.\n"
                "- Sorunun doğrudan cevabı olmayan, yalnızca aynı bağlamda geçen sonraki olayları veya sonuçları cevaba ekleme.\n"
                "- Soru nedenleri, faktörleri, şartları veya etkenleri soruyorsa yalnızca bu neden, faktör, şart ve etkenleri seç; sonraki gelişmeleri cevap unsuru yapma.\n"
                "- Neden veya faktör sorularında kaynakta açıkça belirtilen ilgili faktörlerin tamamını mümkün olduğunca eksiksiz aktar.\n"
                "- Neden veya faktör sorularında cevap yazmadan önce kaynakta bu soruya karşılık gelen tüm ayrı etkenleri tek tek belirle; hiçbirini atlama.\n"
                "- Aynı cümlede birden fazla faktör varsa her birini ayrı cevap unsuru olarak koru; özetlerken faktör kaybetme.\n"
                "- Savaş, fetih, tahta çıkma, tarih veya sonraki kronolojik gelişmeleri, kaynak bunları açıkça neden olarak tanımlamıyorsa neden veya faktör gibi sunma.\n"
                "- Yalnızca aynı paragrafta bulunmasından dolayı iki olay arasında nedensellik kurma.\n"
                "- Bağlam yetersiz veya belirsizse bunu açıkça belirt; tahmin ederek boşluğu doldurma.\n"
                "- Kaynak bağlamla çelişen yorum yapma."
            )
        else:
            context_rule = (
                "- Bağlam verilmemişse genel bilgiyle ama temkinli cevap ver.\n"
                "- Güncel veya doğrulama gerektiren konularda kesin konuşma."
            )

        return f"""
Sen KODA Secure LLM Core içinde çalışan kapalı devre bir Türkçe kurumsal asistansın.

Çalışma modu:
- Sistem modu: {self.mode}
- Model: {self.model_name}
- İnternet erişimi varsayma.
- Kurumsal güvenlik önceliklidir.

Kurallar:
- Bilmediğin şeyi uydurma.
- Türkçe cevap ver.
- Kısa, net ve teknik konuş.
- Kullanıcı gizli veri, parola, token, anahtar veya erişim bilgisi isterse reddet.
- Güvenlik, audit, erişim kontrolü ve veri gizliliği konularında dikkatli davran.
{context_rule}

Bağlam:
{context}

Soru:
{question}

Cevap:
""".strip()
