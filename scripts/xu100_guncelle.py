"""data/xu100.csv dosyasını yfinance ile günceller (son 3 yıl).

GitHub Actions her iş günü akşamı bu dosyayı çalıştırır.
Elle çalıştırmak için: python scripts/xu100_guncelle.py
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

HEDEF = Path(__file__).resolve().parent.parent / "data" / "xu100.csv"


def main():
    veri = yf.download("XU100.IS", period="3y", auto_adjust=True, progress=False)
    if veri is None or veri.empty:
        raise SystemExit("XU100 verisi gelmedi, dosya değiştirilmedi.")
    kapanis = veri["Close"]
    if isinstance(kapanis, pd.DataFrame):
        kapanis = kapanis.iloc[:, 0]
    tablo = pd.DataFrame({
        "Tarih": pd.to_datetime(kapanis.index).tz_localize(None).strftime("%Y-%m-%d"),
        "Kapanis": kapanis.round(2).values,
    }).dropna()
    HEDEF.parent.mkdir(exist_ok=True)
    tablo.to_csv(HEDEF, index=False)
    print(f"{len(tablo)} gün yazıldı, son tarih: {tablo['Tarih'].iloc[-1]}")


if __name__ == "__main__":
    main()
