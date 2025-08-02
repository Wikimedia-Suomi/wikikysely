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
        if (!data || !data.hidden) { window.location.reload(); return; }
        const row = link.closest('tr');
        if (row) row.remove();
      }).catch(() => window.location.reload());
    });
  }


  function attachAnswerForm(form) {
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
  }

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
        const navCount = document.getElementById('unanswered-count');
        if (navCount && typeof data.unanswered_count !== 'undefined') {
          navCount.textContent = data.unanswered_count;
        }
        if (updateUnanswered) {
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

  function buildTables(data) {
    const questions = data.questions || [];
    const unansweredHeader = document.getElementById('unanswered-header');
    const unansweredTable = document.getElementById('unanswered-table');
    const unansweredBody = unansweredTable ? unansweredTable.tBodies[0] : null;
    const answersHeader = document.getElementById('my-answers-header');
    const answersTable = document.getElementById('my-answers-table');
    const answersBody = answersTable ? answersTable.tBodies[0] : null;
    let unansweredCount = 0;

    questions.forEach(q => {
      if (!unansweredBody || !answersBody) return;
      if (q.user_answer) {
        const tr = document.createElement('tr');
        tr.dataset.questionId = q.id;

        const tdPublished = document.createElement('td');
        tdPublished.setAttribute('data-label', LABEL_PUBLISHED);
        tdPublished.textContent = q.published;
        tr.appendChild(tdPublished);

        const tdTitle = document.createElement('td');
        tdTitle.setAttribute('data-label', LABEL_TITLE);
        const titleLink = document.createElement('a');
        const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
        titleLink.href = `${q.answer_url}?next=${nextParam}`;
        titleLink.textContent = q.text;
        tdTitle.appendChild(titleLink);
        tr.appendChild(tdTitle);

        const tdTotal = document.createElement('td');
        tdTotal.className = 'total-answers';
        tdTotal.setAttribute('data-label', LABEL_ANSWERS);
        tdTotal.textContent = q.total_answers;
        tr.appendChild(tdTotal);

        const tdRatio = document.createElement('td');
        tdRatio.className = 'agree-ratio';
        tdRatio.setAttribute('data-label', LABEL_AGREE);
        tdRatio.textContent = `${q.agree_ratio.toFixed ? q.agree_ratio.toFixed(1) : q.agree_ratio}%`;
        tr.appendChild(tdRatio);

        const tdActions = document.createElement('td');
        tdActions.className = 'text-end';
        if (SURVEY_STATE === 'running') {
          const form = document.createElement('form');
          form.method = 'post';
          form.action = q.answer_edit_url;
          form.className = 'd-inline ajax-answer-form';

          const qInput = document.createElement('input');
          qInput.type = 'hidden';
          qInput.name = 'question_id';
          qInput.value = q.id;
          form.appendChild(qInput);

          const group = document.createElement('div');
          group.className = 'btn-group yes-no-group';
          group.setAttribute('role', 'group');
          group.setAttribute('aria-label', LABEL_ANSWER);

          const yesInput = document.createElement('input');
          yesInput.type = 'radio';
          yesInput.className = 'btn-check';
          yesInput.name = 'answer';
          yesInput.id = `answer-${q.answer_id}-yes`;
          yesInput.value = 'yes';
          if (q.user_answer === 'yes') yesInput.checked = true;
          const yesLabel = document.createElement('label');
          yesLabel.className = 'btn btn-sm btn-outline-success';
          yesLabel.setAttribute('for', `answer-${q.answer_id}-yes`);
          yesLabel.textContent = LABEL_YES;

          const noInput = document.createElement('input');
          noInput.type = 'radio';
          noInput.className = 'btn-check';
          noInput.name = 'answer';
          noInput.id = `answer-${q.answer_id}-no`;
          noInput.value = 'no';
          if (q.user_answer === 'no') noInput.checked = true;
          const noLabel = document.createElement('label');
          noLabel.className = 'btn btn-sm btn-outline-danger';
          noLabel.setAttribute('for', `answer-${q.answer_id}-no`);
          noLabel.textContent = LABEL_NO;

          group.appendChild(yesInput);
          group.appendChild(yesLabel);
          group.appendChild(noInput);
          group.appendChild(noLabel);
          form.appendChild(group);
          attachAnswerForm(form);
          tdActions.appendChild(form);

          const delLink = document.createElement('a');
          delLink.href = q.answer_delete_url;
          delLink.className = 'btn btn-sm btn-danger ms-2 ajax-delete-answer';
          delLink.textContent = LABEL_REMOVE_ANSWER;
          delLink.dataset.questionId = q.id;
          tdActions.appendChild(delLink);
          attachDeleteAnswer(delLink);
        }
        tr.appendChild(tdActions);
        answersBody.appendChild(tr);
      } else {
        unansweredCount += 1;
        const tr = document.createElement('tr');
        tr.dataset.questionId = q.id;

        const tdPublished = document.createElement('td');
        tdPublished.setAttribute('data-label', LABEL_PUBLISHED);
        tdPublished.textContent = q.published;
        tr.appendChild(tdPublished);

        const tdTitle = document.createElement('td');
        tdTitle.setAttribute('data-label', LABEL_TITLE);
        if (IS_AUTHENTICATED) {
          const link = document.createElement('a');
          const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
          link.href = `${q.answer_url}?next=${nextParam}`;
          link.textContent = q.text;
          tdTitle.appendChild(link);
        } else {
          tdTitle.textContent = q.text;
        }
        tr.appendChild(tdTitle);

        const tdTotal = document.createElement('td');
        tdTotal.className = 'total-answers';
        tdTotal.setAttribute('data-label', LABEL_ANSWERS);
        tdTotal.textContent = q.total_answers;
        tr.appendChild(tdTotal);

        const tdRatio = document.createElement('td');
        tdRatio.className = 'agree-ratio';
        tdRatio.setAttribute('data-label', LABEL_AGREE);
        tdRatio.textContent = `${q.agree_ratio.toFixed ? q.agree_ratio.toFixed(1) : q.agree_ratio}%`;
        tr.appendChild(tdRatio);

        const tdActions = document.createElement('td');
        tdActions.className = 'text-end';
        if (q.can_edit) {
          const editLink = document.createElement('a');
          editLink.href = q.edit_url;
          editLink.className = 'btn btn-sm btn-warning me-2';
          editLink.textContent = LABEL_EDIT;
          tdActions.appendChild(editLink);

          const delLink = document.createElement('a');
          delLink.href = q.delete_url;
          delLink.className = 'btn btn-sm btn-danger ajax-delete-question';
          delLink.textContent = LABEL_REMOVE_QUESTION;
          tdActions.appendChild(delLink);
          attachDeleteQuestion(delLink);
        }
        tr.appendChild(tdActions);
        unansweredBody.appendChild(tr);
      }
    });

    if (unansweredCount > 0) {
      if (unansweredHeader) unansweredHeader.style.display = '';
      if (unansweredTable) unansweredTable.style.display = '';
      const ansBtn = document.getElementById('answer-survey-btn');
      if (ansBtn) ansBtn.style.display = '';
    } else if (questions.length > 0) {
      const answersBtn = document.getElementById('survey-answers-btn');
      if (answersBtn) answersBtn.style.display = '';
    }

    if (answersBody && answersBody.children.length > 0) {
      if (answersHeader) answersHeader.style.display = '';
      if (answersTable) answersTable.style.display = '';
    }

    if (typeof initSortableTables === 'function') {
      initSortableTables('.survey-detail-table');
    }
  }

  fetch(QUESTIONS_API_URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(resp => resp.ok ? resp.json() : Promise.reject())
    .then(buildTables)
    .catch(() => {});
});
