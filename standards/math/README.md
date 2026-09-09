# KODAAI MathSpeak V1.0

## Amaç

KODAAI MathSpeak V1.0, matematiksel içeriğin özellikle görme engelli ve ses öncelikli öğrenen kullanıcılar için anlaşılır, tutarlı ve denetlenebilir biçimde seslendirilmesine yönelik KODAAI erişilebilirlik çalışmasının kamuya açık standart katmanıdır.

Bu dizin **production Math Engine kaynak kodunu veya gerçek eğitim/test corpus'unu içermez**. Public repo; standardın yaklaşımını, kurallarını ve güvenli örneklerini paylaşır. Çalışan production parser/engine, regression corpus'u ve özel eğitim verileri dağıtılmaz.

## Temel İlkeler

- Matematiksel ifade yalnız karakter karakter okunmaz; yapısal anlam korunur.
- İşlem sırası ve ifade sınırları sesli anlatımda belirsiz bırakılmaz.
- Kesir, kök, üs, parantez, eşitlik, oran ve benzeri yapılar konuşma sırasında açık sınırlarla aktarılır.
- Görsel konum tek başına anlam taşıyorsa, bu anlam sesli karşılığa dönüştürülür.
- Gereksiz sözel yükten kaçınılırken matematiksel anlamdan taviz verilmez.
- Aynı yapı aynı bağlamda mümkün olduğunca tutarlı biçimde seslendirilir.
- Erişilebilirlik dönüşümü deterministik uygulama katmanında tutulur; üretken yapay zekâ matematik kural motorunun yerine geçmez.

## Örnekler

| Yazılı ifade | Erişilebilir ses örneği |
| --- | --- |
| `x + 3 = 7` | x artı üç eşittir yedi |
| `√25 = 5` | karekök yirmi beş, eşittir beş |
| `3/4` | dörtte üç |
| `x²` | x kare |
| `(a + b) / c` | pay, a artı b, payda c |

Örnekler standardın genel yaklaşımını göstermek içindir; production motorunun tüm dönüşüm kurallarını veya regression testlerini temsil etmez.

## Referans Yaklaşımı

KODAAI çalışması; MathML gibi yapısal matematik gösterimlerinden ve MathSpeak/ClearSpeak gibi konuşmalı matematik yaklaşımlarından yararlanır, ancak Türkçe ses öncelikli eğitim kullanımında gerekli ifade, duraklama ve açıklık kurallarını ayrıca ele alır.

## Public / Private Sınırı

Public:
- standardın amacı ve ilkeleri,
- güvenli örnekler,
- erişilebilirlik yaklaşımının açıklaması.

Private / production:
- Math Engine V1.0 implementation,
- production parser ve dönüştürme kodları,
- tam regression corpus'u,
- gerçek eğitim içeriği,
- üretim verileri ve loglar.

## Durum

MathSpeak V1.0, KODAAI'nin erişilebilir matematik Ar-Ge hattının sabitlenmiş ilk production standardı olarak kullanılmaktadır. Public dokümantasyon, production implementasyonunun kendisini açmadan standardın incelenebilmesini ve geri bildirim alınabilmesini amaçlar.
