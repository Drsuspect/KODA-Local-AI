# KODAAI Local AI Benchmark v1

İlk sürüm smoke/regression benchmark'ıdır.

## Çalıştırma

Backend çalışırken:

```powershell
$env:KODAAI_API_KEY="..."
python .\benchmarks\local_ai_v1\run_benchmark.py
```

Varsayılan API:
`http://127.0.0.1:8080`

Farklı adres:

```powershell
python .\benchmarks\local_ai_v1\run_benchmark.py --url http://127.0.0.1:8080
```

## Çıktı

`benchmark_report.json`

Rapor:
- toplam case
- pass rate
- ortalama latency
- median latency
- case bazlı route/refusal/answer kontrolleri

## Not

Bu ilk set yalnız smoke testtir. Model kalite benchmark'ı olarak yorumlanmamalıdır.

Gerçek karşılaştırma için:
1. 50-100 doğrulanmış soru,
2. sabit benchmark split,
3. konu dengesi,
4. insan doğrulamalı expected answer,
5. hallucination/grounding değerlendirmesi

eklenmelidir.
