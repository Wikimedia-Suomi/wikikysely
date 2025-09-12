function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

function updateAnswerNavLink(count) {
  const navCount = document.getElementById('unanswered-count');
  if (navCount) {
    navCount.textContent = count;
  }

  const navLink = document.getElementById('answer-nav-link');
  if (!navLink) return;

  if (count > 0 && navLink.tagName === 'SPAN') {
    const url = navLink.dataset.answerUrl;
    const newLink = document.createElement('a');
    newLink.id = 'answer-nav-link';
    newLink.className = 'nav-link';
    newLink.href = url;
    newLink.innerHTML = navLink.innerHTML;
    navLink.replaceWith(newLink);
  } else if (count === 0 && navLink.tagName === 'A') {
    const url = navLink.href;
    const newSpan = document.createElement('span');
    newSpan.id = 'answer-nav-link';
    newSpan.className = 'nav-link text-secondary';
    newSpan.dataset.answerUrl = url;
    newSpan.innerHTML = navLink.innerHTML;
    navLink.replaceWith(newSpan);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const questionEl = document.getElementById('question-text');
  const yesBtn = document.getElementById('btn-yes');
  const noBtn = document.getElementById('btn-no');
  const skipBtn = document.getElementById('btn-skip');
  const form = document.getElementById('answer-question-form');
  if (form) {
    form.addEventListener('submit', ev => ev.preventDefault());
  }
  let questions = [];
  let current = null;

  function showNext() {
    if (questions.length === 0) {
      window.location.reload();
      return;
    }
    const idx = Math.floor(Math.random() * questions.length);
    current = questions.splice(idx, 1)[0];
    if (questionEl) {
      questionEl.textContent = current.text;
    }
    updateAnswerNavLink(questions.length);
  }

  function sendAnswer(value) {
    if (!current) return;
    const data = new FormData();
    data.append('question_id', current.id);
    if (value) data.append('answer', value);
    fetch(answerSubmitUrl, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken') || ''
      },
      body: data
    }).then(resp => resp.ok ? resp.json() : {}).then(data => {
      const msgEl = document.getElementById('ajax-message');
      if (msgEl && data.message) {
        msgEl.textContent = data.message;
        msgEl.className = `alert ${data.skipped ? 'alert-info' : 'alert-success'}`;
      }
      if (typeof data.unanswered_count === 'number') {
        updateAnswerNavLink(data.unanswered_count);
      }
      showNext();
    });
  }

  if (yesBtn) yesBtn.addEventListener('click', e => { e.preventDefault(); sendAnswer('yes'); });
  if (noBtn) noBtn.addEventListener('click', e => { e.preventDefault(); sendAnswer('no'); });
  if (skipBtn) skipBtn.addEventListener('click', e => { e.preventDefault(); sendAnswer(''); });

  fetch(unansweredQuestionsUrl, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  }).then(resp => resp.ok ? resp.json() : {questions: []}).then(data => {
    questions = data.questions || [];
    showNext();
  });
});
