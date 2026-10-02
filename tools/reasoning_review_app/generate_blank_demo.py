from __future__ import annotations

import os
import sys
from pathlib import Path

TEXT = (
    "Yazdıklarını hep bir oyun olarak nitelemekten nokta nokta nokta yazarlar, "
    "gerçek hayatın içine girince de yazarlıklarını oyuna dönüştürürler. "
    "Edebiyatın, kurmacanın, yaratıcı yazının bir oyun olduğunu kendi buluşları gibi "
    "öne sürerek öteki yazarlara nokta nokta nokta çalışırlar. "
    "Bu parçada boş bırakılan yerlere aşağıdakilerden hangileri sırasıyla getirilmelidir?"
)

INSTRUCTIONS = (
    "Türkçe bir sınav sorusunu görme engelli bir öğrenci için açık, doğal ve öğretici biçimde oku. "
    "Genel konuşma hızı orta ve nettir. "
    "Metinde geçen 'nokta nokta nokta' ifadeleri soru boşluğunu temsil eder. "
    "Bu ifadelerin hemen öncesinde ve sonrasında kısa bir duraklama yap. "
    "Her 'nokta' kelimesini birbirinden belirgin biçimde ayır, normal metinden biraz daha yavaş söyle "
    "ve boşluk olduğunu fark ettirecek ölçülü bir vurgu uygula. "
    "Abartılı dramatik ton kullanma. "
    "Herhangi bir XML etiketi, köşeli parantez, tırnak veya noktalama işaretinin adını ayrıca okuma."
)


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("HATA: OPENAI_API_KEY bulunamadı.", file=sys.stderr)
        return 2

    try:
        from openai import OpenAI
    except ImportError:
        print(
            "HATA: openai paketi bulunamadı. "
            "python -m pip install --upgrade openai",
            file=sys.stderr,
        )
        return 2

    root = Path(__file__).resolve().parents[2]
    output_dir = root / "artifacts" / "tts_demos"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "blank_emphasis_alloy_v1.mp3"

    print("Model      : gpt-4o-mini-tts")
    print("Voice      : alloy")
    print("Speed      : 1.2")
    print(f"Output     : {output_file}")
    print()
    print("TTS metni:")
    print(TEXT)
    print()

    client = OpenAI()
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=TEXT,
        instructions=INSTRUCTIONS,
        speed=1.2,
        response_format="mp3",
    ) as response:
        response.stream_to_file(output_file)

    if not output_file.exists() or output_file.stat().st_size == 0:
        print("HATA: MP3 üretilemedi.", file=sys.stderr)
        return 1

    print(f"TAMAM: {output_file} ({output_file.stat().st_size} bayt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
