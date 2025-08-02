document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('survey-app');
  if (!root) return;
  const apiUrl = root.dataset.apiUrl;

  const app = Vue.createApp({
    data() {
      return {
        unanswered: [],
        answers: [],
      };
    },
    mounted() {
      fetch(apiUrl)
        .then((resp) => resp.json())
        .then((data) => {
          this.unanswered = data.unanswered || [];
          this.answers = data.answers || [];
        })
        .then(() => {
          this.$nextTick(() => {
            if (typeof initSortableTables === 'function') {
              initSortableTables('.survey-detail-table');
            }
          });
        });
    },
  });

  app.mount('#survey-app');
});

