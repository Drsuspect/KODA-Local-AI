class PromptGuard:
    def __init__(self):
        self.blocked_keywords = [
            "şifre",
            "parola",
            "password",
            "token",
            "api key",
            "secret key",
            "private key",
            "gizli anahtar",
            "erişim anahtarı",
            "veritabanı şifresi",
            "admin şifresi",
            "bypass",
            "yetki atlat",
            "güvenliği devre dışı bırak"
        ]

    def check(self, text: str) -> dict:
        normalized = text.lower()

        for keyword in self.blocked_keywords:
            if keyword in normalized:
                return {
                    "allowed": False,
                    "reason": f"Riskli ifade tespit edildi: {keyword}"
                }

        return {
            "allowed": True,
            "reason": "OK"
        }