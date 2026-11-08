"""Dosya okuma ve eşleştirme testleri."""

import pandas as pd
import pytest

from src import veri


def _yaz(tmp_path, ad, icerik):
    yol = tmp_path / ad
    yol.write_text(icerik, encoding="utf-8")
    return yol


def _gunler(n=40):
    return pd.bdate_range("2025-01-01", periods=n)


def test_turkce_csv_okur(tmp_path):
    satirlar = ["Tarih;Kapanış"] + [
        f"{g.strftime('%d.%m.%Y')};1.234,{i:02d}" for i, g in enumerate(_gunler())
    ]
    seri = veri.dosya_oku(_yaz(tmp_path, "thyao.csv", "\n".join(satirlar)))
    assert seri.name == "THYAO"
    assert len(seri) == 40
    assert seri.iloc[0] == pytest.approx(1234.00)
    assert seri.index[0] == pd.Timestamp("2025-01-01")


def test_ingilizce_csv_okur(tmp_path):
    satirlar = ["Date,Close"] + [f"{g.date()},{100 + i}.5" for i, g in enumerate(_gunler())]
    seri = veri.dosya_oku(_yaz(tmp_path, "asels.csv", "\n".join(satirlar)))
    assert seri.iloc[-1] == pytest.approx(139.5)


def test_eksik_sutun_hata_verir(tmp_path):
    with pytest.raises(ValueError, match="Tarih"):
        veri.dosya_oku(_yaz(tmp_path, "x.csv", "a,b\n1,2\n"))


def test_esle_ortak_gunleri_kullanir():
    g = _gunler(10)
    hisse = pd.Series(range(100, 110), index=g, dtype=float)
    endeks = pd.Series(range(1000, 1008), index=g[2:], dtype=float)
    tablo = veri.esle(hisse, endeks)
    assert len(tablo) == 7  # 8 ortak gün, ilk getiri boş
    assert tablo.index[0] == g[3]


def test_supheli_gun_bulur():
    g = _gunler(5)
    hisse = pd.Series([100, 101, 50, 51, 52], index=g, dtype=float)  # bölünme gibi
    endeks = pd.Series([10, 10.1, 10.2, 10.1, 10.0], index=g)
    supheli = veri.supheli_gunler(veri.esle(hisse, endeks))
    assert list(supheli.index) == [g[2]]
