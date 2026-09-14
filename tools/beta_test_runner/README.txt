KODAAI Beta Test Runner v1

1) beta_test_runner.py ve questions.json dosyalarını KODA-Local-AI proje köküne koyun.
2) PowerShell:
   cd F:\Yazilimlar\app\KODA_AI_LAB\04_KODA_Local_AI
   python .\beta_test_runner.py
3) UI: http://127.0.0.1:8765

Özellikler:
- 100 soru gömülü.
- Sesli komut: sonraki / önceki / tekrar / final analiz (Chrome/Edge SpeechRecognition).
- Sağ/sol ok tuşları.
- Manuel oturum başlangıç zamanı.
- İsteğe bağlı 100 soruyu /ask endpointine otomatik gönderme.
- Final analiz: logs/telemetry.jsonl, logs/content_gap.jsonl, logs/audit_log.jsonl.
- Exact + fuzzy soru eşleştirme.
- Route/subject/süre/source_count/başarı/hata özeti.
- İçerik açıkları listesi.
- JSON raporu logs/beta_test_reports altına kaydeder.
- KODAAI_API_KEY ortam değişkeninden veya proje .env dosyasından otomatik okunur; UI'da gösterilmez.

Not: Otomatik test gerçekten 100 API isteği üretir.
