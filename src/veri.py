"""Veri okuma, BIST 100 verisini getirme ve iki seriyi eşleştirme."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Kullanıcı dosyalarında karşılaşılabilecek sütun adları (küçük harfe çevrilmiş)
TARIH_ADLARI = ["tarih", "date", "datetime", "gün", "gun"]
KAPANIS_ADLARI = [
    "kapanış", "kapanis", "kapanış fiyatı", "kapanis fiyati",
    "adj close", "adj_close", "close", "son", "şimdi", "simdi", "fiyat",
]

# Bir günde bundan büyük hareket varsa bedelsiz/bölünme şüphesi
SUPHELI_HAREKET = 0.15

PROJE_KOKU = Path(__file__).resolve().parent.parent
YEDEK_XU100 = PROJE_KOKU / "data" / "xu100.csv"


def _sutun_bul(sutunlar, adaylar):
    """Sütun adları arasından aday listesine uyan ilkini döndürür."""
    temiz = {str(s).strip().lower(): s for s in sutunlar}
    for aday in adaylar:
        if aday in temiz:
            return temiz[aday]
    return None


def _sayiya_cevir(seri: pd.Series) -> pd.Series:
    """'1.234,56' veya '1234.56' gibi yazımları sayıya çevirir."""
    if pd.api.types.is_numeric_dtype(seri):
        return seri.astype(float)

    def cevir(deger):
        if pd.isna(deger):
            return None
        metin = str(deger).strip().replace(" ", "").replace("₺", "")
        if "," in metin and "." in metin:
            # Hangisi sondaysa ondalık ayırıcı odur
            if metin.rfind(",") > metin.rfind("."):
                metin = metin.replace(".", "").replace(",", ".")
            else:
                metin = metin.replace(",", "")
        elif "," in metin:
            metin = metin.replace(",", ".")
        try:
            return float(metin)
        except ValueError:
            return None

    return seri.map(cevir).astype(float)


def _tarihe_cevir(seri: pd.Series) -> pd.Series:
    """Farklı tarih biçimlerini tanır (08.11.2026, 2026-11-08, 08/11/2026)."""
    if pd.api.types.is_datetime64_any_dtype(seri):
        return seri.dt.tz_localize(None) if seri.dt.tz is not None else seri
    metin = seri.astype(str).str.strip()
    # Önce yıl başta olan ISO biçimini dene
    iso = pd.to_datetime(metin, format="%Y-%m-%d", errors="coerce")
    if iso.notna().mean() > 0.9:
        return iso
    # Türkiye'de yaygın olan gün başta biçim
    return pd.to_datetime(metin, dayfirst=True, errors="coerce", format="mixed")


def dosya_oku(yol: str | Path) -> pd.Series:
    """CSV veya Excel dosyasından tarih-kapanış serisi okur.

    Dönen seri tarihe göre sıralı, tarih indeksli kapanış fiyatlarıdır.
    """
    yol = Path(yol)
    if not yol.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {yol}")

    if yol.suffix.lower() in (".xlsx", ".xls"):
        tablo = pd.read_excel(yol)
    else:
        # Ayırıcıyı (virgül / noktalı virgül / sekme) otomatik bul
        tablo = pd.read_csv(yol, sep=None, engine="python", encoding_errors="replace")

    tarih_sutunu = _sutun_bul(tablo.columns, TARIH_ADLARI)
    kapanis_sutunu = _sutun_bul(tablo.columns, KAPANIS_ADLARI)
    if tarih_sutunu is None or kapanis_sutunu is None:
        raise ValueError(
            f"{yol.name}: 'Tarih' ve 'Kapanış' sütunları bulunamadı. "
            f"Dosyadaki sütunlar: {list(tablo.columns)}"
        )

    seri = pd.Series(
        _sayiya_cevir(tablo[kapanis_sutunu]).values,
        index=_tarihe_cevir(tablo[tarih_sutunu]),
        name=yol.stem.upper(),
    )
    seri = seri[seri.index.notna()].dropna()
    seri = seri[~seri.index.duplicated(keep="last")].sort_index()
    if len(seri) < 30:
        raise ValueError(f"{yol.name}: en az 30 günlük veri gerekli, {len(seri)} gün bulundu.")
    return seri


def yfinance_getir(kod: str, baslangic, bitis) -> pd.Series:
    """yfinance ile kapanış verisi çeker (örnek kod: 'XU100.IS', 'THYAO.IS')."""
    import yfinance as yf  # Sadece gerektiğinde yüklensin

    veri = yf.download(
        kod, start=baslangic, end=bitis + pd.Timedelta(days=1),
        auto_adjust=True, progress=False,
    )
    if veri is None or veri.empty:
        raise RuntimeError(f"{kod} için veri gelmedi.")
    kapanis = veri["Close"]
    if isinstance(kapanis, pd.DataFrame):  # Yeni yfinance sürümleri çok sütun döndürebilir
        kapanis = kapanis.iloc[:, 0]
    kapanis.index = pd.to_datetime(kapanis.index).tz_localize(None)
    return kapanis.dropna().rename(kod.replace(".IS", ""))


def xu100_getir(baslangic, bitis) -> tuple[pd.Series, str]:
    """BIST 100 verisini getirir. Önce yfinance, olmazsa data/xu100.csv.

    Dönüş: (seri, kaynak açıklaması)
    """
    try:
        seri = yfinance_getir("XU100.IS", baslangic, bitis)
        return seri.rename("XU100"), "yfinance"
    except Exception as hata:  # noqa: BLE001 - her türlü hatada yedeğe geç
        if YEDEK_XU100.exists():
            seri = dosya_oku(YEDEK_XU100).rename("XU100")
            seri = seri[(seri.index >= baslangic) & (seri.index <= bitis)]
            return seri, f"data/xu100.csv (yfinance kullanılamadı: {hata})"
        raise RuntimeError(
            "BIST 100 verisi alınamadı. yfinance kurun (pip install yfinance) "
            "veya data/xu100.csv dosyasını ekleyin."
        ) from hata


def esle(hisse: pd.Series, endeks: pd.Series) -> pd.DataFrame:
    """İki seriyi ortak tarihlerde birleştirir ve günlük getirileri hesaplar.

    Dönen tablo sütunları: hisse_fiyat, endeks_fiyat, hisse, endeks
    (hisse ve endeks sütunları günlük getiridir, 0.01 = %1).
    """
    tablo = pd.concat(
        [hisse.rename("hisse_fiyat"), endeks.rename("endeks_fiyat")], axis=1, join="inner"
    ).dropna()
    tablo["hisse"] = tablo["hisse_fiyat"].pct_change()
    tablo["endeks"] = tablo["endeks_fiyat"].pct_change()
    return tablo.dropna()


def supheli_gunler(tablo: pd.DataFrame, esik: float = SUPHELI_HAREKET) -> pd.DataFrame:
    """Hissenin bir günde esikten fazla oynadığı günleri döndürür."""
    return tablo[tablo["hisse"].abs() > esik]
