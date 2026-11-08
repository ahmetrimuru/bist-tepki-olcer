"""Web sayfası verisi üretimi testi (yapay veriyle, internet gerekmez)."""

import json

import numpy as np
import pandas as pd

from scripts.web_verisi import hisseleri_oku, site_verisi_uret


def test_site_verisi(tmp_path):
    rng = np.random.default_rng(0)
    g = pd.bdate_range(end="2026-11-06", periods=600)
    e = rng.normal(0, 0.015, 600)
    endeks = pd.Series(10000 * np.cumprod(1 + e), index=g)
    kapanis = pd.DataFrame({
        "AAA": 50 * np.cumprod(1 + 1.4 * e + rng.normal(0, 0.005, 600)),
        "BBB": 20 * np.cumprod(1 + 0.6 * e + rng.normal(0, 0.005, 600)),
        "YOK": np.nan,
    }, index=g)

    ozet = site_verisi_uret(kapanis, endeks, tmp_path)

    assert [h["kod"] for h in ozet["hisseler"]] == ["AAA", "BBB"]
    assert ozet["atlanan"] == ["YOK"]
    assert abs(ozet["hisseler"][0]["2y"]["beta"] - 1.4) < 0.1
    detay = json.loads((tmp_path / "hisse" / "AAA.json").read_text(encoding="utf-8"))
    assert set(detay["donemler"]) == {"1y", "2y"}
    assert len(detay["donemler"]["2y"]["dagilim"]) > 400
    json.loads((tmp_path / "ozet.json").read_text(encoding="utf-8"))  # geçerli JSON


def test_hisse_listesi(tmp_path):
    yol = tmp_path / "liste.txt"
    yol.write_text("# yorum\nthyao\n\nASELS  # savunma\nTHYAO\n", encoding="utf-8")
    assert hisseleri_oku(yol) == ["THYAO", "ASELS"]
