const { createApp, ref, computed, onMounted, nextTick } = Vue;

if (typeof window.unansweredCount === 'number') {
  window.unansweredCount = ref(window.unansweredCount);
}

const app = createApp({
  setup() {
    const questions = ref([]);
    const loading = ref(true);
    const currentQuestion = ref(null);
    const root = document.getElementById('survey-detail-app');
    const isAuthenticated = root.dataset.auth === 'true';
    const answerUrlTemplate = root.dataset.answerUrlTemplate;
    const answerApiUrlTemplate = root.dataset.answerApiUrlTemplate;
    const answerDeleteUrlTemplate = root.dataset.answerDeleteUrlTemplate;
    const answerDeleteApiUrlTemplate = root.dataset.answerDeleteApiUrlTemplate;
    const questionEditUrlTemplate = root.dataset.questionEditUrlTemplate;
    const isRunning = root.dataset.running === 'true';
    const answerSurveyUrl = root.dataset.answerSurveyUrl;

    function formatDate(str) {
      return str ? str.slice(0, 10) : '';
    }

    function answerUrl(id) {
      const nextParam = encodeURIComponent(window.location.pathname + window.location.search);
      return answerUrlTemplate.replace('0', id) + `?next=${nextParam}`;
    }

    function answerPath(id) {
      return answerUrlTemplate.replace('0', id);
    }

    function questionEditUrl(id) {
      return questionEditUrlTemplate.replace('0', id);
    }

    const unansweredQuestions = computed(() =>
      questions.value.filter(q => !q.my_answer)
    );
    const userAnswers = computed(() =>
      questions.value.filter(q => q.my_answer)
    );
    const otherUserAnswers = computed(() =>
      questions.value.filter(q => q.my_answer && (!currentQuestion.value || q.id !== currentQuestion.value.id))
    );

    function getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function fetchQuestions() {
      const currentId = currentQuestion.value ? currentQuestion.value.id : null;
      loading.value = true;
      return fetch(window.questionsJsonUrl)
        .then(resp => resp.json())
        .then(data => {
          questions.value = data.questions || [];
          if (currentId) {
            currentQuestion.value = questions.value.find(q => q.id === currentId) || null;
          }
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
      const url = answerApiUrlTemplate.replace('0', a.id);
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
      const url = answerDeleteApiUrlTemplate.replace('0', a.my_answer_id);
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

    function openQuestion(q, push = true) {
      currentQuestion.value = q;
      if (push) {
        window.history.pushState({ questionId: q.id }, '', answerPath(q.id));
      }
    }

    function closeQuestion(push = true) {
      currentQuestion.value = null;
      if (push) {
        window.history.pushState({}, '', answerSurveyUrl);
      }
    }

    function submitAnswer(ans) {
      if (!currentQuestion.value) return;
      const prevId = currentQuestion.value.id;
      const url = answerApiUrlTemplate.replace('0', prevId);
      const formData = new FormData();
      formData.append('answer', ans);
      formData.append('question_id', prevId);
      closeQuestion(false);
      fetch(url, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        },
        body: formData
      }).then(resp => resp.ok ? resp.json() : Promise.reject())
        .then(() => fetchQuestions())
        .then(() => {
          const next = unansweredQuestions.value.find(q => q.id !== prevId);
          if (next) {
            openQuestion(next);
          } else {
            closeQuestion();
          }
        })
        .catch(() => window.location.reload());
    }

    function handlePopState() {
      const m = window.location.pathname.match(/question\/(\d+)/);
      if (m) {
        const id = parseInt(m[1]);
        const q = questions.value.find(q => q.id === id);
        if (q) {
          openQuestion(q, false);
        }
      } else {
        closeQuestion(false);
      }
    }

    onMounted(() => {
      fetchQuestions().then(() => {
        handlePopState();
      });
      window.addEventListener('popstate', handlePopState);
    });

    return {
      loading,
      isAuthenticated,
      isRunning,
      questions,
      currentQuestion,
      answerSurveyUrl,
      questionEditUrl,
      unansweredQuestions,
      userAnswers,
      otherUserAnswers,
      formatDate,
      answerUrl,
      updateAnswer,
      deleteAnswer,
      deleteUrl,
      openQuestion,
      closeQuestion,
      submitAnswer
    };
  }
});

app.config.compilerOptions.delimiters = ['[[', ']]'];
const surveyApp = app.mount('#survey-detail-app');

window.openFirstQuestion = () => {
  if (surveyApp && surveyApp.unansweredQuestions.length) {
    surveyApp.openQuestion(surveyApp.unansweredQuestions[0]);
  } else if (surveyApp && surveyApp.answerSurveyUrl) {
    window.location.href = surveyApp.answerSurveyUrl;
  }
};

const navRoot = document.getElementById('nav-answer-app');
if (navRoot) {
  const navApp = createApp({
    setup() {
      const count = window.unansweredCount;
      const auth = navRoot.dataset.auth === 'true';
      const answerUrl = navRoot.dataset.answerUrl;
      const isActive = navRoot.dataset.isActive === 'true';
      function openFirstQuestion() {
        if (typeof window.openFirstQuestion === 'function') {
          window.openFirstQuestion();
        } else {
          window.location.href = answerUrl;
        }
      }
      return { count, auth, answerUrl, isActive, openFirstQuestion };
    }
  });
  navApp.config.compilerOptions.delimiters = ['[[', ']]'];
  navApp.mount('#nav-answer-app');
}
