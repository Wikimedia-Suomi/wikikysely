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
      const unansweredHeader = document.getElementById('unanswered-header');
      const unansweredTable = document.getElementById('unanswered-table');
      const reloadNeeded = !unansweredHeader || !unansweredTable;
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
        const navCount = document.getElementById('unanswered-count');
        if (navCount && typeof data.unanswered_count !== 'undefined') {
          navCount.textContent = data.unanswered_count;
        }
        if (!reloadNeeded) {
          const tbody = unansweredTable.tBodies[0];
          if (tbody) {
            const tr = document.createElement('tr');
            tr.dataset.questionId = data.question_id;

            const tdPublished = document.createElement('td');
            tdPublished.textContent = data.question_published;
            tr.appendChild(tdPublished);

            const tdTitle = document.createElement('td');
            const titleLink = document.createElement('a');
            const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
            titleLink.href = `${data.question_url}?next=${nextParam}`;
            titleLink.textContent = data.question_text;
            tdTitle.appendChild(titleLink);
            tr.appendChild(tdTitle);

            const tdTotal = document.createElement('td');
            tdTotal.className = 'total-answers';
            tdTotal.textContent = data.total;
            tr.appendChild(tdTotal);

            const tdRatio = document.createElement('td');
            tdRatio.className = 'agree-ratio';
            tdRatio.textContent = `${data.agree_ratio}%`;
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
          }
        } else {
          window.location.reload();
        }
      }).catch(() => window.location.reload());
    });
  }

  document.querySelectorAll('a.ajax-delete-answer').forEach(attachDeleteAnswer);
  document.querySelectorAll('a.ajax-delete-question').forEach(attachDeleteQuestion);
});
