document.addEventListener('DOMContentLoaded', () => {
  let content = document.getElementById('content');
  const questionsLink = document.getElementById('nav-questions');
  const answersLink = document.getElementById('nav-answers');
  const navRoot = document.getElementById('nav-answer-app');

  const questionsPath = questionsLink ? questionsLink.pathname : null;
  const answersPath = answersLink ? answersLink.pathname : null;

  function setActive(path) {
    if (questionsLink) questionsLink.classList.toggle('active', path === questionsPath);
    if (answersLink) answersLink.classList.toggle('active', path === answersPath);
    if (navRoot && window.navApp) {
      const active = path === questionsPath;
      window.navApp.isActive = active;
      navRoot.dataset.isActive = active ? 'true' : 'false';
    }
    const langNext = document.getElementById('language-next');
    if (langNext) langNext.value = path;
  }

  function loadPage(url, push = true) {
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(resp => resp.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newContent = doc.getElementById('content');
        const newTitle = doc.querySelector('title');
        if (newContent) {
          content.replaceWith(newContent);
          content = newContent;
          if (newTitle) document.title = newTitle.textContent;
          window.mountSurveyDetailApp();
          window.mountAnswersApp();
          setActive(new URL(url, window.location.origin).pathname);
          window.scrollTo(0, 0);
        }
        if (push) {
          window.history.pushState({}, '', url);
        }
      });
  }

  document.addEventListener('click', ev => {
    const link = ev.target.closest('a');
    if (!link) return;
    if (link.target === '_blank' || link.hasAttribute('download')) return;
    if (link.origin !== window.location.origin) return;
    const path = link.pathname;
    if (path === questionsPath || path === answersPath) {
      ev.preventDefault();
      loadPage(link.href);
    }
  });

  window.addEventListener('popstate', () => {
    loadPage(location.href, false);
  });

  // initial mount for current page
  setActive(window.location.pathname);
  window.mountSurveyDetailApp();
  window.mountAnswersApp();
});

