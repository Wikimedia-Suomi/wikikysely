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

  const initialNavCount = document.getElementById('unanswered-count');
  if (initialNavCount) {
    const initialCount = parseInt(initialNavCount.textContent, 10) || 0;
    updateAnswerNavLink(initialCount);
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
        if (!data || !data.hidden) { window.location.reload(); return; }
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
          if (ratioCell) ratioCell.textContent = `${formatPercentage(data.agree_ratio)}%`;
        }
      }).catch(() => window.location.reload());
    });
  });

  function attachDeleteAnswer(link) {
    link.addEventListener('click', ev => {
      ev.preventDefault();
      const unansweredHeader = document.getElementById('unanswered-header');
      const unansweredTable = document.getElementById('unanswered-table');
      const updateUnanswered = unansweredHeader && unansweredTable;
      const noReload = link.dataset.noReload !== undefined;
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
        if (typeof data.unanswered_count !== 'undefined') {
          updateAnswerNavLink(data.unanswered_count);
        }
        const answerBtn = document.getElementById('answer-survey-btn');
        const answersBtn = document.getElementById('answers-btn');
        if (typeof data.unanswered_count !== 'undefined' && answerBtn && answersBtn) {
          if (data.unanswered_count > 0) {
            answerBtn.style.display = '';
            answersBtn.style.display = 'none';
          } else {
            answersBtn.style.display = '';
            answerBtn.style.display = 'none';
          }
        }
        if (updateUnanswered) {
          const tbody = unansweredTable.tBodies[0];
          if (tbody) {
            const tr = document.createElement('tr');
            tr.dataset.questionId = data.question_id;

            const tdId = document.createElement('td');
            tdId.dataset.label = data.id_label;
            tdId.textContent = data.question_id;
            tr.appendChild(tdId);

            const tdPublished = document.createElement('td');
            tdPublished.dataset.label = data.published_label;
            tdPublished.textContent = data.question_published;
            tr.appendChild(tdPublished);

            const tdTitle = document.createElement('td');
            tdTitle.dataset.label = data.title_label;
            const titleLink = document.createElement('a');
            const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
            titleLink.href = `${data.question_url}?next=${nextParam}`;
            titleLink.textContent = data.question_text;
            tdTitle.appendChild(titleLink);
            tr.appendChild(tdTitle);

            const tdTotal = document.createElement('td');
            tdTotal.className = 'total-answers';
            tdTotal.dataset.label = data.answers_label;
            tdTotal.textContent = data.total;
            tr.appendChild(tdTotal);

            const tdRatio = document.createElement('td');
            tdRatio.className = 'agree-ratio';
            tdRatio.dataset.label = data.agree_label;
            tdRatio.textContent = `${formatPercentage(data.agree_ratio)}%`;
            tr.appendChild(tdRatio);

            const tdActions = document.createElement('td');
            tdActions.className = 'text-end';
            if (data.can_edit) {
              const editLink = document.createElement('a');
              editLink.href = data.edit_url;
              editLink.className = 'btn btn-sm btn-warning me-2';
              editLink.textContent = data.edit_label;
              tdActions.appendChild(editLink);

              const delLink = document.createElement('a');
              delLink.href = data.delete_url;
              delLink.className = 'btn btn-sm btn-danger ajax-delete-question';
              delLink.textContent = data.remove_label;
              tdActions.appendChild(delLink);
              attachDeleteQuestion(delLink);
            }
            tr.appendChild(tdActions);

            tbody.appendChild(tr);
            if (unansweredHeader.style.display === 'none') {
              unansweredHeader.style.display = '';
            }
            if (unansweredTable.style.display === 'none') {
              unansweredTable.style.display = '';
            }
          }
        } else if (!noReload) {
          window.location.reload();
        }
      }).catch(() => window.location.reload());
    });
  }

  document.querySelectorAll('a.ajax-delete-answer').forEach(attachDeleteAnswer);
  document.querySelectorAll('a.ajax-delete-question').forEach(attachDeleteQuestion);
});
