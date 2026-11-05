import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sunucu"))
import cekirdek as c


class Maske(unittest.TestCase):
    def test_tc_iban_telefon_eposta(self):
        m = c.maskele("TC 12345678901, IBAN TR12 0006 1005 1978 6457 8413 26, tel 0532 123 45 67, a.b@ornek.com")
        self.assertNotIn("12345678901", m)
        self.assertNotIn("8413", m)
        self.assertNotIn("532", m)
        self.assertNotIn("@", m)
        for k in ("[TC no]", "[IBAN]", "[telefon]", "[e-posta]"):
            self.assertIn(k, m)

    def test_tarih_ve_tutar_maskelenmez(self):
        s = "15.03.2026 tarihine kadar 1.250,50 TL ödenmelidir. 7201 sayılı Kanun"
        self.assertEqual(c.maskele(s), s)


class Denetim(unittest.TestCase):
    ASIL = "Borcunuz 1.250,50 TL olup tebliğden itibaren 30 gün içinde 7201 sayılı Kanun uyarınca ödenmelidir."

    def test_kaynakta_olan_sayilar_temiz(self):
        s = {"ozet": "30 gün içinde 1.250,50 TL ödemeniz gerekiyor.", "sade": "7201 sayılı Kanun", "yapilacaklar": [{"ne": "Öde", "ne_zaman": "30 gün içinde"}]}
        self.assertEqual(c.denetle(self.ASIL, s), [])

    def test_uydurma_sure_yakalanir(self):
        s = {"ozet": "15 gün içinde ödemeniz gerekiyor.", "sade": "", "yapilacaklar": []}
        self.assertEqual(c.denetle(self.ASIL, s), ["15"])

    def test_ayrac_farki_sorun_degil(self):
        s = {"ozet": "1250,50 TL", "sade": "", "yapilacaklar": []}
        self.assertEqual(c.denetle(self.ASIL, s), [])


if __name__ == "__main__":
    unittest.main()
