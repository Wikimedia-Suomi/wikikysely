(() => {
  const { createApp, ref } = Vue;
  const root = document.getElementById('nav-qr-app');
  if (!root) return;
  const questionsId = root.dataset.questionsId;
  const resultsId = root.dataset.resultsId;
  const questionsUrl = root.dataset.questionsUrl;
  const resultsUrl = root.dataset.resultsUrl;
  const initialView = root.dataset.initialView || 'questions';
  const navRoot = document.getElementById('nav-answer-app');

  function toggle(view) {
    const qEl = document.getElementById(questionsId);
    const rEl = document.getElementById(resultsId);
    if (qEl) qEl.classList.toggle('d-none', view !== 'questions');
    if (rEl) rEl.classList.toggle('d-none', view !== 'results');
  }

  const app = createApp({
    setup() {
      const view = ref(initialView);
      const count = (window.unansweredCount && typeof window.unansweredCount === 'object' && 'value' in window.unansweredCount)
        ? window.unansweredCount
        : ref(window.unansweredCount || 0);
      window.unansweredCount = count;
      const auth = navRoot ? navRoot.dataset.auth === 'true' : false;
      const answerUrl = navRoot ? navRoot.dataset.answerUrl : '';
      const isActive = ref(navRoot ? navRoot.dataset.isActive === 'true' : false);

      function openFirstQuestion() {
        if (typeof window.openFirstQuestion === 'function') {
          window.openFirstQuestion();
        } else if (answerUrl) {
          window.location.href = answerUrl;
        }
      }

      function show(v, push = true) {
        view.value = v;
        const targetExists = (v === 'questions'
          ? document.getElementById(questionsId)
          : document.getElementById(resultsId)) !== null;
        if (targetExists) {
          toggle(v);
          if (push) {
            const url = v === 'questions' ? questionsUrl : resultsUrl;
            window.history.pushState({ view: v }, '', url);
          }
        } else {
          const url = v === 'questions' ? questionsUrl : resultsUrl;
          if (window.location.pathname !== url) {
            window.location.href = url;
          }
        }
      }

      window.navQr = { show };

      window.addEventListener('popstate', e => {
        const v = (e.state && e.state.view) || initialView;
        show(v, false);
      });

      toggle(view.value);

      return { view, show, count, auth, answerUrl, isActive, openFirstQuestion };
    }
  });

  app.config.compilerOptions.delimiters = ['[[', ']]'];
  app.mount('#nav-qr-app');
})();
