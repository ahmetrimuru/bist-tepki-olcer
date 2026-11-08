"""Sade (renksiz) grafikler: dağılım + regresyon çizgisi ve hareketli beta."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Ekran olmadan dosyaya çiz
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .hesap import hareketli_beta  # noqa: E402


def dagilim_grafigi(tablo: pd.DataFrame, ad: str, b: float, klasor: Path) -> Path:
    x = tablo["endeks"] * 100
    y = tablo["hisse"] * 100
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(x, y, s=10, color="#555555", alpha=0.6)
    if len(x) > 2:
        egim, kesim = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, egim * xs + kesim, color="black", linewidth=1.5,
                label=f"Beta = {b:.2f}")
        ax.legend(frameon=False)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.axvline(0, color="#999999", linewidth=0.8)
    ax.set_xlabel("BIST 100 günlük getiri (%)")
    ax.set_ylabel(f"{ad} günlük getiri (%)")
    ax.set_title(f"{ad} - BIST 100 günlük tepki")
    ax.grid(color="#e5e5e5", linewidth=0.6)
    yol = klasor / f"{ad}_dagilim.png"
    fig.tight_layout()
    fig.savefig(yol, dpi=130)
    plt.close(fig)
    return yol


def hareketli_beta_grafigi(tablo: pd.DataFrame, ad: str, klasor: Path, pencere: int = 60) -> Path | None:
    hb = hareketli_beta(tablo, pencere)
    if hb.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(hb.index, hb.values, color="black", linewidth=1.2)
    ax.axhline(1, color="#999999", linewidth=0.8, linestyle="--", label="Beta = 1")
    ax.set_ylabel("Beta")
    ax.set_title(f"{ad} - {pencere} günlük hareketli beta")
    ax.legend(frameon=False)
    ax.grid(color="#e5e5e5", linewidth=0.6)
    yol = klasor / f"{ad}_hareketli_beta.png"
    fig.tight_layout()
    fig.savefig(yol, dpi=130)
    plt.close(fig)
    return yol
