"""Hissenin BIST 100'e tepkisini ölçen hesaplar.

Tüm fonksiyonlar esle() çıktısını, yani 'hisse' ve 'endeks' günlük getiri
sütunları olan tabloyu kullanır.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_SERT_GUN = 20  # Bunun altında sert gün sonucu güvenilir sayılmaz


def beta(hisse: pd.Series, endeks: pd.Series) -> float:
    """Beta = Kovaryans(hisse, endeks) / Varyans(endeks)."""
    if len(endeks) < 3 or endeks.var() == 0:
        return float("nan")
    return float(np.cov(hisse, endeks, ddof=1)[0, 1] / endeks.var(ddof=1))


def korelasyon(tablo: pd.DataFrame) -> float:
    return float(tablo["hisse"].corr(tablo["endeks"]))


def yukselis_dusus_beta(tablo: pd.DataFrame) -> tuple[float, float]:
    """Endeksin yükseldiği ve düştüğü günler için ayrı beta."""
    yukselis = tablo[tablo["endeks"] > 0]
    dusus = tablo[tablo["endeks"] < 0]
    return beta(yukselis["hisse"], yukselis["endeks"]), beta(dusus["hisse"], dusus["endeks"])


def yakalama_oranlari(tablo: pd.DataFrame) -> tuple[float, float]:
    """Up capture / Down capture (yüzde).

    Up capture %120 ise: endeks yükseldiği günlerde hisse ortalama olarak
    endeksin yükselişinin 1,2 katı kadar yükselmiş demektir.
    Down capture düşükse hisse düşüşlerde endeksten daha az kaybediyor demektir.
    """
    yukselis = tablo[tablo["endeks"] > 0]
    dusus = tablo[tablo["endeks"] < 0]
    up = yukselis["hisse"].mean() / yukselis["endeks"].mean() * 100 if len(yukselis) else float("nan")
    down = dusus["hisse"].mean() / dusus["endeks"].mean() * 100 if len(dusus) else float("nan")
    return float(up), float(down)


def sert_gunler(tablo: pd.DataFrame, esik_yuzde: float = 2.0) -> dict:
    """Endeksin ±esik'ten fazla oynadığı günlerde hissenin ortalama tepkisi."""
    esik = esik_yuzde / 100
    sert_yukselis = tablo[tablo["endeks"] >= esik]
    sert_dusus = tablo[tablo["endeks"] <= -esik]
    return {
        "esik_yuzde": esik_yuzde,
        "sert_yukselis_gun": int(len(sert_yukselis)),
        "sert_yukselis_endeks_ort": float(sert_yukselis["endeks"].mean() * 100) if len(sert_yukselis) else float("nan"),
        "sert_yukselis_hisse_ort": float(sert_yukselis["hisse"].mean() * 100) if len(sert_yukselis) else float("nan"),
        "sert_dusus_gun": int(len(sert_dusus)),
        "sert_dusus_endeks_ort": float(sert_dusus["endeks"].mean() * 100) if len(sert_dusus) else float("nan"),
        "sert_dusus_hisse_ort": float(sert_dusus["hisse"].mean() * 100) if len(sert_dusus) else float("nan"),
        "guvenilir": bool(len(sert_yukselis) + len(sert_dusus) >= MIN_SERT_GUN),
    }


def yon_uyumu(tablo: pd.DataFrame) -> float:
    """Hissenin endeksle aynı yöne gittiği günlerin yüzdesi (yatay günler hariç)."""
    hareketli = tablo[(tablo["hisse"] != 0) & (tablo["endeks"] != 0)]
    if hareketli.empty:
        return float("nan")
    ayni = np.sign(hareketli["hisse"]) == np.sign(hareketli["endeks"])
    return float(ayni.mean() * 100)


def hareketli_beta(tablo: pd.DataFrame, pencere: int = 60) -> pd.Series:
    """Son 'pencere' günlük veriyle hesaplanan, zaman içinde değişen beta."""
    kov = tablo["hisse"].rolling(pencere).cov(tablo["endeks"])
    var = tablo["endeks"].rolling(pencere).var()
    return (kov / var).dropna().rename("hareketli_beta")


def etiket(b: float) -> str:
    if np.isnan(b):
        return "Belirsiz"
    if b < 0.8:
        return "Defansif"
    if b <= 1.2:
        return "Endeksle paralel"
    return "Agresif"


def hepsini_hesapla(tablo: pd.DataFrame, esik_yuzde: float = 2.0, pencere: int = 60) -> dict:
    """Tüm ölçüleri tek sözlükte toplar."""
    b = beta(tablo["hisse"], tablo["endeks"])
    k = korelasyon(tablo)
    b_yuk, b_dus = yukselis_dusus_beta(tablo)
    up, down = yakalama_oranlari(tablo)
    hb = hareketli_beta(tablo, pencere) if len(tablo) > pencere else pd.Series(dtype=float)
    return {
        "baslangic": tablo.index.min().date().isoformat(),
        "bitis": tablo.index.max().date().isoformat(),
        "gun_sayisi": int(len(tablo)),
        "beta": b,
        "yukselis_beta": b_yuk,
        "dusus_beta": b_dus,
        "up_capture": up,
        "down_capture": down,
        "korelasyon": k,
        "r2": k ** 2,
        "yon_uyumu": yon_uyumu(tablo),
        "hareketli_beta_son": float(hb.iloc[-1]) if len(hb) else float("nan"),
        "etiket": etiket(b),
        **sert_gunler(tablo, esik_yuzde),
    }
