/* ═══════════════════════════════════════
   COUNTDOWN TIMER
   Seminar sanasini o'zgartirish uchun:
   TARGET_DATE ni o'zgartiring
═══════════════════════════════════════ */
const TARGET_DATE = new Date('2025-05-15T10:00:00');

function updateCountdown() {
  const now = new Date();
  const diff = TARGET_DATE - now;

  if (diff <= 0) {
    document.getElementById('countdown').innerHTML =
      '<span style="color:var(--accent);font-size:1.1rem;font-weight:700">Seminar boshlandi!</span>';
    return;
  }

  const days  = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const mins  = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const secs  = Math.floor((diff % (1000 * 60)) / 1000);

  const pad = n => String(n).padStart(2, '0');
  document.getElementById('cd-days').textContent  = pad(days);
  document.getElementById('cd-hours').textContent = pad(hours);
  document.getElementById('cd-mins').textContent  = pad(mins);
  document.getElementById('cd-secs').textContent  = pad(secs);
}

updateCountdown();
setInterval(updateCountdown, 1000);

/* ═══════════════════════════════════════
   FAQ ACCORDION
═══════════════════════════════════════ */
function toggleFaq(btn) {
  const answer = btn.nextElementSibling;
  const isOpen = btn.classList.contains('open');

  // Close all
  document.querySelectorAll('.faq-q').forEach(b => {
    b.classList.remove('open');
    b.nextElementSibling.classList.remove('show');
  });

  // Open clicked if was closed
  if (!isOpen) {
    btn.classList.add('open');
    answer.classList.add('show');
  }
}

/* ═══════════════════════════════════════
   FORM SUBMIT
   Telegram botga yoki Webhook ga yuborish
   WEBHOOK_URL ni o'z serveringizga moslashtiring
═══════════════════════════════════════ */
const TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN';  // yoki backend webhook URL
const TELEGRAM_CHAT_ID   = '5741383928';       // Founder ID

async function submitForm(e) {
  e.preventDefault();
  const form = e.target;
  const btn  = form.querySelector('button[type=submit]');

  const data = {
    name:      form.name.value.trim(),
    phone:     form.phone.value.trim(),
    business:  form.business.value,
    employees: form.employees.value,
  };

  btn.textContent = 'Yuborilmoqda...';
  btn.disabled = true;

  // Telegram'ga xabar yuborish
  const text =
    `🆕 *Yangi ariza!*\n\n` +
    `👤 Ism: ${data.name}\n` +
    `📞 Tel: ${data.phone}\n` +
    `🏪 Biznes: ${data.business}\n` +
    `👥 Xodimlar: ${data.employees}`;

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

  // Show success
  document.getElementById('leadForm').style.display = 'none';
  document.getElementById('formSuccess').style.display = 'block';
}

/* ═══════════════════════════════════════
   SMOOTH SCROLL for anchor links
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
   SCROLL ANIMATION (fade-in on scroll)
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
  '.pain-card, .seg-card, .prog-item, .res-card, .price-card, .faq-item'
).forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(20px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  observer.observe(el);
});
