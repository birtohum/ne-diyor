"""Ne Diyor? herkese açık API: POST /api/sadelestir {"metin": "..."}.
Caddy önde HTTPS'i yapar, /ne-diyor/* isteklerini 127.0.0.1:8791'e iletir.

Sınırlar (ortam değişkeniyle):
  NEDIYOR_IP_GUN  bir IP'nin günlük istek sayısı   (10)
  NEDIYOR_GUN     tüm ziyaretçiler, günlük        (100)
  NEDIYOR_TAVAN   toplam model harcaması, $        (5)
Metinler kaydedilmez; IP'nin kısaltılmış özeti yalnızca gün içinde bellekte sayılır.
"""
import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cekirdek

PORT = int(os.environ.get("NEDIYOR_PORT", "8791"))
IP_GUN = int(os.environ.get("NEDIYOR_IP_GUN", "10"))
GUN = int(os.environ.get("NEDIYOR_GUN", "100"))
IZINLI = {"https://birtohum.github.io", "http://127.0.0.1:8879"}
TR = timezone(timedelta(hours=3))
_kilit = threading.Lock()
_sayac = {"gun": None, "toplam": 0, "ip": {}}


def _bugun():
    return datetime.now(TR).date().isoformat()


def _hak_al(ozet):
    with _kilit:
        if _sayac["gun"] != _bugun():
            _sayac.update({"gun": _bugun(), "toplam": 0, "ip": {}})
        kisi = _sayac["ip"].get(ozet, 0)
        if kisi >= IP_GUN:
            return f"Bugünlük hakkınız doldu ({IP_GUN} metin). Yarın yeniden deneyebilirsiniz."
        if _sayac["toplam"] >= GUN:
            return "Servis bugünkü sınırına ulaştı. Yarın yeniden deneyebilirsiniz."
        _sayac["ip"][ozet] = kisi + 1
        _sayac["toplam"] += 1
        return None


def _iade(ozet):
    with _kilit:
        if _sayac["ip"].get(ozet):
            _sayac["ip"][ozet] -= 1
            _sayac["toplam"] -= 1


class Isleyici(BaseHTTPRequestHandler):
    server_version = "ne-diyor"

    def log_message(self, *a):  # metin ya da IP günlüğe yazılmaz
        pass

    def _cors(self):
        koken = self.headers.get("Origin", "")
        if koken in IZINLI or koken.startswith("chrome-extension://"):
            self.send_header("Access-Control-Allow-Origin", koken)
            self.send_header("Vary", "Origin")

    def _gonder(self, kod, veri):
        govde = json.dumps(veri, ensure_ascii=False).encode()
        self.send_response(kod)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(govde)

    def _ozet(self):
        ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
        return hashlib.sha256(("ne-diyor:" + ip).encode()).hexdigest()[:16]

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/durum"):
            with _kilit:
                kisi = _sayac["ip"].get(self._ozet(), 0) if _sayac["gun"] == _bugun() else 0
            return self._gonder(200, {"kalan": max(0, IP_GUN - kisi), "en_uzun": cekirdek.EN_UZUN,
                                      "butce_dolu": cekirdek.harcanan() >= cekirdek.TAVAN})
        return self._gonder(404, {"hata": "bulunamadı"})

    def do_POST(self):
        if self.path != "/api/sadelestir":
            return self._gonder(404, {"hata": "bulunamadı"})
        uzunluk = int(self.headers.get("Content-Length", 0) or 0)
        if uzunluk > 40000:
            return self._gonder(413, {"hata": "Metin çok uzun."})
        try:
            metin = str(json.loads(self.rfile.read(uzunluk)).get("metin", "")).strip()
        except (ValueError, AttributeError):
            return self._gonder(400, {"hata": "İstek okunamadı."})
        if len(metin) < 40:
            return self._gonder(400, {"hata": "Biraz daha uzun bir metin yapıştırın (en az bir cümle)."})
        if cekirdek.harcanan() >= cekirdek.TAVAN:
            return self._gonder(503, {"hata": "Servisin bütçesi doldu. Kod açık; kendi anahtarınızla çalıştırabilirsiniz."})
        ozet = self._ozet()
        neden = _hak_al(ozet)
        if neden:
            return self._gonder(429, {"hata": neden})
        try:
            sonuc = cekirdek.sadelestir(metin)
        except Exception:  # noqa: BLE001  (ayrıntı kullanıcıya gösterilmez)
            _iade(ozet)
            return self._gonder(502, {"hata": "Model şu an cevap vermedi. Biraz sonra yeniden deneyin."})
        sonuc["kirpildi"] = len(metin) > cekirdek.EN_UZUN
        return self._gonder(200, sonuc)


if __name__ == "__main__":
    print(f"ne-diyor: 127.0.0.1:{PORT} (IP/gün {IP_GUN}, gün {GUN}, tavan {cekirdek.TAVAN} $)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Isleyici).serve_forever()
