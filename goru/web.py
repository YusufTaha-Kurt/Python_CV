"""Yerel canlı yayın sunucusu: tarayıcıya video, durum ve olay akışı; tarayıcıdan komut.

Sadece Python standart kütüphanesi kullanılır ve sunucu yalnızca 127.0.0.1'e bağlanır
(ağdaki başka cihazlar erişemez).

    GET  /              kök klasördeki index.html
    GET  /<dosya>       kök klasörden statik dosya (klasör dışına çıkış engellenir)
    GET  /<önek>/...    ek klasörlerden statik dosya (örn. /icerik/resim.png)
    GET  /video.mjpg    MJPEG video akışı (<img src="/video.mjpg"> ile gösterilir)
    GET  /durum         SSE: her zaman SADECE en son durum (ara durumlar atlanır)
    GET  /olaylar       SSE: olayların HEPSİ, sırayla (her istemcinin kendi kuyruğu)
                        ?gecmis=1 ile bağlanınca önce son 50 olay gönderilir (kontrol paneli için)
    GET  /durum.json    En son durumun anlık görüntüsü
    POST /komut         JSON komut {"a": "...", ...}; izin listesinde olmayanlar reddedilir

Üç farklı akış türü vardır, çünkü her biri farklı bir ihtiyaca hizmet eder:
    MJPEG   Video. Tarayıcı <img> etiketiyle sürekli yenilenen JPEG gösterir.
    SSE     (Server-Sent Events) Sunucudan tarayıcıya tek yönlü, metin tabanlı canlı akış.
            /durum "en son hâli" verir (sahne çizimi için ara kareler önemsizdir);
            /olaylar ise HİÇBİRİNİ kaçırmaz (olay günlüğü, kontrol paneli için).
    POST    Tarayıcıdan Python'a komut. Güvenlik için sadece izin listesindekiler kabul edilir.
"""

import json
import mimetypes
import queue
import sys
import threading
import urllib.parse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KALP_ATISI = 15.0  # Saniye: boşta kalan SSE bağlantısına yorum satırı gönderilir
_BAGLANTI_KAPANDI = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)


class _Sunucu(ThreadingHTTPServer):
    """Her istek ayrı iş parçacığında çalışır; uzun süren SSE / MJPEG bağlantıları diğerlerini engellemez."""

    daemon_threads = True

    def handle_error(self, request, client_address):
        """Beklenen bağlantı kopmalarını sessizce yut, gerçek hataları normal şekilde bildir."""
        # Tarayıcı sekmesi kapanınca bağlantı koparılır: bu bir hata değil, günlüğe yazılmasın
        if isinstance(sys.exc_info()[1], _BAGLANTI_KAPANDI):
            return
        super().handle_error(request, client_address)


class CanliYayin:
    """Yerel HTTP sunucusu. Ana döngü `kare_yayinla`, `durum_yayinla`, `olay_yayinla` ile veri verir;
    tarayıcı ya da başka bir uygulama bağlanıp okur. `baslat()` adresi döndürür."""

    def __init__(self, kok_klasor=None, port=8765, ek_klasorler=None, izinli_komutlar=()):
        self.kok = Path(kok_klasor).resolve() if kok_klasor else None
        self.ek_klasorler = {onek.strip("/"): Path(yol).resolve() for onek, yol in (ek_klasorler or {}).items()}
        self.izinli_komutlar = set(izinli_komutlar)
        self.port = port
        self._kosul = threading.Condition()
        self._jpeg, self._jpeg_no = None, 0
        self._durum, self._durum_no = b"{}", 0
        self._video_istemcileri = 0
        self._olay_kuyruklari = []
        self._son_olaylar = deque(maxlen=50)
        self._komutlar = queue.Queue()
        self._calisiyor = False
        self._sunucu = None

    # --- Yayın tarafı (ana döngüden çağrılır) ---

    @property
    def video_izleniyor(self):
        """Şu an videoyu izleyen tarayıcı var mı? Yoksa JPEG kodlaması yapılmaz."""
        return self._video_istemcileri > 0

    def kare_yayinla(self, kare_bgr, kalite=75):
        """Kareyi JPEG olarak yayınlar. İzleyen yoksa kodlama yapılmaz (işlemci tasarrufu)."""
        if not self.video_izleniyor:
            return
        import cv2  # Burada: sunucunun geri kalanı OpenCV olmadan da test edilebilsin

        basarili, jpeg = cv2.imencode(".jpg", kare_bgr, [cv2.IMWRITE_JPEG_QUALITY, kalite])
        if basarili:
            with self._kosul:
                self._jpeg, self._jpeg_no = jpeg.tobytes(), self._jpeg_no + 1
                self._kosul.notify_all()

    def durum_yayinla(self, durum):
        """Son durumu (JSON'a çevrilebilir sözlük) günceller; /durum akışındaki herkese iletilir."""
        veri = json.dumps(durum, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        with self._kosul:
            self._durum, self._durum_no = veri, self._durum_no + 1
            self._kosul.notify_all()

    def olay_yayinla(self, olay):
        """olay: JSON'a çevrilebilir sözlük. Bağlı her istemciye sırayla iletilir."""
        veri = json.dumps(olay, ensure_ascii=False).encode("utf-8")
        with self._kosul:
            self._son_olaylar.append(veri)
            for kuyruk in self._olay_kuyruklari:
                if kuyruk.qsize() < 1000:  # Yavaş istemci belleği şişirmesin
                    kuyruk.put(veri)

    def komutlari_al(self):
        """Tarayıcıdan / dış uygulamadan gelen komutlar (ana döngüde işlenmek üzere)."""
        komutlar = []
        while not self._komutlar.empty():
            komutlar.append(self._komutlar.get_nowait())
        return komutlar

    # --- Sunucu ---

    def baslat(self):
        """Sunucuyu arka planda başlatır ve adresini ("http://127.0.0.1:PORT/") döndürür. port=0: boş port seçilir."""
        yayin = self

        class Isleyici(BaseHTTPRequestHandler):
            """Gelen HTTP isteklerini yukarıdaki yayın nesnesinin ilgili yöntemine yönlendirir."""

            def log_message(self, *_):
                pass  # Her isteği konsola yazma (video akışı saniyede onlarca satır üretirdi)

            def do_GET(self):
                """GET yolları: /video.mjpg, /durum, /olaylar, /durum.json, gerisi statik dosya."""
                yol = self.path.split("?", 1)[0]
                if yol == "/video.mjpg":
                    return yayin._mjpeg(self)
                if yol == "/durum":
                    return yayin._sse_durum(self)
                if yol == "/olaylar":
                    return yayin._sse_olaylar(self, gecmis="gecmis=1" in self.path)
                if yol == "/durum.json":
                    with yayin._kosul:
                        veri = yayin._durum
                    return yayin._gonder(self, 200, veri, "application/json; charset=utf-8")
                return yayin._statik(self, yol)

            def do_POST(self):
                """POST /komut: JSON gövdesi izin listesine karşı denetlenir; geçerliyse kuyruğa alınır."""
                if self.path.split("?", 1)[0] != "/komut":
                    return yayin._gonder(self, 404, b"")
                uzunluk = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    if not 0 < uzunluk <= 65536:
                        raise ValueError("boyut")
                    komut = json.loads(self.rfile.read(uzunluk))
                    if not isinstance(komut, dict) or komut.get("a") not in yayin.izinli_komutlar:
                        raise ValueError("izin listesinde yok")
                except Exception as hata:
                    return yayin._gonder(self, 400, str(hata).encode("utf-8"), "text/plain; charset=utf-8")
                yayin._komutlar.put(komut)
                return yayin._gonder(self, 204, b"")

        self._sunucu = _Sunucu(("127.0.0.1", self.port), Isleyici)
        self.port = self._sunucu.server_address[1]
        self._calisiyor = True
        threading.Thread(target=self._sunucu.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self.port}/"

    def durdur(self):
        """Sunucuyu ve bekleyen akış bağlantılarını kapatır."""
        self._calisiyor = False
        with self._kosul:
            self._kosul.notify_all()
        if self._sunucu:
            self._sunucu.shutdown()
            self._sunucu.server_close()

    # --- İstek işleyiciler ---

    @staticmethod
    def _gonder(istek, kod, veri, tur="application/octet-stream"):
        """Tek seferlik yanıt gönderir (önbellek kapalı: tarayıcı hep güncel veriyi alsın)."""
        istek.send_response(kod)
        if veri:
            istek.send_header("Content-Type", tur)
        istek.send_header("Content-Length", str(len(veri)))
        istek.send_header("Cache-Control", "no-store")
        istek.end_headers()
        if veri:
            istek.wfile.write(veri)

    def _statik(self, istek, yol):
        """Kök (ya da ek) klasörden dosya sunar. Klasör dışına çıkış girişimleri 404 döner."""
        # URL kodunu çöz ("resim%20adi.png"); kaçış denemeleri ("%2e%2e") aşağıdaki kontrolde yakalanır
        parcalar = [p for p in urllib.parse.unquote(yol).split("/") if p]
        kok = self.kok
        if parcalar and parcalar[0] in self.ek_klasorler:
            kok = self.ek_klasorler[parcalar[0]]
            parcalar = parcalar[1:]
        if kok is None:
            return self._gonder(istek, 404, b"")
        hedef = (kok / "/".join(parcalar or ["index.html"])).resolve()
        # Önce çözümle, sonra kök klasörün içinde mi kontrol et ("../" ile kaçış engellenir)
        if (kok != hedef and kok not in hedef.parents) or not hedef.is_file():
            return self._gonder(istek, 404, b"")
        tur = mimetypes.guess_type(hedef.name)[0] or "application/octet-stream"
        if tur.startswith("text/") or tur.endswith("javascript"):
            tur += "; charset=utf-8"
        return self._gonder(istek, 200, hedef.read_bytes(), tur)

    def _sse_baslik(self, istek):
        """SSE yanıtının başlıklarını yazar; bağlantı açık kalır."""
        istek.send_response(200)
        istek.send_header("Content-Type", "text/event-stream; charset=utf-8")
        istek.send_header("Cache-Control", "no-store")
        istek.send_header("Connection", "keep-alive")
        istek.end_headers()

    def _sse_durum(self, istek):
        """/durum: yeni durum gelince gönderir; yavaş istemci ara durumları kaçırır, hep en günceli alır."""
        self._sse_baslik(istek)
        son_no = -1
        try:
            while self._calisiyor:
                with self._kosul:
                    yeni = self._kosul.wait_for(lambda: self._durum_no != son_no or not self._calisiyor, KALP_ATISI)
                    veri, son_no = self._durum, self._durum_no
                istek.wfile.write(b"data: " + veri + b"\n\n" if yeni else b": kalp\n\n")
                istek.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def _sse_olaylar(self, istek, gecmis=False):
        """/olaylar: her istemcinin KENDİ kuyruğu vardır, böylece hiçbir olay kaçmaz ve kimse diğerini yavaşlatmaz."""
        self._sse_baslik(istek)
        kuyruk = queue.Queue()
        with self._kosul:
            if gecmis:
                for veri in self._son_olaylar:
                    kuyruk.put(veri)
            self._olay_kuyruklari.append(kuyruk)
        try:
            while self._calisiyor:
                try:
                    veri = kuyruk.get(timeout=KALP_ATISI)
                    istek.wfile.write(b"data: " + veri + b"\n\n")
                except queue.Empty:
                    istek.wfile.write(b": kalp\n\n")
                istek.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            with self._kosul:
                self._olay_kuyruklari.remove(kuyruk)

    def _mjpeg(self, istek):
        """/video.mjpg: yeni JPEG gelince sürekli gönderir. İzleyici sayılır (kodlama sadece izleyen varken yapılır)."""
        istek.send_response(200)
        istek.send_header("Content-Type", "multipart/x-mixed-replace; boundary=kare")
        istek.send_header("Cache-Control", "no-store")
        istek.end_headers()
        with self._kosul:
            self._video_istemcileri += 1
        son_no = -1
        try:
            while self._calisiyor:
                with self._kosul:
                    if not self._kosul.wait_for(lambda: self._jpeg_no != son_no or not self._calisiyor, 5.0):
                        continue
                    jpeg, son_no = self._jpeg, self._jpeg_no
                if jpeg is None:
                    continue
                istek.wfile.write(
                    b"--kare\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpeg)).encode()
                    + b"\r\n\r\n"
                    + jpeg
                    + b"\r\n"
                )
                istek.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            with self._kosul:
                self._video_istemcileri -= 1
