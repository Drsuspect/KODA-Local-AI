// KODAAI public voice-first UI example.
// Production hosts, telemetry details and private runtime configuration are intentionally omitted.

const API_BASE = window.KODAAI_API_BASE || "http://127.0.0.1:8080";
const scopeBtn = document.getElementById("scopeBtn");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let recognitionActive = false;
let controller = null;
let utterance = null;

const scopeFullText =
  "KODAAI Lokal AI şu anda Beta / Ar-Ge sürümündedir. " +
  "Geliştirme ve doğrulama çalışmaları devam eden, lokal çalışan ve belgeye dayalı soru-cevap üreten deneysel bir yapay zekâ sistemidir. " +
  "Mevcut bilgi kapsamı, EKPSS lisans eğitim düzeyine yönelik Türkçe, Coğrafya, Matematik, Tarih ve Vatandaşlık derslerinden oluşmaktadır. " +
  "KODAAI Lokal AI; ders anlatımı, alıştırma, test ve deneme sınavı içeriklerinden oluşturulan kendi bilgi deposunu kullanarak kullanıcı sorularına öncelikle bu kaynaklara dayalı ve kontrollü yanıtlar üretir. " +
  "Yapay zekâ uygulamayı yönetmez. Eğitim ve uygulama akışının kontrolü yapay zekâya bırakılmaz; sistemin temel işleyişi deterministik KODAAI yapısı tarafından yönetilir. " +
  "Beta / Ar-Ge süreci devam ettiği için yanıtlar eksik veya hatalı olabilir. Özellikle mevcut bilgi kapsamı dışında kalan sorularda doğru yanıt garanti edilmez.";

function active() {
  return recognitionActive || Boolean(controller) || Boolean(utterance);
}

function showStop(show) {
  stopBtn.hidden = !show;
}

function stopActive() {
  if (recognitionActive && recognition) {
    recognitionActive = false;
    try { recognition.abort(); } catch (_) {}
  }
  if (controller) {
    controller.abort();
    controller = null;
  }
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  utterance = null;
  showStop(false);
  statusEl.textContent = "Durduruldu.";
}

function speak(text, rate = 1.0) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "tr-TR";
  utterance.rate = rate;
  utterance.onend = () => {
    utterance = null;
    showStop(false);
    statusEl.textContent = "Hazır";
  };
  showStop(true);
  window.speechSynthesis.speak(utterance);
}

async function askKoda(question) {
  if (active()) stopActive();
  controller = new AbortController();
  transcriptEl.value = "SORU:\n" + question + "\n\nKODAAI:\n";
  statusEl.textContent = "KODAAI düşünüyor...";
  showStop(true);

  try {
    const response = await fetch(API_BASE + "/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ question, user_role: "research" })
    });
    if (!response.ok) throw new Error("API response error");
    const data = await response.json();
    controller = null;
    transcriptEl.value = "SORU:\n" + question + "\n\nKODAAI:\n" + data.answer;
    statusEl.textContent = "Yanıt alındı.";
    speak(data.answer_speech || data.answer);
  } catch (error) {
    controller = null;
    if (error.name === "AbortError") return;
    showStop(false);
    statusEl.textContent = "Yanıt alınamadı.";
  }
}

scopeBtn.addEventListener("click", () => {
  if (active()) stopActive();
  transcriptEl.value = "KODAAI BİLGİ KAPSAMI:\n\n" + scopeFullText;
  statusEl.textContent = "KODAAI bilgi kapsamı okunuyor.";
  speak(scopeFullText, 1.12);
});

stopBtn.addEventListener("click", stopActive);

if (!SpeechRecognition) {
  startBtn.disabled = true;
  statusEl.textContent = "Bu tarayıcı ses tanımayı desteklemiyor.";
} else {
  recognition = new SpeechRecognition();
  recognition.lang = "tr-TR";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    recognitionActive = true;
    statusEl.textContent = "Dinleniyor...";
    showStop(true);
  };
  recognition.onresult = (event) => {
    recognitionActive = false;
    askKoda(event.results[0][0].transcript);
  };
  recognition.onend = () => {
    recognitionActive = false;
    if (!controller && !utterance) showStop(false);
  };
  recognition.onerror = () => {
    recognitionActive = false;
    showStop(false);
    statusEl.textContent = "Ses tanıma hatası.";
  };
  startBtn.addEventListener("click", () => {
    if (active()) stopActive();
    recognition.start();
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.repeat && active()) {
    const tag = event.target && event.target.tagName;
    if (tag === "INPUT" || tag === "SELECT" || (tag === "TEXTAREA" && !event.target.readOnly)) return;
    event.preventDefault();
    stopActive();
  }
});

window.addEventListener("DOMContentLoaded", () => {
  showStop(false);
  scopeBtn.focus();
});
