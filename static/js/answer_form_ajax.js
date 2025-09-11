document.addEventListener('DOMContentLoaded', () => {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function formatPercentage(value) {
    const num = typeof value === 'number' ? value : parseFloat(value);
    if (Number.isNaN(num)) return value;
    return num.toFixed(1).replace('.', ',');
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

  const form = document.getElementById('answer-question-form');
  if (!form) return;

  form.addEventListener('submit', ev => {
    ev.preventDefault();
    const formData = new FormData(form);
    if (ev.submitter && ev.submitter.name) {
      formData.append(ev.submitter.name, ev.submitter.value);
    }

    fetch(form.action, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken') || ''
      },
      body: formData
    }).then(resp => resp.ok ? resp.json() : Promise.reject()).then(data => {
      if (!data || !data.success) { window.location.reload(); return; }

      const yesCell = document.getElementById('yes-count');
      const noCell = document.getElementById('no-count');
      const totalCell = document.getElementById('total-count');
      const agreeCell = document.getElementById('agree-ratio');
      const noCount = data.total - data.yes_count;
      if (yesCell) yesCell.textContent = data.yes_count;
      if (noCell) noCell.textContent = noCount;
      if (totalCell) totalCell.textContent = data.total;
      if (agreeCell) agreeCell.textContent = `${formatPercentage(data.agree_ratio)}%`;

      if (typeof data.unanswered_count !== 'undefined') {
        updateAnswerNavLink(data.unanswered_count);
      }

      const msgBox = document.getElementById('ajax-message');
      if (msgBox) {
        const alertType = data.skipped ? 'alert-info' : 'alert-success';
        msgBox.className = `alert ${alertType} mt-2`;
        msgBox.textContent = data.message || '';
      }
    }).catch(() => window.location.reload());
  });
});

