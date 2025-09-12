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

    function showAlert(message, type = 'info') {
      const container = document.querySelector('.container');
      if (!container) return;
      container.querySelectorAll('.alert').forEach(el => el.remove());
      const alert = document.createElement('div');
      alert.className = `alert alert-${type} alert-dismissible fade show`;
      alert.setAttribute('role', 'alert');
      const span = document.createElement('span');
      span.textContent = message;
      alert.appendChild(span);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn-close';
      btn.setAttribute('data-bs-dismiss', 'alert');
      btn.setAttribute('aria-label', 'Close');
      alert.appendChild(btn);
      container.prepend(alert);
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
          if (ratioCell) ratioCell.textContent = `${formatPercentage(data.agree_ratio)}%`;
        }
      }).catch(() => window.location.reload());
    });
  }

  document.querySelectorAll('form.ajax-answer-form').forEach(attachAnswerForm);

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

    document.querySelectorAll('form.ajax-answer-question').forEach(form => {
      form.addEventListener('submit', ev => {
        ev.preventDefault();
        const formData = new FormData(form);
        let answerValue = '';
        const isEdit = form.dataset.isEdit === 'true';
        if (ev.submitter && ev.submitter.name) {
          formData.append(ev.submitter.name, ev.submitter.value);
          if (ev.submitter.name === 'answer') {
            answerValue = ev.submitter.value;
          }
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
          const nextField = form.querySelector('input[name="next"]');
          if (isEdit && nextField && nextField.value) {
            window.location.href = nextField.value;
            return;
          }
          const qid = data.question_id;
          document.querySelectorAll(`[data-question-id="${qid}"]`).forEach(el => el.remove());
          const nextCard = document.querySelector('.unanswered-card.d-none');
          if (nextCard) {
            nextCard.classList.remove('d-none');
          }
          if (data.message) {
            showAlert(data.message, data.message_type || 'info');
          }
          if (!isEdit) {
            const skipHelp = document.getElementById('skip-help-message');
            const thanksMsg = document.getElementById('thanks-message');
            if (answerValue === '') {
              if (skipHelp) skipHelp.style.display = '';
              if (thanksMsg) thanksMsg.style.display = 'none';
            } else if (answerValue === 'yes' || answerValue === 'no') {
              if (skipHelp) skipHelp.style.display = 'none';
              if (thanksMsg) thanksMsg.style.display = '';
            }
          }
          if (answerValue === 'yes' || answerValue === 'no') {
          const tbody = document.getElementById('my-answers-body');
        if (tbody) {
          const tr = document.createElement('tr');
          tr.dataset.questionId = qid;

          const today = new Date().toISOString().slice(0, 10);
          const tdDate = document.createElement('td');
          tdDate.dataset.label = answerDateLabel;
          tdDate.textContent = today;
          tr.appendChild(tdDate);

          const tdTitle = document.createElement('td');
          tdTitle.dataset.label = titleLabel;
          const link = document.createElement('a');
          const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
          link.href = `${form.action}?next=${nextParam}`;
          const title = form.closest('.card')?.querySelector('.card-title')?.textContent?.trim() || '';
          link.textContent = title;
          tdTitle.appendChild(link);
          tr.appendChild(tdTitle);

          const tdTotal = document.createElement('td');
          tdTotal.className = 'total-answers';
          tdTotal.dataset.label = answersLabel;
          tdTotal.textContent = data.total;
          tr.appendChild(tdTotal);

          const tdAgree = document.createElement('td');
          tdAgree.className = 'agree-ratio';
          tdAgree.dataset.label = agreeLabel;
          tdAgree.textContent = `${formatPercentage(data.agree_ratio)}%`;
          tr.appendChild(tdAgree);

          const tdActions = document.createElement('td');
          tdActions.className = 'text-end';
          if (data.edit_url && data.delete_url && data.answer_id) {
            const editForm = document.createElement('form');
            editForm.method = 'post';
            editForm.action = data.edit_url;
            editForm.className = 'd-inline ajax-answer-form';
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = getCookie('csrftoken') || '';
            editForm.appendChild(csrfInput);
            const qInput = document.createElement('input');
            qInput.type = 'hidden';
            qInput.name = 'question_id';
            qInput.value = qid;
            editForm.appendChild(qInput);
            const btnGroup = document.createElement('div');
            btnGroup.className = 'btn-group yes-no-group';
            btnGroup.role = 'group';
            btnGroup.setAttribute('aria-label', answerLabel);
            const yesInput = document.createElement('input');
            yesInput.type = 'radio';
            yesInput.className = 'btn-check';
            yesInput.name = 'answer';
            yesInput.id = `answer-${data.answer_id}-yes`;
            yesInput.value = 'yes';
            if (answerValue === 'yes') yesInput.checked = true;
            const yesLabelEl = document.createElement('label');
            yesLabelEl.className = 'btn btn-sm btn-outline-success';
            yesLabelEl.setAttribute('for', `answer-${data.answer_id}-yes`);
            yesLabelEl.textContent = yesLabel;
            const noInput = document.createElement('input');
            noInput.type = 'radio';
            noInput.className = 'btn-check';
            noInput.name = 'answer';
            noInput.id = `answer-${data.answer_id}-no`;
            noInput.value = 'no';
            if (answerValue === 'no') noInput.checked = true;
            const noLabelEl = document.createElement('label');
            noLabelEl.className = 'btn btn-sm btn-outline-danger';
            noLabelEl.setAttribute('for', `answer-${data.answer_id}-no`);
            noLabelEl.textContent = noLabel;
            btnGroup.appendChild(yesInput);
            btnGroup.appendChild(yesLabelEl);
            btnGroup.appendChild(noInput);
            btnGroup.appendChild(noLabelEl);
            editForm.appendChild(btnGroup);
            tdActions.appendChild(editForm);
            attachAnswerForm(editForm);
            const delLink = document.createElement('a');
            delLink.href = data.delete_url;
            delLink.className = 'btn btn-sm btn-danger ms-2 ajax-delete-answer';
            delLink.dataset.questionId = qid;
            delLink.dataset.noReload = 'true';
            delLink.textContent = removeAnswerLabel;
            tdActions.appendChild(delLink);
            attachDeleteAnswer(delLink);
          }
          tr.appendChild(tdActions);

          tbody.prepend(tr);

          const header = document.getElementById('my-answers-header');
          if (header) {
            header.hidden = false;
            header.style.display = '';
          }

          const table = document.getElementById('my-answers-table');
          if (table) {
            table.hidden = false;
            table.style.display = '';
          }

          const collapseDiv = document.getElementById('myAnswers');
          if (collapseDiv) {
            collapseDiv.hidden = false;
            collapseDiv.style.display = '';
            if (typeof bootstrap !== 'undefined') {
              const coll = bootstrap.Collapse.getOrCreateInstance(collapseDiv, { toggle: false });
              coll.show();
            } else {
              collapseDiv.classList.add('show');
            }
            const toggle = document.querySelector('a[href="#myAnswers"]');
            if (toggle) {
              toggle.classList.remove('collapsed');
              toggle.setAttribute('aria-expanded', 'true');
            }
          }

          const placeholder = tbody.querySelector('.no-answers-placeholder');
          if (placeholder) placeholder.remove();
        }
        }
        const countEl = document.getElementById('unanswered-count');
        if (countEl && !isEdit) {
          let newCount = typeof data.unanswered_count !== 'undefined'
            ? data.unanswered_count
            : Math.max(0, (parseInt(countEl.textContent, 10) || 0) - 1);
          countEl.textContent = newCount;
          updateAnswerNavLink(newCount);
          if (typeof completionUrl !== 'undefined') {
            const remainingForms = document.querySelectorAll('form.ajax-answer-question').length;
            if (remainingForms === 0) {
              if (newCount === 0) {
                window.location.href = completionUrl;
              } else {
                window.location.reload();
              }
            }
          }
        }
      }).catch(() => window.location.reload());
    });
  });
});
