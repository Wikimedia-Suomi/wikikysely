const { createApp, ref, onMounted, nextTick, watch } = Vue;

window.mountAnswersApp = function () {
  const root = document.getElementById('answers-app');
  if (!root) return;

  const questionsJsonUrl = root.dataset.questionsJsonUrl;
  const yesLabel = root.dataset.yesLabel;
  const noLabel = root.dataset.noLabel;
  const noAnswersLabel = root.dataset.noAnswersLabel;

  const app = createApp({
    setup() {
      const questions = ref([]);
      const loading = ref(true);
      const isAuthenticated = root.dataset.auth === 'true';
      const answerUrlTemplate = root.dataset.answerUrlTemplate;
      const totalUsers = ref(parseInt(root.dataset.totalUsers, 10) || 0);
      const chartTypeKey = 'resultsChartType';
      const chartType = ref(localStorage.getItem(chartTypeKey) || 'pie');
      watch(chartType, val => localStorage.setItem(chartTypeKey, val));

      function formatDate(str) {
        return str ? str.slice(0, 10) : '';
      }

      function answerUrl(id) {
        const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
        return answerUrlTemplate.replace('0', id) + `?next=${nextParam}`;
      }

      function percent(count, total) {
        return total ? (count / total) * 100 : 0;
      }

      function renderPieCharts() {
        const successColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-success').trim() || 'green';
        const dangerColor = getComputedStyle(document.documentElement).getPropertyValue('--bs-danger').trim() || 'red';
        const placeholderColor =
          getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary-bg').trim() ||
          getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary').trim() || 'gray';
        const pieContainers = document.querySelectorAll('#pieCharts .pie-chart');
        const totals = Array.from(pieContainers, el => parseInt(el.dataset.total));
        const maxTotal = Math.max(...totals, 1);
        const maxSize = 200;
        pieContainers.forEach(el => {
          const yes = parseInt(el.dataset.yes);
          const no = parseInt(el.dataset.no);
          const total = parseInt(el.dataset.total);
          const placeholderSize = 100;
          const size = total === 0 ? placeholderSize : maxSize * Math.sqrt(total / maxTotal);
          const canvas = el.querySelector('canvas');
          canvas.width = size;
          canvas.height = size;
          const data = total === 0 ? [1] : [yes, no];
          const colors = total === 0 ? [placeholderColor] : [successColor, dangerColor];
          new Chart(canvas, {
            type: 'pie',
            data: {
              labels: total === 0 ? [noAnswersLabel] : [yesLabel, noLabel],
              datasets: [
                {
                  data: data,
                  backgroundColor: colors
                }
              ]
            },
            options: {
              responsive: false,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false }
              }
            }
          });
        });
      }

      function fetchQuestions() {
        loading.value = true;
        return fetch(questionsJsonUrl)
          .then(resp => resp.json())
          .then(data => {
            questions.value = data.questions || [];
          })
          .finally(() => {
            loading.value = false;
            nextTick(() => {
              renderPieCharts();
              if (typeof initSortableTables === 'function') {
                initSortableTables('#answerTable');
              }
            });
          });
      }

      onMounted(() => {
        fetchQuestions();
      });

      return { questions, loading, isAuthenticated, formatDate, answerUrl, percent, chartType, totalUsers };
    }
  });

  app.config.compilerOptions.delimiters = ['[[', ']]'];
  app.mount('#answers-app');
};

window.mountAnswersApp();

