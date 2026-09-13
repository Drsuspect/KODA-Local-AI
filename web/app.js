// KODAAI Lokal AI public voice-first UI.
// Existing /api/chat, SpeechRecognition, TTS, stop and Enter behavior preserved.

const CHAT_ENDPOINT = "/api/chat";

const scopeBtn = document.getElementById("scopeBtn");
const scopeNavBtn = document.getElementById("scopeNavBtn");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");
const questionCard = document.getElementById("questionCard");
const answerCard = document.getElementById("answerCard");
const questionText = document.getElementById("questionText");
const answerText = document.getElementById("answerText");
const writeBtn = document.getElementById("writeBtn");
const textAskForm = document.getElementById("textAskForm");
const questionInput = document.getElementById("questionInput");
const listenAnswerBtn = document.getElementById("listenAnswerBtn");
const copyAnswerBtn = document.getElementById("copyAnswerBtn");
const infoDialog = document.getElementById("infoDialog");
const dialogTitle = document.getElementById("dialogTitle");
const dialogBody = document.getElementById("dialogBody");
const dialogClose = document.getElementById("dialogClose");
const scopeDisplay = document.getElementById("scopeDisplay");
const scopeDisplayText = document.getElementById("scopeDisplayText");

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let recognitionActive = false;
let controller = null;
let utterance = null;
let ekpssAudio = null;
let lastAnswer = "";
let lastAnswerSpeech = "";

const scopeFullText =
  "KODAAI Lokal AI şu anda Beta / Ar-Ge sürümündedir. " +
  "Geliştirme ve doğrulama çalışmaları devam eden, lokal çalışan ve belgeye dayalı soru-cevap üreten deneysel bir yapay zekâ sistemidir. " +
  "Mevcut bilgi kapsamı, EKPSS lisans eğitim düzeyine yönelik Türkçe, Coğrafya, Matematik, Tarih ve Vatandaşlık derslerinden oluşmaktadır. " +
  "KODAAI Lokal AI; ders anlatımı, alıştırma, test ve deneme sınavı içeriklerinden oluşturulan kendi bilgi deposunu kullanarak kullanıcı sorularına öncelikle bu kaynaklara dayalı ve kontrollü yanıtlar üretir. " +
  "Yapay zekâ uygulamayı yönetmez. Eğitim ve uygulama akışının kontrolü yapay zekâya bırakılmaz; sistemin temel işleyişi deterministik KODAAI yapısı tarafından yönetilir. " +
  "Beta / Ar-Ge süreci devam ettiği için yanıtlar eksik veya hatalı olabilir. Özellikle mevcut bilgi kapsamı dışında kalan sorularda doğru yanıt garanti edilmez.";

function active() {
  return recognitionActive || Boolean(controller) || Boolean(utterance) || Boolean(ekpssAudio);
}

function setUiState(state, text) {
  document.body.classList.remove("is-listening", "is-thinking", "is-error");
  if (state) document.body.classList.add("is-" + state);
  statusEl.textContent = text;
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

  if (ekpssAudio) {
    try {
      ekpssAudio.pause();
      ekpssAudio.currentTime = 0;
    } catch (_) {}
    ekpssAudio = null;
  }
  utterance = null;
  showStop(false);
  setUiState("", "Durduruldu.");
}

function speak(text, rate = 1.0) {
  if (!("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  utterance = new SpeechSynthesisUtterance(String(text).replace(/\bEKPSS\b/gi, "eğkape sese"));
  utterance.lang = "tr-TR";
  utterance.rate = rate;
  utterance.onend = () => {
    utterance = null;
    showStop(false);
    setUiState("", "Hazır");
  };
  utterance.onerror = () => {
    utterance = null;
    showStop(false);
    setUiState("error", "Seslendirme hatası.");
  };
  showStop(true);
  window.speechSynthesis.speak(utterance);
}

function renderQuestion(question) {
  questionText.textContent = question;
  questionCard.hidden = false;
  answerCard.hidden = true;
}

function renderAnswer(answer) {
  answerText.textContent = answer;
  answerCard.hidden = false;
}

async function askKoda(question) {

  if (scopeDisplay) {
    scopeDisplay.hidden = true;
  }
  question = (question || "").trim();
  if (!question) return;

  if (active()) stopActive();
  controller = new AbortController();

  renderQuestion(question);
  transcriptEl.value = "SORU:\\n" + question + "\\n\\nKODAAI:\\n";
  setUiState("thinking", "KODAAI düşünüyor...");
  showStop(true);

  try {
    const response = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({ question, user_role: "research" })
    });

    if (!response.ok) throw new Error("API response error");

    const data = await response.json();
    controller = null;

    lastAnswer = data.answer || "";
    lastAnswerSpeech = data.answer_speech || lastAnswer;

    transcriptEl.value = "SORU:\\n" + question + "\\n\\nKODAAI:\\n" + lastAnswer;
    renderAnswer(lastAnswer);
    setUiState("", "Yanıt alındı.");
    speak(lastAnswerSpeech);
  } catch (error) {
    controller = null;
    if (error.name === "AbortError") return;
    showStop(false);
    setUiState("error", "Yanıt alınamadı.");
  }
}


function speakScopeWithEkpss() {
  if (!("speechSynthesis" in window)) return;

  window.speechSynthesis.cancel();

  const marker = "EKPSS";
  const parts = scopeFullText.split(marker);

  if (parts.length !== 2) {
    speak(scopeFullText, 1.12);
    return;
  }

  const beforeText = parts[0];
  const afterText = parts[1];

  const before = new SpeechSynthesisUtterance(beforeText);
  before.lang = "tr-TR";
  before.rate = 1.12;

  utterance = before;
  showStop(true);

  before.onend = () => {
    utterance = null;

    ekpssAudio = new Audio("/static/audio/ekpss_telaffuz.mp3");

    ekpssAudio.onended = () => {
      ekpssAudio = null;

      const after = new SpeechSynthesisUtterance(afterText);
      after.lang = "tr-TR";
      after.rate = 1.12;

      utterance = after;

      after.onend = () => {
        utterance = null;
        showStop(false);
        setUiState("", "Hazır");
      };

      window.speechSynthesis.speak(after);
    };

    ekpssAudio.onerror = () => {
      ekpssAudio = null;
      showStop(false);
      setUiState("error", "EKPSS ses dosyası oynatılamadı.");
    };

    ekpssAudio.play().catch(() => {
      ekpssAudio = null;
      showStop(false);
      setUiState("error", "EKPSS ses dosyası başlatılamadı.");
    });
  };

  window.speechSynthesis.speak(before);
}
function showScope() {
  if (active()) stopActive();
  transcriptEl.value = "KODAAI BİLGİ KAPSAMI:\n\n" + scopeFullText;

  if (scopeDisplay && scopeDisplayText) {
    scopeDisplayText.textContent = scopeFullText;
    scopeDisplay.hidden = false;

    scopeDisplay.scrollIntoView({
      behavior: "smooth",
      block: "nearest"
    });
  }
  dialogTitle.textContent = "Neleri sorabilirim?";
  dialogBody.innerHTML =
    "<p>Mevcut bilgi kapsamı: <strong>Türkçe, Coğrafya, Matematik, Tarih ve Vatandaşlık</strong>.</p>" +
    "<p>KODAAI Lokal AI yanıtlarını öncelikle kendi belge deposuna dayalı ve kontrollü biçimde üretir.</p>";
  if (infoDialog && typeof infoDialog.showModal === "function") infoDialog.showModal();
  setUiState("", "KODAAI bilgi kapsamı okunuyor.");
  speak(scopeFullText, 1.12);
}

scopeBtn.addEventListener("click", showScope);
scopeNavBtn.addEventListener("click", showScope);
stopBtn.addEventListener("click", stopActive);

writeBtn.addEventListener("click", () => {
  questionInput.focus();
  questionInput.scrollIntoView({ behavior: "smooth", block: "center" });
});

textAskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value;
  questionInput.value = "";
  askKoda(question);
});

listenAnswerBtn.addEventListener("click", () => speak(lastAnswerSpeech || lastAnswer));

copyAnswerBtn.addEventListener("click", async () => {
  if (!lastAnswer) return;
  try {
    await navigator.clipboard.writeText(lastAnswer);
    copyAnswerBtn.textContent = "✓ Kopyalandı";
    setTimeout(() => { copyAnswerBtn.textContent = "⧉ Kopyala"; }, 1200);
  } catch (_) {
    setUiState("error", "Kopyalama başarısız.");
  }
});

dialogClose.addEventListener("click", () => infoDialog.close());

const infoButtons = {
  sourcesNavBtn: ["Kaynaklar", "Kaynak ayrıntıları sonraki aşamada API kaynak verisine bağlanacaktır."],
  historyNavBtn: ["Geçmiş", "Sohbet geçmişi bu araştırma arayüzünde henüz etkin değildir."],
  settingsNavBtn: ["Ayarlar", "Dil, ses ve görünüm seçenekleri bu bölümde geliştirilecektir."],
  aboutNavBtn: ["KODAAI Hakkında", "KODAAI; erişilebilir teknoloji, yerel yapay zekâ ve kontrollü belge destekli bilgi erişimi üzerine geliştirilen bir Ar-Ge çalışmasıdır."]
};

Object.entries(infoButtons).forEach(([id, content]) => {
  const btn = document.getElementById(id);
  if (!btn) return;
  btn.addEventListener("click", () => {
    dialogTitle.textContent = content[0];
    dialogBody.textContent = content[1];
    infoDialog.showModal();
  });
});

if (!SpeechRecognition) {
  startBtn.disabled = true;
  setUiState("error", "Bu tarayıcı ses tanımayı desteklemiyor.");
} else {
  recognition = new SpeechRecognition();
  recognition.lang = "tr-TR";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    recognitionActive = true;
    setUiState("listening", "Dinleniyor...");
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
    setUiState("error", "Ses tanıma hatası.");
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
