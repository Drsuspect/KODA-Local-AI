import json
import urllib.request
import urllib.error


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
        prompt = self._build_prompt(question, context)

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

    def _build_prompt(self, question: str, context: str = "") -> str:
        has_context = bool(context.strip())

        if has_context:
            context_rule = (
                "- Cevabını öncelikle verilen bağlama dayandır.\n"
                "- Bağlamda açıkça bulunmayan bilgileri kesin bilgi gibi sunma.\n"
                "- Eğer bağlam yetersizse bunu açıkça belirt.\n"
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