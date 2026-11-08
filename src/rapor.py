"""Sonuçları sade bir metin özetine ve CSV dosyasına çevirir."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def _y(sayi: float, ondalik: int = 2) -> str:
    """Sayıyı Türkçe biçimde yazar (virgüllü ondalık)."""
    if sayi is None or (isinstance(sayi, float) and math.isnan(sayi)):
        return "-"
    return f"{sayi:.{ondalik}f}".replace(".", ",")


def ozet_metni(ad: str, s: dict) -> str:
    satirlar = [
        f"=== {ad} / BIST 100 ===",
        f"Dönem: {s['baslangic']} - {s['bitis']} ({s['gun_sayisi']} işlem günü)",
        "",
        f"Beta              : {_y(s['beta'])}  -> {s['etiket']}",
        f"Yükseliş betası   : {_y(s['yukselis_beta'])}",
        f"Düşüş betası      : {_y(s['dusus_beta'])}",
        f"Up capture        : %{_y(s['up_capture'], 0)}",
        f"Down capture      : %{_y(s['down_capture'], 0)}",
        f"Korelasyon / R²   : {_y(s['korelasyon'])} / {_y(s['r2'])}",
        f"Yön uyumu         : %{_y(s['yon_uyumu'], 0)}",
        f"Son 60 gün betası : {_y(s['hareketli_beta_son'])}",
        "",
        f"Sert günler (endeks ±%{_y(s['esik_yuzde'], 1)}):",
        f"  Yükseliş: {s['sert_yukselis_gun']} gün, endeks ort. %{_y(s['sert_yukselis_endeks_ort'])}, "
        f"hisse ort. %{_y(s['sert_yukselis_hisse_ort'])}",
        f"  Düşüş   : {s['sert_dusus_gun']} gün, endeks ort. %{_y(s['sert_dusus_endeks_ort'])}, "
        f"hisse ort. %{_y(s['sert_dusus_hisse_ort'])}",
    ]
    if not s["guvenilir"]:
        satirlar.append("  Uyarı: örnek az, güvenilirlik düşük. Eşiği düşürmeyi deneyin (--esik 1.5).")

    satirlar += ["", "Yorum: " + yorum(s)]
    return "\n".join(satirlar)


def yorum(s: dict) -> str:
    """Basit, tek cümlelik yorumlar üretir."""
    parcalar = []
    b = s["beta"]
    if not math.isnan(b):
        parcalar.append(
            f"BIST 100 %1 hareket ettiğinde hisse ortalama %{_y(b)} hareket ediyor."
        )
    yb, db = s["yukselis_beta"], s["dusus_beta"]
    if not (math.isnan(yb) or math.isnan(db)):
        if yb - db > 0.15:
            parcalar.append("Yükselişlere düşüşlerden daha güçlü tepki veriyor (olumlu asimetri).")
        elif db - yb > 0.15:
            parcalar.append("Düşüşlere yükselişlerden daha güçlü tepki veriyor (olumsuz asimetri).")
        else:
            parcalar.append("Yükseliş ve düşüşlere benzer güçte tepki veriyor.")
    if not math.isnan(s["r2"]) and s["r2"] < 0.3:
        parcalar.append("Endeksle bağı zayıf; hisse daha çok kendi haberleriyle hareket ediyor.")
    return " ".join(parcalar)


def karsilastirma_tablosu(sonuclar: dict[str, dict]) -> pd.DataFrame:
    sutunlar = ["beta", "yukselis_beta", "dusus_beta", "up_capture", "down_capture",
                "korelasyon", "r2", "yon_uyumu", "etiket", "gun_sayisi"]
    tablo = pd.DataFrame(sonuclar).T[sutunlar]
    for s in sutunlar:
        if s != "etiket":
            tablo[s] = pd.to_numeric(tablo[s])
    tablo["gun_sayisi"] = tablo["gun_sayisi"].astype(int)
    return tablo.sort_values("beta", ascending=False).round(2)


def csv_kaydet(sonuclar: dict[str, dict], yol: Path) -> Path:
    pd.DataFrame(sonuclar).T.to_csv(yol, index_label="hisse", encoding="utf-8-sig")
    return yol
