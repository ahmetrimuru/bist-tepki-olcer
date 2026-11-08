"""bist-tepki-olcer komut satırı.

Örnekler:
    python main.py --dosya ornekler/THYAO.csv
    python main.py --dosya THYAO.csv,ASELS.xlsx --esik 1.5
    python main.py --hisse THYAO,AKBNK --sure 1y        (yfinance gerekir)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src import grafik, hesap, rapor, veri

SURELER = {"6m": 182, "1y": 365, "2y": 730, "3y": 1095}


def argumanlar():
    p = argparse.ArgumentParser(description="Hissenin BIST 100 hareketlerine tepkisini ölçer.")
    p.add_argument("--dosya", help="Hisse verisi dosyaları (CSV/Excel), virgülle ayrılmış")
    p.add_argument("--hisse", help="yfinance ile çekilecek hisse kodları, ör: THYAO,ASELS")
    p.add_argument("--sure", default="2y", choices=SURELER.keys(), help="Analiz süresi (varsayılan 2y)")
    p.add_argument("--esik", type=float, default=2.0, help="Sert gün eşiği, yüzde (varsayılan 2)")
    p.add_argument("--pencere", type=int, default=60, help="Hareketli beta penceresi, gün (varsayılan 60)")
    p.add_argument("--endeks-dosya", help="BIST 100 verisi için yerel dosya (isteğe bağlı)")
    p.add_argument("--cikti", default="cikti", help="Çıktı klasörü (varsayılan: cikti)")
    a = p.parse_args()
    if not a.dosya and not a.hisse:
        p.error("--dosya veya --hisse vermelisiniz.")
    return a


def hisseleri_yukle(a) -> dict[str, pd.Series]:
    hisseler = {}
    bitis = pd.Timestamp.today().normalize()
    baslangic = bitis - pd.Timedelta(days=SURELER[a.sure])
    if a.dosya:
        for yol in a.dosya.split(","):
            seri = veri.dosya_oku(yol.strip())
            hisseler[seri.name] = seri
    if a.hisse:
        for kod in a.hisse.split(","):
            kod = kod.strip().upper()
            hisseler[kod] = veri.yfinance_getir(f"{kod}.IS", baslangic, bitis)
    return hisseler


def main():
    a = argumanlar()
    klasor = Path(a.cikti)
    klasor.mkdir(parents=True, exist_ok=True)

    hisseler = hisseleri_yukle(a)

    # Analiz dönemi: seçilen süre, ama en fazla hisse verisinin olduğu aralık
    son = max(s.index.max() for s in hisseler.values())
    ilk = son - pd.Timedelta(days=SURELER[a.sure])

    if a.endeks_dosya:
        endeks, kaynak = veri.dosya_oku(a.endeks_dosya).rename("XU100"), a.endeks_dosya
    else:
        endeks, kaynak = veri.xu100_getir(ilk, son)
    print(f"BIST 100 verisi: {kaynak}\n")

    sonuclar = {}
    for ad, seri in hisseler.items():
        seri = seri[seri.index >= ilk]
        tablo = veri.esle(seri, endeks)
        print(f"{ad}: {len(seri)} gün hisse verisi, {len(tablo)} gün BIST 100 ile eşleşti.")
        if len(tablo) < 30:
            print(f"  {ad} atlandı: eşleşen gün sayısı çok az (tarihleri kontrol edin).\n")
            continue

        for tarih, satir in veri.supheli_gunler(tablo).iterrows():
            print(f"  Uyarı: {tarih.date()} günü %{satir['hisse'] * 100:.1f} hareket var. "
                  "Bedelsiz/bölünme olabilir, düzeltilmiş veri kullanın.")

        s = hesap.hepsini_hesapla(tablo, a.esik, a.pencere)
        sonuclar[ad] = s
        print()
        print(rapor.ozet_metni(ad, s))
        grafik.dagilim_grafigi(tablo, ad, s["beta"], klasor)
        grafik.hareketli_beta_grafigi(tablo, ad, klasor, a.pencere)
        print()

    if not sonuclar:
        print("Hesaplanacak hisse kalmadı.")
        return 1

    if len(sonuclar) > 1:
        print("=== Karşılaştırma (betaya göre) ===")
        print(rapor.karsilastirma_tablosu(sonuclar).to_string())
        print()

    csv_yolu = rapor.csv_kaydet(sonuclar, klasor / "sonuclar.csv")
    print(f"Sonuçlar ve grafikler '{klasor}' klasörüne kaydedildi ({csv_yolu.name}).")
    print("Not: Bu araç yatırım tavsiyesi değildir, eğitim amaçlıdır.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (FileNotFoundError, ValueError, RuntimeError) as hata:
        print(f"Hata: {hata}")
        sys.exit(1)
