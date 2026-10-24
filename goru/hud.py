"""Fütüristik ekran üstü göstergeler (HUD) ve FPS sayacı."""

import math
import time

import cv2
import numpy as np

from .el import EL_BAGLANTILARI

# BGR renkler
CAMGOBEGI = (255, 220, 0)  # HUD mavisi
TURUNCU = (0, 165, 255)
KIRMIZI = (40, 40, 230)
YESIL = (80, 220, 80)
BEYAZ = (240, 240, 240)
FONT = cv2.FONT_HERSHEY_SIMPLEX


class FpsSayaci:
    def __init__(self, yumusatma=0.9):
        self._yumusatma = yumusatma
        self._onceki = None
        self.fps = 0.0

    def tik(self):
        simdi = time.perf_counter()
        if self._onceki is not None:
            anlik = 1.0 / max(simdi - self._onceki, 1e-6)
            self.fps = anlik if self.fps == 0 else self._yumusatma * self.fps + (1 - self._yumusatma) * anlik
        self._onceki = simdi
        return self.fps


def iskelet_ciz(kare, noktalar, renk=CAMGOBEGI):
    for a, b in EL_BAGLANTILARI:
        pa = tuple(int(v) for v in noktalar[a, :2])
        pb = tuple(int(v) for v in noktalar[b, :2])
        cv2.line(kare, pa, pb, renk, 2, cv2.LINE_AA)
    for x, y, _ in noktalar:
        cv2.circle(kare, (int(x), int(y)), 3, BEYAZ, -1, cv2.LINE_AA)


def reaktor_halkasi(kare, merkez, oran, yaricap=26, renk=CAMGOBEGI):
    """Ark reaktörü tarzı ilerleme halkası. oran: 0.0 - 1.0"""
    merkez = (int(merkez[0]), int(merkez[1]))
    cv2.circle(kare, merkez, yaricap, (90, 90, 90), 2, cv2.LINE_AA)
    bitis = int(360 * float(np.clip(oran, 0, 1)))
    cv2.ellipse(kare, merkez, (yaricap, yaricap), -90, 0, bitis, renk, 4, cv2.LINE_AA)
    for i in range(12):  # Reaktör dişleri
        aci = math.radians(i * 30)
        ic = (int(merkez[0] + (yaricap - 9) * math.cos(aci)), int(merkez[1] + (yaricap - 9) * math.sin(aci)))
        dis = (int(merkez[0] + (yaricap - 5) * math.cos(aci)), int(merkez[1] + (yaricap - 5) * math.sin(aci)))
        cv2.line(kare, ic, dis, renk, 1, cv2.LINE_AA)


def panel(kare, satirlar, sol_ust=(15, 15), baslik="PYTHON CV"):
    """Yarı saydam bilgi paneli. satirlar: [(metin, renk), ...] veya [metin, ...]
    Not: cv2.putText Türkçe karakter desteklemez, metinler ASCII yazılmalı."""
    satirlar = [s if isinstance(s, tuple) else (s, BEYAZ) for s in satirlar]
    x, y = sol_ust
    genislik = 20 + max(cv2.getTextSize(m, FONT, 0.55, 1)[0][0] for m, _ in satirlar + [(baslik, None)])
    yukseklik = 40 + 24 * len(satirlar)

    bolge = kare[y : y + yukseklik, x : x + genislik]
    kare[y : y + yukseklik, x : x + genislik] = cv2.addWeighted(bolge, 0.35, np.zeros_like(bolge), 0.65, 0)
    cv2.rectangle(kare, (x, y), (x + genislik, y + yukseklik), CAMGOBEGI, 1, cv2.LINE_AA)
    cv2.line(kare, (x, y + 30), (x + genislik, y + 30), CAMGOBEGI, 1, cv2.LINE_AA)
    cv2.putText(kare, baslik, (x + 10, y + 21), FONT, 0.6, CAMGOBEGI, 2, cv2.LINE_AA)
    for i, (metin, renk) in enumerate(satirlar):
        cv2.putText(kare, metin, (x + 10, y + 52 + 24 * i), FONT, 0.55, renk, 1, cv2.LINE_AA)


def cubuk(kare, sol_ust, boyut, oran, etiket="", renk=CAMGOBEGI):
    """Dikey seviye çubuğu (ses seviyesi vb.)."""
    x, y = sol_ust
    g, h = boyut
    cv2.rectangle(kare, (x, y), (x + g, y + h), (90, 90, 90), 2)
    dolu = int(h * float(np.clip(oran, 0, 1)))
    cv2.rectangle(kare, (x + 3, y + h - dolu), (x + g - 3, y + h - 3), renk, -1)
    if etiket:
        cv2.putText(kare, etiket, (x - 5, y + h + 25), FONT, 0.6, renk, 2, cv2.LINE_AA)
