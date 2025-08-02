const { createApp, ref, onMounted, nextTick } = Vue;

let answersApp = null;

function mountAnswersApp() {
  const root = document.getElementById('survey-answers-app');
  if (!root) return null;
  if (answersApp) return answersApp;
  const jsonUrl = root.dataset.jsonUrl;
  const pageUrl = root.dataset.pageUrl;
  const wikitextUrl = root.dataset.wikitextUrl;
  const auth = root.dataset.auth === 'true';
  const answerUrlTemplate = root.dataset.answerUrlTemplate;
  const yesLabel = root.dataset.yesLabel;
  const noLabel = root.dataset.noLabel;

  const app = createApp({
    setup() {
      const rows = ref([]);
      const totalUsers = ref(0);
      const loading = ref(true);
      const pieChart = ref(null);
      const barChart = ref(null);

      function renderCharts() {
        if (typeof Chart === 'undefined') return;
        const yesTotal = rows.value.reduce((sum, r) => sum + r.yes, 0);
        const noTotal = rows.value.reduce((sum, r) => sum + r.no, 0);
        const pieCtx = document.getElementById('answerPieChart');
        if (pieCtx) {
          if (pieChart.value) pieChart.value.destroy();
          pieChart.value = new Chart(pieCtx, {
            type: 'pie',
            data: {
              labels: [yesLabel, noLabel],
              datasets: [{
                data: [yesTotal, noTotal],
                backgroundColor: ['#198754', '#dc3545']
              }]
            }
          });
        }
        const barCtx = document.getElementById('answerBarChart');
        if (barCtx) {
          if (barChart.value) barChart.value.destroy();
          barChart.value = new Chart(barCtx, {
            type: 'bar',
            data: {
              labels: [yesLabel, noLabel],
              datasets: [{
                data: [yesTotal, noTotal],
                backgroundColor: ['#198754', '#dc3545']
              }]
            },
            options: {
              plugins: {
                legend: { display: false }
              }
            }
          });
        }
      }

      function fetchData() {
        loading.value = true;
        return fetch(jsonUrl)
          .then(r => r.json())
          .then(data => {
            const items = data.questions || [];
            rows.value = items.map(q => ({
              id: q.id,
              text: q.text,
              published: q.created_at,
              yes: q.yes_count,
              no: q.no_count,
              total: q.total_answers,
              agree_ratio: q.agree_ratio,
              my_answer: q.my_answer
            }));
            totalUsers.value = data.total_users || 0;
          })
          .finally(() => {
            loading.value = false;
            nextTick(() => {
              if (typeof initSortableTables === 'function') {
                initSortableTables('#answerTable');
              }
              renderCharts();
            });
          });
      }

      function answerUrl(id) {
        if (!auth) return '#';
        const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
        return answerUrlTemplate.replace('0', id) + `?next=${nextParam}`;
      }

      onMounted(() => {
        fetchData();
      });

      return { rows, totalUsers, loading, auth, answerUrl, pageUrl, wikitextUrl };
    }
  });
  app.config.compilerOptions.delimiters = ['[[', ']]'];
  answersApp = app.mount('#survey-answers-app');
  return answersApp;
}

function showAnswers() {
  const root = document.getElementById('survey-answers-app');
  if (!root) return;
  mountAnswersApp();
  const detail = document.getElementById('survey-detail-app');
  if (detail) detail.classList.add('d-none');
  root.classList.remove('d-none');
  history.pushState({ page: 'answers' }, '', root.dataset.pageUrl);
}

function hideAnswers() {
  const root = document.getElementById('survey-answers-app');
  if (!root) return;
  const detail = document.getElementById('survey-detail-app');
  root.classList.add('d-none');
  if (detail) detail.classList.remove('d-none');
}

window.openAnswers = showAnswers;

window.addEventListener('popstate', () => {
  const root = document.getElementById('survey-answers-app');
  if (!root) return;
  if (window.location.pathname === root.dataset.pageUrl) {
    showAnswers();
  } else {
    hideAnswers();
  }
});

// Mount immediately if answers app is visible (direct navigation)
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('survey-answers-app');
  if (root && !root.classList.contains('d-none')) {
    mountAnswersApp();
  }
});

// Navigation link app
const navRoot = document.getElementById('nav-answers-app');
if (navRoot) {
  const navApp = createApp({
    setup() {
      const label = navRoot.dataset.label;
      const pageUrl = navRoot.dataset.pageUrl;
      const isActive = navRoot.dataset.isActive === 'true';
      function open() {
        if (typeof window.openAnswers === 'function') {
          window.openAnswers();
        } else {
          window.location.href = pageUrl;
        }
      }
      return { label, pageUrl, isActive, open };
    }
  });
  navApp.config.compilerOptions.delimiters = ['[[', ']]'];
  navApp.mount('#nav-answers-app');
}

