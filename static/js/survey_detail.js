const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = getCookie('csrftoken');
  const app = Vue.createApp({
    data() {
      return {
        unanswered: [],
        answers: [],
        yesLabel: window.surveyYesLabel || 'Yes',
        noLabel: window.surveyNoLabel || 'No'
      };
    },
    methods: {
      fetchData() {
        fetch('/api/unanswered/')
          .then(r => r.json())
          .then(data => { this.unanswered = data.items; });
        fetch('/api/my_answers/')
          .then(r => r.json())
          .then(data => { this.answers = data.items; });
      },
      saveAnswer(item, val) {
        const formData = new FormData();
        formData.append('question_id', item.question_id);
        formData.append('answer', val);
        fetch('/api/answer/save/', {
          method: 'POST',
          headers: {'X-CSRFToken': csrfToken},
          body: formData
        }).then(() => this.fetchData());
      },
      deleteQuestion(item) {
        const formData = new FormData();
        fetch(`/api/question/${item.id}/delete/`, {
          method: 'POST',
          headers: {'X-CSRFToken': csrfToken},
          body: formData
        }).then(() => this.fetchData());
      },
      deleteAnswer(item) {
        const formData = new FormData();
        fetch(`/api/answer/${item.answer_id}/delete/`, {
          method: 'POST',
          headers: {'X-CSRFToken': csrfToken},
          body: formData
        }).then(() => this.fetchData());
      }
    },
    mounted() {
      this.fetchData();
    }
  });
  const vm = app.mount('#survey-app');
});

