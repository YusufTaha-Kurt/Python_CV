import http.client
import json
import time

import pytest

from goru.web import CanliYayin


@pytest.fixture
def yayin(tmp_path):
    kok = tmp_path / "kok"
    kok.mkdir()
    (kok / "index.html").write_text("<h1>merhaba</h1>", encoding="utf-8")
    (tmp_path / "gizli.txt").write_text("sir", encoding="utf-8")
    icerik = tmp_path / "icerik"
    icerik.mkdir()
    (icerik / "not.md").write_text("# not", encoding="utf-8")
    (icerik / "bosluklu ad.md").write_text("bosluk", encoding="utf-8")
    y = CanliYayin(kok, port=0, ek_klasorler={"icerik": icerik}, izinli_komutlar={"toparla"})
    y.baslat()
    yield y
    y.durdur()


def istek(yayin, yontem, yol, govde=None):
    baglanti = http.client.HTTPConnection("127.0.0.1", yayin.port, timeout=5)
    baglanti.request(yontem, yol, body=govde)
    yanit = baglanti.getresponse()
    return yanit.status, yanit.read()


def test_statik_dosyalar(yayin):
    assert istek(yayin, "GET", "/") == (200, b"<h1>merhaba</h1>")
    assert istek(yayin, "GET", "/icerik/not.md") == (200, b"# not")
    assert istek(yayin, "GET", "/icerik/bosluklu%20ad.md") == (200, b"bosluk")


@pytest.mark.parametrize("yol", ["/../gizli.txt", "/icerik/../../gizli.txt", "/%2e%2e/gizli.txt", "/yok.html"])
def test_klasor_disina_cikilamaz(yayin, yol):
    assert istek(yayin, "GET", yol)[0] == 404


def test_komut_izin_listesi(yayin):
    assert istek(yayin, "POST", "/komut", json.dumps({"a": "toparla"}))[0] == 204
    assert istek(yayin, "POST", "/komut", json.dumps({"a": "dosya_sil"}))[0] == 400
    assert istek(yayin, "POST", "/komut", "json degil")[0] == 400
    assert yayin.komutlari_al() == [{"a": "toparla"}]
    assert yayin.komutlari_al() == []


def _sse_oku(yayin, yol, adet):
    baglanti = http.client.HTTPConnection("127.0.0.1", yayin.port, timeout=5)
    baglanti.request("GET", yol)
    yanit = baglanti.getresponse()
    assert yanit.getheader("Content-Type").startswith("text/event-stream")
    return yanit


def _sonraki_veri(yanit):
    while True:
        satir = yanit.readline().decode("utf-8").strip()
        if satir.startswith("data: "):
            return json.loads(satir[6:])


def test_durum_akisi_en_son_durumu_verir(yayin):
    yayin.durum_yayinla({"n": 1})
    yanit = _sse_oku(yayin, "/durum", 1)
    assert _sonraki_veri(yanit) == {"n": 1}
    yayin.durum_yayinla({"n": 2})
    assert _sonraki_veri(yanit) == {"n": 2}
    assert json.loads(istek(yayin, "GET", "/durum.json")[1]) == {"n": 2}


def test_olay_akisi_hepsini_sirayla_verir(yayin):
    yanit = _sse_oku(yayin, "/olaylar", 3)
    time.sleep(0.2)  # İstemci kuyruğu oluşsun
    for i in range(3):
        yayin.olay_yayinla({"ad": "x", "i": i})
    assert [_sonraki_veri(yanit)["i"] for _ in range(3)] == [0, 1, 2]


def test_video_izleyen_yoksa_kodlamaz(yayin):
    assert not yayin.video_izleniyor
    yayin.kare_yayinla(object())  # İzleyen yokken kare hiç dokunulmadan atlanır
