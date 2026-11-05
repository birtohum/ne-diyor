
"use strict";
const API = "https://51-20-66-93.sslip.io/ne-diyor";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

function maskele(m) {
  return m.replace(/\bTR\s?\d{2}(?:\s?\d{4}){5}\s?\d{2}\b/gi, "[IBAN]")
    .replace(/(?<!\d)[1-9]\d{10}(?!\d)/g, "[TC no]")
    .replace(/(?<!\d)(?:\+?90[\s-]?)?0?\(?5\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)/g, "[telefon]")
    .replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, "[e-posta]");
}
function sayac() { $("#sayac").textContent = `${$("#metin").value.length.toLocaleString("tr-TR")} / 6.000`; }
$("#metin").addEventListener("input", sayac);

function ciz(r) {
  let h = "";
  if (r.supheli_sayilar && r.supheli_sayilar.length)
    h += `<p class="uyari"><b>Dikkat:</b> Sade metinde asıl yazıda geçmeyen sayı(lar) var: ${r.supheli_sayilar.map(esc).join(", ")}. Bu tarih, süre ya da tutarı asıl yazıdan kontrol et.</p>`;
  h += `<p class="ozet"><mark>${esc(r.ozet)}</mark></p>`;
  if (r.yapilacaklar && r.yapilacaklar.length)
    h += `<h3>Senden istenen</h3><ul class="yap">${r.yapilacaklar.map((y) => `<li><div>${esc(y.ne || "")}${y.ne_zaman ? `<br><span class="zaman">${esc(y.ne_zaman)}</span>` : ""}</div></li>`).join("")}</ul>`;
  if (r.sade) h += `<h3>Sade hâli</h3><div class="sade">${r.sade.split(/\n{2,}/).map((p) => `<p>${esc(p)}</p>`).join("")}</div>`;
  if (r.terimler && r.terimler.length) h += `<h3>Zor kelimeler</h3><dl class="terim">${r.terimler.map((t) => `<dt>${esc(t.terim)}</dt><dd>${esc(t.anlam)}</dd>`).join("")}</dl>`;
  if (r.supheli_sayilar && !r.supheli_sayilar.length) h += `<p class="temiz">Sade metindeki bütün sayılar asıl yazıda da geçiyor.</p>`;
  if (r.maskelendi) h += `<p class="kucuk" style="margin-top:10px">Kişisel numaralar gönderilmeden önce gizlendi.</p>`;
  if (r.kirpildi) h += `<p class="kucuk">Yazı uzun olduğu için ilk 6.000 karakteri işlendi.</p>`;
  $("#sonuc").innerHTML = h;
}

$("#cevir").onclick = async () => {
  const ham = $("#metin").value.trim(), metin = maskele(ham);
  if (metin.length < 40) { $("#sonuc").innerHTML = `<p class="bos">Biraz daha uzun bir metin yapıştır (en az bir cümle).</p>`; return; }
  $("#cevir").disabled = true; $("#sure").textContent = "";
  $("#sonuc").innerHTML = `<div class="bekle"><i></i> Okunuyor… genellikle 15–25 saniye sürüyor.</div>`;
  const t = performance.now();
  try {
    const c = await fetch(API + "/api/sadelestir", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({metin})});
    const r = await c.json();
    if (!c.ok) throw new Error(r.hata || "Bir sorun oldu.");
    r.maskelendi = r.maskelendi || metin !== ham; ciz(r); $("#sure").textContent = `${((performance.now() - t) / 1000).toFixed(0)} sn`;
  } catch (e) {
    $("#sonuc").innerHTML = `<p class="uyari">${esc(e.message === "Failed to fetch" ? "Sunucuya ulaşılamadı. Biraz sonra yeniden dene." : e.message)}</p>`;
  } finally { $("#cevir").disabled = false; durum(); }
};

async function durum() {
  try { const d = await (await fetch(API + "/durum")).json();
    $("#kalan").textContent = d.butce_dolu ? "Servisin bütçesi doldu." : `Bugün ${d.kalan} hakkın kaldı.`; } catch (e) { $("#kalan").textContent = ""; }
}
chrome.storage.session.get("metin").then(({metin}) => {
  if (metin) { $("#metin").value = metin; sayac(); $("#cevir").click(); } else { sayac(); $("#metin").focus(); }
});
durum();
