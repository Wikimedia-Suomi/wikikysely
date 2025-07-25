function languageDetectSetup(url) {
    const input = document.getElementById('id_text');
    const target = document.getElementById('language-detection');
    if (!input || !target) return;
    let timer = null;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const text = input.value.trim();
        if (!text) {
            target.textContent = '';
            return;
        }
        timer = setTimeout(() => {
            fetch(url + '?q=' + encodeURIComponent(text))
                .then(resp => resp.json())
                .then(data => {
                    if (!data.language) {
                        target.textContent = '';
                    } else {
                        target.textContent = target.dataset.label.replace('%s', data.language);
                    }
                })
                .catch(() => {
                    target.textContent = '';
                });
        }, 300);
    });
}
