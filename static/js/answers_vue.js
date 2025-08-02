const { createApp, ref, onMounted, nextTick } = Vue;

const app = createApp({
  setup() {
    const questions = ref([]);
    const loading = ref(true);
    const root = document.getElementById('answers-table-app');
    const isAuthenticated = root.dataset.auth === 'true';
    const answerUrlTemplate = root.dataset.answerUrlTemplate;

    function formatDate(str) {
      return str ? str.slice(0, 10) : '';
    }

    function answerUrl(id) {
      const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
      return answerUrlTemplate.replace('0', id) + `?next=${nextParam}`;
    }

    function fetchQuestions() {
      loading.value = true;
      return fetch(window.questionsJsonUrl)
        .then(resp => resp.json())
        .then(data => {
          questions.value = data.questions || [];
        })
        .finally(() => {
          loading.value = false;
          nextTick(() => {
            if (typeof initSortableTables === 'function') {
              initSortableTables('#answerTable');
            }
          });
        });
    }

    onMounted(() => {
      fetchQuestions();
    });

    return { questions, loading, isAuthenticated, formatDate, answerUrl };
  }
});

app.config.compilerOptions.delimiters = ['[[', ']]'];
app.mount('#answers-table-app');
