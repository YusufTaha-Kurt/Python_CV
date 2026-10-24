import json

from goru.olaylar import JsonlKaydedici, OlayYolu


def test_abone_ve_joker():
    yol = OlayYolu()
    belirli, hepsi = [], []
    yol.abone_ol("jest.degisti", belirli.append)
    yol.abone_ol(OlayYolu.HEPSI, hepsi.append)

    yol.yayinla("jest.degisti", el="sag", jest="yumruk")
    yol.yayinla("el.kayboldu", el="sag")

    assert [o.veri["jest"] for o in belirli] == ["yumruk"]
    assert [o.ad for o in hepsi] == ["jest.degisti", "el.kayboldu"]


def test_hatali_abone_digerlerini_engellemez():
    yol = OlayYolu()
    alinan = []

    def bozuk(_):
        raise ValueError("bozuk abone")

    yol.abone_ol("x", bozuk)
    yol.abone_ol("x", alinan.append)
    yol.yayinla("x")
    assert len(alinan) == 1


def test_jsonl_kaydedici(tmp_path):
    dosya = tmp_path / "olaylar.jsonl"
    kaydedici = JsonlKaydedici(dosya)
    yol = OlayYolu()
    yol.abone_ol(OlayYolu.HEPSI, kaydedici)
    yol.yayinla("jest.kaydirma", el="sol", yon="sag")
    yol.yayinla("jest.degisti", el="sag", jest="avuc")
    kaydedici.kapat()

    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines()]
    assert [s["ad"] for s in satirlar] == ["jest.kaydirma", "jest.degisti"]
    assert satirlar[0]["veri"] == {"el": "sol", "yon": "sag"}
