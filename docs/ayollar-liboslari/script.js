/* ═══════════════════════════════════════
   FAQ ACCORDION
═══════════════════════════════════════ */
function toggleFaq(btn) {
  const answer = btn.nextElementSibling;
  const isOpen = btn.classList.contains('open');

  document.querySelectorAll('.faq-q').forEach(b => {
    b.classList.remove('open');
    b.nextElementSibling.classList.remove('show');
  });

  if (!isOpen) {
    btn.classList.add('open');
    answer.classList.add('show');
  }
}

/* ═══════════════════════════════════════
   DIAGNOSIS QUIZ
═══════════════════════════════════════ */
const quizAnswers = {};
const totalSteps = 4;
let currentStep = 1;

function showStep(step) {
  document.querySelectorAll('.quiz-step').forEach(el => {
    el.classList.toggle('active', el.dataset.step === String(step));
  });
  document.querySelector('.quiz-result').classList.remove('active');
}

document.querySelectorAll('.quiz-opt').forEach(btn => {
  btn.addEventListener('click', () => {
    quizAnswers[btn.dataset.q] = btn.dataset.v;
    if (currentStep < totalSteps) {
      currentStep++;
      showStep(currentStep);
    } else {
      showResult();
    }
  });
});

function showResult() {
  document.querySelectorAll('.quiz-step').forEach(el => el.classList.remove('active'));
  const resultBox = document.querySelector('.quiz-result');
  resultBox.classList.add('active');

  const { experience, time, history, goal } = quizAnswers;
  let title, text;

  if (goal === 'fast') {
    title = "Halol gap: bu hozir mos kelmasligi mumkin";
    text = "Konstruksiya va tikuv ko'nikmasi haftalar, ko'pincha oylar ichida shakllanadi — " +
           "2 haftada daromad kerak bo'lsa, bu kurs bunga javob bermaydi. Agar muddat unchalik qattiq " +
           "bo'lmasa va doimiy daromad qurish maqsad bo'lsa, gaplashib ko'ramiz. Aks holda, hozircha " +
           "boshqa tezroq yechimlar (masalan, mavjud ko'nikma bilan kichik buyurtmalar) to'g'riroq bo'lishi mumkin.";
  } else if (experience === 'atelier' || goal === 'scale') {
    title = "Sizga mos: tezkor amaliyot + portfolio nazorati";
    text = "Siz allaqachon tajribaga egasiz, lekin bir joyda tiqilib qolgansiz. Sizga kerak bo'lgan narsa " +
           "yana bir video kurs emas — har bir ishingizga Nasibaning shaxsiy fikri va sifat nazorati. " +
           "Bu aynan atelyeni keyingi bosqichga olib chiqadigan narsa.";
  } else if (history === 'dropped') {
    title = "Sizga mos — lekin avvalgi sababni bilishimiz kerak";
    text = "Avval kursni tashlab ketgansiz — bu juda muhim. Odatda sabab kontent emas, nazoratning yo'qligi " +
           "bo'ladi. Bu tizimda har kuni ishingizni ko'rib turadigan ismli kurator va haftalik aniq muddat bor — " +
           "aynan \"keyinroq qilaman\" holatiga qarshi qurilgan. Lekin suhbatda avvalgi sababni aniq aytib bering.";
  } else if (time === 'low') {
    title = "Mos kelishi mumkin — lekin vaqtni himoya qiling";
    text = "Haftasiga 3 soatdan kam vaqt — bu juda tor, ammo imkonsiz emas. Platforma 24/7 ochiq, jonli darslar " +
           "oyiga atigi 2 marta. Savol shu: bu vaqt yo'qligi, yoki energiya/tartib muammosimi? Suhbatda buni " +
           "aniqlashtirib, real reja tuzamiz.";
  } else {
    title = "Sizga mos: kuratorlangan ritm + jamoa";
    text = "Tajribangiz va vaqtingiz mos keladi. Sizga kerak bo'lgan narsa — haftalik aniq vazifalar, " +
           "har kuni ishingizni ko'rib turadigan kurator va sizga o'xshagan ayollar jamoasi. " +
           "Keyingi qadam — real holatingizni batafsil aytib, aniq rejani birga tuzish.";
  }

  document.getElementById('resultContent').innerHTML = `<h3>${title}</h3><p>${text}</p>`;
}

function restartQuiz() {
  Object.keys(quizAnswers).forEach(k => delete quizAnswers[k]);
  currentStep = 1;
  showStep(1);
}

/* ═══════════════════════════════════════
   LEAD FORM SUBMIT
   Telegram botga yuborish — quyidagi ikkisini
   o'zingizning bot tokeningiz va chat ID'ga moslang
═══════════════════════════════════════ */
const TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN';
const TELEGRAM_CHAT_ID   = 'YOUR_CHAT_ID';

async function submitForm(e) {
  e.preventDefault();
  const form = e.target;
  const btn  = form.querySelector('button[type=submit]');

  document.getElementById('quizExperience').value = quizAnswers.experience || '';
  document.getElementById('quizTime').value       = quizAnswers.time || '';
  document.getElementById('quizHistory').value    = quizAnswers.history || '';
  document.getElementById('quizGoal').value       = quizAnswers.goal || '';

  const data = {
    name:      form.name.value.trim(),
    phone:     form.phone.value.trim(),
    telegram:  form.telegram.value.trim(),
    situation: form.situation.value.trim(),
    quiz:      { ...quizAnswers },
  };

  btn.textContent = 'Yuborilmoqda...';
  btn.disabled = true;

  const text =
    `🧵 *Yangi ariza — Ayollar liboslari*\n\n` +
    `👤 Ism: ${data.name}\n` +
    `📞 Tel: ${data.phone}\n` +
    `✈️ Telegram: ${data.telegram || '—'}\n` +
    `📝 Holati: ${data.situation || '—'}\n` +
    `🔎 Tashxis: tajriba=${data.quiz.experience || '—'}, vaqt=${data.quiz.time || '—'}, ` +
    `tarix=${data.quiz.history || '—'}, maqsad=${data.quiz.goal || '—'}`;

  try {
    await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: TELEGRAM_CHAT_ID,
        text: text,
        parse_mode: 'Markdown',
      }),
    });
  } catch (_) {
    // Silent fail — show success anyway
  }

  document.getElementById('leadForm').style.display = 'none';
  document.getElementById('formSuccess').style.display = 'block';
}

/* ═══════════════════════════════════════
   SMOOTH SCROLL
═══════════════════════════════════════ */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

/* ═══════════════════════════════════════
   SCROLL ANIMATION
═══════════════════════════════════════ */
const observer = new IntersectionObserver(
  entries => entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.opacity = '1';
      e.target.style.transform = 'translateY(0)';
    }
  }),
  { threshold: 0.1 }
);

document.querySelectorAll(
  '.reality-card, .system-item, .faq-item, .testi-card, .pos-card'
).forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(20px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  observer.observe(el);
});
