const { createApp, ref, computed, onMounted, nextTick } = Vue;

const app = createApp({
  setup() {
    const questions = ref([]);
    const loading = ref(true);
    const root = document.getElementById('survey-detail-app');
    const isAuthenticated = root.dataset.auth === 'true';
    const answerUrlTemplate = root.dataset.answerUrlTemplate;

    function formatDate(str) {
      return str ? str.slice(0, 10) : '';
    }

    function answerUrl(id) {
      const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
      return answerUrlTemplate.replace('0', id) + `?next=${nextParam}`;
    }

    const unansweredQuestions = computed(() =>
      questions.value.filter(q => !q.my_answer)
    );
    const userAnswers = computed(() =>
      questions.value.filter(q => q.my_answer)
    );

    onMounted(() => {
      fetch(window.questionsJsonUrl)
        .then(resp => resp.json())
        .then(data => {
          questions.value = data.questions || [];
        })
        .finally(() => {
          loading.value = false;
          nextTick(() => {
            if (typeof initSortableTables === 'function') {
              initSortableTables('.survey-detail-table');
            }
          });
        });
    });

    return {
      loading,
      isAuthenticated,
      unansweredQuestions,
      userAnswers,
      formatDate,
      answerUrl
    };
  }
});

app.config.compilerOptions.delimiters = ['[[', ']]'];
app.mount('#survey-detail-app');
