"""Ne Diyor? çekirdeği: resmî yazıyı sade Türkçeye çevirir ve çıktıyı asıl metne karşı denetler.

Model uydurursa en tehlikeli yer tarih, süre ve tutardır. Bu yüzden çıktıdaki her sayı (tarih, gün, tutar,
madde no) asıl metinde de geçiyor mu diye kodla bakılır; geçmeyenler kullanıcıya işaretlenir.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://api.meta.ai/v1/chat/completions"
# Kişisel veri içerebilecek metinler için veri paylaşımsız katman (contributor DEĞİL).
MODEL = os.environ.get("NEDIYOR_MODEL", "muse-spark-1.3")
FIYAT = {"muse-spark-1.3": (1.25, 4.25), "muse-spark-1.3-contributor": (0.10, 0.20)}  # $ / 1M token
TAVAN = float(os.environ.get("NEDIYOR_TAVAN", "5"))
SAYAC = Path(os.environ.get("NEDIYOR_KAYIT", Path(__file__).parent / "kayitlar")) / "butce.jsonl"
EN_UZUN = 6000
_kilit = threading.Lock()

ISTEM = """Sen resmî yazıları herkesin anlayacağı sade Türkçeye çeviren bir yardımcısın.
Aşağıdaki metin bir resmî yazı, tebligat, sözleşme maddesi, mevzuat ya da kurum duyurusu olabilir.

Kurallar:
- Yalnızca metinde yazanı kullan. Metinde olmayan bir tarih, süre, tutar, kurum ya da yükümlülük EKLEME.
- Tarihleri, süreleri, tutarları ve madde numaralarını metindeki rakamlarla AYNEN yaz.
- Hukuki tavsiye verme; "itiraz etmelisiniz" gibi yönlendirme yapma, metin ne diyorsa onu söyle.
- Kısa cümleler, günlük kelimeler. "Tebliğ", "müracaat", "ihtar" gibi kelimelerin yerine "bildirim", "başvuru", "uyarı" de.
- Metinde [TC no], [IBAN], [telefon], [e-posta] gibi maskeli yerler varsa onları olduğu gibi bırak.
- Metin resmî bir yazı değilse ya da anlamsızsa "ozet" alanına bunu yaz, diğerlerini boş bırak.

Yalnızca şu JSON'u döndür:
{"ozet": "tek cümlede bu yazı ne diyor",
 "yapilacaklar": [{"ne": "okuyanın yapması gereken ya da yapabileceği şey", "ne_zaman": "metinde süre/tarih varsa aynen, yoksa boş"}],
 "sade": "metnin tamamının sade Türkçe hâli, paragraflar \\n\\n ile ayrılmış",
 "terimler": [{"terim": "metindeki zor kelime", "anlam": "kısa açıklama"}]}

METİN:
"""

TC = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
IBAN = re.compile(r"\bTR\s?\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.I)
TELEFON = re.compile(r"(?<!\d)(?:\+?90[\s-]?)?0?\(?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")
EPOSTA = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def maskele(metin):
    """Kişisel numaralar modele gitmeden önce gizlenir."""
    metin = IBAN.sub("[IBAN]", metin)
    metin = TC.sub("[TC no]", metin)
    metin = TELEFON.sub("[telefon]", metin)
    return EPOSTA.sub("[e-posta]", metin)


def _anahtar():
    if os.environ.get("META_MODEL_API_KEY"):
        return os.environ["META_MODEL_API_KEY"]
    for satir in open(Path.home() / ".pflow-anahtarlar.env", encoding="utf-8"):
        if satir.startswith("META_MODEL_API_KEY="):
            return satir.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("META_MODEL_API_KEY bulunamadı")


def harcanan():
    if not SAYAC.exists():
        return 0.0
    return sum(json.loads(s)["usd"] for s in SAYAC.read_text(encoding="utf-8").splitlines() if s)


def _sor(icerik):
    govde = {"model": MODEL, "max_tokens": 6000, "messages": [{"role": "user", "content": icerik}],
             "response_format": {"type": "json_object"}}
    istek = urllib.request.Request(URL, data=json.dumps(govde).encode(), headers={
        "Authorization": "Bearer " + _anahtar(), "Content-Type": "application/json"})
    for deneme in range(3):
        try:
            with urllib.request.urlopen(istek, timeout=120) as r:
                j = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and deneme < 2:
                time.sleep(4 * (deneme + 1))
                continue
            raise RuntimeError(f"model hatası {e.code}")
        except (urllib.error.URLError, TimeoutError):
            if deneme == 2:
                raise RuntimeError("modele ulaşılamadı")
            time.sleep(4 * (deneme + 1))
    u = j.get("usage", {})
    gir, cik = FIYAT.get(MODEL, (1.25, 4.25))
    usd = (u.get("prompt_tokens", 0) * gir + u.get("completion_tokens", 0) * cik) / 1e6
    with _kilit:
        SAYAC.parent.mkdir(parents=True, exist_ok=True)
        with open(SAYAC, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": int(time.time()), "gir": u.get("prompt_tokens"),
                                "cik": u.get("completion_tokens"), "usd": round(usd, 6)}) + "\n")
    return j["choices"][0]["message"]["content"] or ""


def _json(s):
    s = re.sub(r"^```(json)?|```$", "", s.strip(), flags=re.M).strip()
    return json.loads(s[s.find("{"): s.rfind("}") + 1])


SAYI = re.compile(r"\d+(?:[.,]\d+)*")


def _sayilar(s):
    """'1.250,50' ve '1250,5' aynı sayılsın diye ayraçsız biçime indirger."""
    out = set()
    for m in SAYI.findall(s):
        out.add(m)
        out.add(re.sub(r"[.,]", "", m))
    return out


def denetle(asil, sonuc):
    """Çıktıda geçip asıl metinde geçmeyen sayıları döndürür (tarih, süre, tutar uydurma işareti)."""
    kaynak = _sayilar(asil)
    parcalar = [sonuc.get("ozet", ""), sonuc.get("sade", "")]
    for y in sonuc.get("yapilacaklar", []):
        parcalar += [y.get("ne", ""), y.get("ne_zaman", "")]
    supheli = []
    for m in SAYI.findall(" ".join(parcalar)):
        if m not in kaynak and re.sub(r"[.,]", "", m) not in kaynak and m not in supheli:
            supheli.append(m)
    return supheli


def sadelestir(metin):
    metin = metin.strip()[:EN_UZUN]
    gizli = maskele(metin)
    if harcanan() >= TAVAN:
        raise RuntimeError("bütçe doldu")
    sonuc = _json(_sor(ISTEM + gizli))
    sonuc = {"ozet": str(sonuc.get("ozet", "")), "sade": str(sonuc.get("sade", "")),
             "yapilacaklar": [y for y in sonuc.get("yapilacaklar", []) if isinstance(y, dict)][:10],
             "terimler": [t for t in sonuc.get("terimler", []) if isinstance(t, dict)][:15]}
    sonuc["supheli_sayilar"] = denetle(gizli, sonuc)
    sonuc["maskelendi"] = gizli != metin
    return sonuc
