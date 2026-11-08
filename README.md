# bist-tepki-olcer

Bir BIST hissesinin, BIST 100 endeksinin yükseldiği ve düştüğü günlerde nasıl tepki verdiğini ölçen küçük bir Python aracı.

Cevapladığı soru: **"BIST 100 %1 düştüğünde bu hisse ortalama ne kadar düşüyor, %1 yükseldiğinde ne kadar yükseliyor?"**

## Ne hesaplar?

| Ölçü | Basit anlamı |
|---|---|
| Beta | Endeks %1 hareket ettiğinde hisse ortalama yüzde kaç hareket ediyor |
| Yükseliş / Düşüş betası | Aynı ölçü, yalnızca endeksin yükseldiği ya da düştüğü günler için |
| Up capture / Down capture | Endeksin yükseliş günlerindeki hareketinin yüzde kaçını, düşüş günlerindekinin yüzde kaçını yakalıyor |
| Korelasyon / R² | Hisse endeksle ne kadar birlikte hareket ediyor (1'e yakınsa çok bağlı) |
| Yön uyumu | Endeksle aynı yöne gittiği günlerin yüzdesi |
| Sert günler | Endeksin ±%2'den (ayarlanabilir) fazla oynadığı günlerde hissenin ortalama getirisi |
| Hareketli beta | Son 60 günle hesaplanan, zaman içinde değişen beta |
| Etiket | Beta < 0,8 Defansif · 0,8–1,2 Endeksle paralel · > 1,2 Agresif |

## Kurulum

```bash
git clone https://github.com/KULLANICI_ADI/bist-tepki-olcer.git
cd bist-tepki-olcer
pip install -r requirements.txt
```

## Kullanım

En basit yol: hissenin günlük verisini (en az 2 yıl önerilir) CSV veya Excel olarak ver. BIST 100 verisini program kendisi çeker.

```bash
python main.py --dosya THYAO.csv
```

Birden fazla hisseyi karşılaştırmak için:

```bash
python main.py --dosya THYAO.csv,ASELS.xlsx,AKBNK.csv
```

Hisse verisini de internetten çekmek için (yfinance):

```bash
python main.py --hisse THYAO,ASELS --sure 2y
```

### Seçenekler

| Seçenek | Açıklama | Varsayılan |
|---|---|---|
| `--dosya` | Hisse dosyaları, virgülle ayrılmış | - |
| `--hisse` | yfinance ile çekilecek hisse kodları | - |
| `--sure` | `6m`, `1y`, `2y`, `3y` | `2y` |
| `--esik` | Sert gün eşiği (yüzde) | `2` |
| `--pencere` | Hareketli beta penceresi (gün) | `60` |
| `--endeks-dosya` | BIST 100 için yerel dosya | - |
| `--cikti` | Çıktı klasörü | `cikti` |

### Dosya biçimi

Dosyada en az iki sütun olmalı: **Tarih** ve **Kapanış** (ya da `Date` ve `Close`). Dosya adı hisse adı olarak kullanılır (`THYAO.csv` → THYAO).

```
Tarih;Kapanış
06.11.2026;312,50
07.11.2026;315,25
```

- Tarih biçimleri: `07.11.2026`, `2026-11-07`, `07/11/2026`
- Ondalık ayırıcı virgül de nokta da olabilir. CSV'de `,` `;` ve sekme ayırıcıları tanınır.
- **Düzeltilmiş kapanış kullanın.** Bedelsiz veya bölünme olan günlerde düzeltilmemiş veri sahte bir sert düşüş gibi görünür ve sonuçları bozar. Program bir günde %15'ten büyük hareket görürse uyarır.

## Örnek çıktı

```
=== ORNEK / BIST 100 ===
Dönem: 2024-12-10 - 2026-11-06 (499 işlem günü)

Beta              : 1,53  -> Agresif
Yükseliş betası   : 1,34
Düşüş betası      : 1,74
Up capture        : %134
Down capture      : %166
Korelasyon / R²   : 0,89 / 0,79
Yön uyumu         : %84
Son 60 gün betası : 1,60

Sert günler (endeks ±%2,0):
  Yükseliş: 41 gün, endeks ort. %2,65, hisse ort. %3,42
  Düşüş   : 53 gün, endeks ort. %-2,76, hisse ort. %-4,69

Yorum: BIST 100 %1 hareket ettiğinde hisse ortalama %1,53 hareket ediyor.
Düşüşlere yükselişlerden daha güçlü tepki veriyor (olumsuz asimetri).
```

*(Yukarıdaki sayılar biçimi göstermek için yapay veriyle üretilmiştir.)*

`cikti/` klasörüne şunlar kaydedilir:
- `sonuclar.csv`: tüm ölçüler
- `HISSE_dagilim.png`: günlük getirilerin dağılımı ve regresyon çizgisi
- `HISSE_hareketli_beta.png`: betanın zaman içindeki değişimi

## BIST 100 verisi nereden geliyor?

1. Önce `yfinance` ile `XU100.IS` çekilir.
2. Çekilemezse `data/xu100.csv` kullanılır.
3. `data/xu100.csv` dosyasını GitHub Actions hafta içi her akşam otomatik günceller (`.github/workflows/xu100_guncelle.yml`). Elle güncellemek için: `python scripts/xu100_guncelle.py`

## Neden 2 yıl?

1 yıl yaklaşık 250 işlem günü eder. Beta için yeterli, ama sert gün sayısı az kalır. 2 yıl hem güncel hem daha sağlam sonuç verir. Çok eski veri ise bugünkü faiz ve kur ortamını yansıtmayabilir. Sert gün sayısı 20'nin altında kalırsa program "güvenilirlik düşük" uyarısı verir.

## Proje yapısı

```
bist-tepki-olcer/
├── main.py                 komut satırı girişi
├── src/
│   ├── veri.py             dosya okuma, BIST 100 verisi, eşleştirme
│   ├── hesap.py            tüm ölçüler
│   ├── grafik.py           grafikler
│   └── rapor.py            özet metin, karşılaştırma, CSV
├── scripts/xu100_guncelle.py
├── tests/                  pytest testleri
├── data/                   BIST 100 yedek verisi
└── .github/workflows/      testler + günlük veri güncelleme
```

## Testler

```bash
pytest
```

## İleride eklenebilecekler

- Streamlit ile web arayüzü
- Gram altın ve dolar/TL ile karşılaştırma
- Haftalık ve aylık veriyle analiz

## Uyarı

Bu proje **yatırım tavsiyesi değildir**, eğitim amaçlıdır. Geçmiş tepkiler gelecekte aynı şekilde tekrar etmeyebilir.

## Lisans

MIT
