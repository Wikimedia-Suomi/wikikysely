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

  function ensureUnansweredTable(data, afterElem) {
    let table = document.getElementById('unanswered-table');
    if (!table) {
      const header = document.createElement('h2');
      header.id = 'unanswered-header';
      header.className = 'mt-3';
      header.textContent = data.unanswered_label;
      afterElem.parentNode.insertBefore(header, afterElem);

      table = document.createElement('table');
      table.id = 'unanswered-table';
      table.className = 'table mb-3 survey-detail-table';
      table.innerHTML = `
        <thead><tr>
          <th>${data.published_label}</th>
          <th>${data.title_label}</th>
          <th>${data.answers_label}</th>
          <th>${data.agree_label}</th>
          <th></th>
        </tr></thead><tbody></tbody>`;
      header.insertAdjacentElement('afterend', table);
    }
    return table;
  }

  function addUnansweredRow(data, afterElem) {
    const table = ensureUnansweredTable(data, afterElem);
    const tbody = table.querySelector('tbody');
    const tr = document.createElement('tr');
    const editButtons = data.can_edit
      ? `<a href="${data.edit_url}" class="btn btn-sm btn-warning me-2">${data.edit_label}</a>` +
        `<a href="${data.delete_url}" class="btn btn-sm btn-danger ajax-delete-question">${data.remove_label}</a>`
      : '';
    tr.innerHTML = `
      <td>${data.question_published}</td>
      <td><a href="${data.question_url}">${data.question_text}</a></td>
      <td class="total-answers">${data.total}</td>
      <td class="agree-ratio">${data.agree_ratio}%</td>
      <td class="text-end">${editButtons}</td>`;
    tbody.appendChild(tr);
    const delLink = tr.querySelector('a.ajax-delete-question');
    if (delLink) attachDeleteQuestion(delLink);
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
        const row = form.closest('tr');
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
        const row = link.closest('tr');
        const tableElem = row ? row.closest('table') : document.getElementById('unanswered-table');
        if (row) row.remove();
        addUnansweredRow(data, tableElem || document.body);
      }).catch(() => window.location.reload());
    });
  }

  document.querySelectorAll('a.ajax-delete-answer').forEach(attachDeleteAnswer);
  document.querySelectorAll('a.ajax-delete-question').forEach(attachDeleteQuestion);
});
