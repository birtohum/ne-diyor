// Seçili metni oturum deposuna koyup sonuç sayfasını açar. Metin hiçbir yerde kalıcı saklanmaz.
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({id: "ne-diyor", title: "Ne diyor? (sade Türkçe)", contexts: ["selection"]});
});
chrome.contextMenus.onClicked.addListener(async (bilgi) => {
  if (bilgi.menuItemId !== "ne-diyor") return;
  await chrome.storage.session.set({metin: (bilgi.selectionText || "").slice(0, 6000)});
  chrome.tabs.create({url: chrome.runtime.getURL("sonuc.html")});
});
chrome.action.onClicked.addListener(async () => {
  await chrome.storage.session.remove("metin");
  chrome.tabs.create({url: chrome.runtime.getURL("sonuc.html")});
});
