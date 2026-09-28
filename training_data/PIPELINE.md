# KODAAI Training Data Production Pipeline

## Akış

SOURCE / CURRICULUM
→ QUESTION DRAFT
→ A-E OPTION REASONING
→ HINT / EXPLAIN / SIMPLIFY / EXAMPLE / CHECK
→ SOURCE + LICENSE CHECK
→ ACCESSIBILITY REVIEW
→ SCHEMA VALIDATOR
→ HUMAN / DOMAIN REVIEW
→ SPLIT ASSIGNMENT
→ LEAKAGE CHECK
→ TRAIN / DEV / BENCHMARK

## PowerShell komutları

Reasoning JSONL doğrulama:

python .\tools\validate_training_data.py .\training_data\seeds\educational_reasoning_v0_1_seed.jsonl --type reasoning

Split oluşturma:

python .\tools\build_reasoning_splits.py .\training_data\seeds\educational_reasoning_v0_1_seed.jsonl --out-dir .\training_data\splits

Leakage kontrolü:

python .\tools\check_dataset_leakage.py .\training_data\splits\train.jsonl .\training_data\splits\dev.jsonl .\training_data\splits\benchmark.jsonl

## Production kullanımı

reviewed veri doğrudan production eğitim verisi sayılmaz.

Yalnız kaynak/lisans, doğruluk, pedagojik içerik ve erişilebilirlik kontrolleri tamamlanmış kayıt verified durumuna geçirilebilir.
