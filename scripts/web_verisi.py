"""Web sayfası için tüm hisselerin sonuçlarını hesaplayıp docs/data klasörüne yazar.

GitHub Actions her iş günü akşamı çalıştırır.
Elle çalıştırmak için: python scripts/web_verisi.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from src import hesap, rapor, veri  # noqa: E402

HISSE_LISTESI = KOK / "data" / "hisseler.txt"
CIKTI = KOK / "docs" / "data"
DONEMLER = {"1y": 365, "2y": 730}
ESIK = 2.0
PENCERE = 60
MIN_GUN = 120


def hisseleri_oku(yol: Path = HISSE_LISTESI) -> list[str]:
    kodlar = []
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.split("#")[0].strip().upper()
        if satir and satir not in kodlar:
            kodlar.append(satir)
    return kodlar


def _temiz(deger):
    """JSON için NaN'ları null yapar, sayıları yuvarlar."""
    if isinstance(deger, float):
        return None if math.isnan(deger) or math.isinf(deger) else round(deger, 4)
    if isinstance(deger, dict):
        return {k: _temiz(v) for k, v in deger.items()}
    if isinstance(deger, list):
        return [_temiz(v) for v in deger]
    return deger


def hisse_sonucu(kod: str, fiyat: pd.Series, endeks: pd.Series) -> dict | None:
    """Bir hisse için iki dönemin özet ve grafik verisini üretir."""
    fiyat = fiyat.dropna()
    if fiyat.empty:
        return None
    son = min(fiyat.index.max(), endeks.index.max())
    donemler = {}
    for ad, gun in DONEMLER.items():
        ilk = son - pd.Timedelta(days=gun)
        tablo = veri.esle(fiyat[(fiyat.index >= ilk) & (fiyat.index <= son)], endeks)
        if len(tablo) < MIN_GUN:
            continue
        ozet = hesap.hepsini_hesapla(tablo, ESIK, PENCERE)
        hb = hesap.hareketli_beta(tablo, PENCERE)
        donemler[ad] = {
            "ozet": {**ozet, "yorum": rapor.yorum(ozet),
                     "supheli_gun": int(len(veri.supheli_gunler(tablo)))},
            "dagilim": [[round(e * 100, 2), round(h * 100, 2)]
                        for e, h in zip(tablo["endeks"], tablo["hisse"])],
            "hareketli_beta": [[t.strftime("%Y-%m-%d"), round(float(v), 3)]
                               for t, v in hb.items()],
        }
    if not donemler:
        return None
    return {"kod": kod, "son_fiyat": round(float(fiyat.iloc[-1]), 2), "donemler": donemler}


def site_verisi_uret(kapanislar: pd.DataFrame, endeks: pd.Series, cikti: Path = CIKTI) -> dict:
    """kapanislar: sütunları hisse kodu olan kapanış tablosu. endeks: XU100 kapanışları."""
    (cikti / "hisse").mkdir(parents=True, exist_ok=True)
    liste, atlanan = [], []
    for kod in kapanislar.columns:
        sonuc = hisse_sonucu(kod, kapanislar[kod], endeks)
        if sonuc is None:
            atlanan.append(kod)
            continue
        (cikti / "hisse" / f"{kod}.json").write_text(
            json.dumps(_temiz(sonuc), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        satir = {"kod": kod, "son_fiyat": sonuc["son_fiyat"]}
        for ad, d in sonuc["donemler"].items():
            o = d["ozet"]
            satir[ad] = {k: o[k] for k in [
                "beta", "yukselis_beta", "dusus_beta", "up_capture", "down_capture",
                "r2", "yon_uyumu", "etiket", "gun_sayisi", "hareketli_beta_son",
                "sert_yukselis_hisse_ort", "sert_dusus_hisse_ort"]}
        liste.append(satir)

    ozet = {
        "guncelleme": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "endeks_son_tarih": endeks.index.max().strftime("%Y-%m-%d"),
        "endeks_son": round(float(endeks.iloc[-1]), 2),
        "esik": ESIK,
        "pencere": PENCERE,
        "atlanan": atlanan,
        "hisseler": sorted(liste, key=lambda s: s["kod"]),
    }
    (cikti / "ozet.json").write_text(
        json.dumps(_temiz(ozet), ensure_ascii=False, indent=0), encoding="utf-8")
    return ozet


def yfinance_kapanislar(kodlar: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    import yfinance as yf

    semboller = [f"{k}.IS" for k in kodlar] + ["XU100.IS"]
    ham = yf.download(semboller, period="3y", auto_adjust=True, progress=False, threads=True)
    kapanis = ham["Close"]
    kapanis.index = pd.to_datetime(kapanis.index).tz_localize(None)
    endeks = kapanis.pop("XU100.IS").dropna().rename("XU100")
    kapanis.columns = [c.replace(".IS", "") for c in kapanis.columns]
    return kapanis, endeks


def main():
    kodlar = hisseleri_oku()
    kapanis, endeks = yfinance_kapanislar(kodlar)
    if endeks.empty:
        raise SystemExit("XU100 verisi gelmedi, site verisi güncellenmedi.")
    ozet = site_verisi_uret(kapanis, endeks)
    print(f"{len(ozet['hisseler'])} hisse yazıldı. Atlanan: {', '.join(ozet['atlanan']) or 'yok'}")


if __name__ == "__main__":
    main()
