const { createApp, ref, computed, onMounted, nextTick } = Vue;

if (typeof window.unansweredCount === 'number') {
  window.unansweredCount = ref(window.unansweredCount);
}

const app = createApp({
  setup() {
    const questions = ref([]);
    const loading = ref(true);
    const root = document.getElementById('survey-detail-app');
    const isAuthenticated = root.dataset.auth === 'true';
    const answerUrlTemplate = root.dataset.answerUrlTemplate;
    const answerEditUrlTemplate = root.dataset.answerEditUrlTemplate;
    const answerDeleteUrlTemplate = root.dataset.answerDeleteUrlTemplate;
    const isRunning = root.dataset.running === 'true';
    const answerSurveyUrl = root.dataset.answerSurveyUrl;

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

    function getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function fetchQuestions() {
      loading.value = true;
      fetch(window.questionsJsonUrl)
        .then(resp => resp.json())
        .then(data => {
          questions.value = data.questions || [];
          if (window.unansweredCount && 'value' in window.unansweredCount) {
            window.unansweredCount.value = questions.value.filter(q => !q.my_answer).length;
          }
        })
        .finally(() => {
          loading.value = false;
          nextTick(() => {
            if (typeof initSortableTables === 'function') {
              initSortableTables('.survey-detail-table');
            }
          });
        });
    }

    function updateAnswer(a) {
      const url = answerEditUrlTemplate.replace('0', a.my_answer_id);
      const formData = new FormData();
      formData.append('answer', a.my_answer);
      formData.append('question_id', a.id);
      fetch(url, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        },
        body: formData
      }).then(resp => resp.ok ? resp.json() : Promise.reject())
        .then(() => fetchQuestions())
        .catch(() => window.location.reload());
    }

    function deleteAnswer(a) {
      const url = answerDeleteUrlTemplate.replace('0', a.my_answer_id);
      fetch(url, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        }
      }).then(resp => resp.ok ? resp.json() : Promise.reject())
        .then(() => fetchQuestions())
        .catch(() => window.location.reload());
    }

    function deleteUrl(id) {
      return answerDeleteUrlTemplate.replace('0', id);
    }

    onMounted(fetchQuestions);

    return {
      loading,
      isAuthenticated,
      isRunning,
      questions,
      answerSurveyUrl,
      unansweredQuestions,
      userAnswers,
      formatDate,
      answerUrl,
      updateAnswer,
      deleteAnswer,
      deleteUrl
    };
  }
});

app.config.compilerOptions.delimiters = ['[[', ']]'];
app.mount('#survey-detail-app');

const navRoot = document.getElementById('nav-answer-app');
if (navRoot) {
  const navApp = createApp({
    setup() {
      const count = window.unansweredCount;
      const auth = navRoot.dataset.auth === 'true';
      const answerUrl = navRoot.dataset.answerUrl;
      const isActive = navRoot.dataset.isActive === 'true';
      return { count, auth, answerUrl, isActive };
    }
  });
  navApp.config.compilerOptions.delimiters = ['[[', ']]'];
  navApp.mount('#nav-answer-app');
}
