"""Hesap fonksiyonları için testler. Gerçek veri gerekmez, yapay veri kullanılır."""

import numpy as np
import pandas as pd
import pytest

from src import hesap


def yapay_tablo(beta=1.5, gurultu=0.002, gun=500, tohum=1):
    """Beta'sı bilinen yapay hisse-endeks getiri tablosu."""
    rng = np.random.default_rng(tohum)
    endeks = rng.normal(0.0005, 0.015, gun)
    hisse = beta * endeks + rng.normal(0, gurultu, gun)
    tarih = pd.bdate_range("2024-01-01", periods=gun)
    return pd.DataFrame({"hisse": hisse, "endeks": endeks}, index=tarih)


def test_beta_bilinen_degeri_bulur():
    t = yapay_tablo(beta=1.5)
    assert hesap.beta(t["hisse"], t["endeks"]) == pytest.approx(1.5, abs=0.03)


def test_hisse_endeksin_aynisiysa_beta_bir():
    t = yapay_tablo(beta=1.0, gurultu=0.0)
    assert hesap.beta(t["hisse"], t["endeks"]) == pytest.approx(1.0)
    assert hesap.korelasyon(t) == pytest.approx(1.0)
    assert hesap.yon_uyumu(t) == pytest.approx(100.0)


def test_asimetrik_tepki():
    t = yapay_tablo(beta=1.0, gurultu=0.0)
    # Düşüş günlerinde hisse iki kat düşsün
    t.loc[t["endeks"] < 0, "hisse"] = 2 * t.loc[t["endeks"] < 0, "endeks"]
    yuk, dus = hesap.yukselis_dusus_beta(t)
    assert yuk == pytest.approx(1.0)
    assert dus == pytest.approx(2.0)
    up, down = hesap.yakalama_oranlari(t)
    assert up == pytest.approx(100.0)
    assert down == pytest.approx(200.0)


def test_sert_gunler_ve_guvenilirlik():
    t = yapay_tablo(beta=1.0, gurultu=0.0, gun=100)
    t["endeks"] = 0.001
    t.iloc[:5, t.columns.get_loc("endeks")] = 0.03
    t.iloc[5:8, t.columns.get_loc("endeks")] = -0.025
    t["hisse"] = t["endeks"] * 1.2
    s = hesap.sert_gunler(t, 2.0)
    assert s["sert_yukselis_gun"] == 5
    assert s["sert_dusus_gun"] == 3
    assert s["sert_yukselis_hisse_ort"] == pytest.approx(3.6)
    assert s["guvenilir"] is False


def test_hareketli_beta_uzunlugu():
    t = yapay_tablo(gun=200)
    hb = hesap.hareketli_beta(t, 60)
    assert len(hb) == 200 - 59
    assert hb.mean() == pytest.approx(1.5, abs=0.1)


@pytest.mark.parametrize("b,beklenen", [(0.5, "Defansif"), (1.0, "Endeksle paralel"), (1.6, "Agresif")])
def test_etiket(b, beklenen):
    assert hesap.etiket(b) == beklenen


def test_hepsini_hesapla_anahtarlar():
    s = hesap.hepsini_hesapla(yapay_tablo())
    for anahtar in ["beta", "yukselis_beta", "dusus_beta", "up_capture", "down_capture",
                    "r2", "yon_uyumu", "etiket", "sert_dusus_gun", "guvenilir"]:
        assert anahtar in s
