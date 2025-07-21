(function() {
  document.addEventListener('DOMContentLoaded', function() {
    var select = document.getElementById('language-select');
    if (!select) return;
    var nextInput = document.getElementById('language-next');
    var re = /^\/(fi|sv|en)(\/|$)/;
    select.addEventListener('change', function() {
      var lang = select.value;
      var path = window.location.pathname;
      var newPath = path;
      var match = re.exec(path);
      if (match) {
        newPath = '/' + lang + path.slice(match[0].length - 1);
      } else {
        newPath = '/' + lang + path;
      }
      if (nextInput) {
        nextInput.value = newPath;
      }
      select.form.submit();
    });
  });
})();

