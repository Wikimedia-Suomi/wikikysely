document.addEventListener('DOMContentLoaded', () => {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function attachDeleteQuestion(link) {
    link.addEventListener('click', ev => {
      ev.preventDefault();
      fetch(link.href, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        }
      }).then(resp => resp.ok ? resp.json() : Promise.reject()).then(data => {
        if (!data || !data.deleted) { window.location.reload(); return; }
        const row = link.closest('tr');
        if (row) row.remove();
      }).catch(() => window.location.reload());
    });
  }


  document.querySelectorAll('form.ajax-answer-form').forEach(form => {
    form.addEventListener('change', event => {
      if (event.target.name !== 'answer') return;
      const formData = new FormData(form);
      fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        },
        body: formData
      }).then(resp => resp.ok ? resp.json() : Promise.reject()).then(data => {
        if (!data || !data.success) { window.location.reload(); return; }
        let row = form.closest('tr');
        if (!row) {
          const qInput = form.querySelector('input[name="question_id"]');
          if (qInput) {
            row = document.querySelector(`tr[data-question-id="${qInput.value}"]`);
          }
        }
        if (row) {
          const totalCell = row.querySelector('.total-answers');
          const ratioCell = row.querySelector('.agree-ratio');
          if (totalCell) totalCell.textContent = data.total;
          if (ratioCell) ratioCell.textContent = `${data.agree_ratio}%`;
        }
      }).catch(() => window.location.reload());
    });
  });

  function attachDeleteAnswer(link) {
    link.addEventListener('click', ev => {
      ev.preventDefault();
      fetch(link.href, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        }
      }).then(resp => resp.ok ? resp.json() : Promise.reject()).then(data => {
        if (!data || !data.deleted) { window.location.reload(); return; }
        let row = link.closest('tr');
        if (!row) {
          const qid = link.dataset.questionId;
          if (qid) {
            row = document.querySelector(`tr[data-question-id="${qid}"]`);
          }
        }
          if (row) row.remove();
      }).catch(() => window.location.reload());
    });
  }

  document.querySelectorAll('a.ajax-delete-answer').forEach(attachDeleteAnswer);
  document.querySelectorAll('a.ajax-delete-question').forEach(attachDeleteQuestion);
});
