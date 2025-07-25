function suggestionsSetup(url) {
    const input = document.getElementById('id_text');
    const container = document.getElementById('suggestions');
    if (!input || !container) return;
    let timer = null;
    input.addEventListener('input', () => {
        clearTimeout(timer);
        const text = input.value.trim();
        if (!text) {
            container.innerHTML = '';
            return;
        }
        timer = setTimeout(() => {
            fetch(url + '?q=' + encodeURIComponent(text))
                .then(resp => resp.json())
                .then(data => {
                    container.innerHTML = '';
                    if (!data.results || !data.results.length) {
                        return;
                    }
                    const heading = document.createElement('h3');
                    heading.textContent = container.dataset.heading;
                    container.appendChild(heading);
                    const ul = document.createElement('ul');
                    ul.className = 'list-group';
                    data.results.forEach(item => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item';
                        li.textContent = item.text;
                        ul.appendChild(li);
                    });
                    container.appendChild(ul);
                })
                .catch(() => {
                    container.innerHTML = '';
                });
        }, 300);
    });
}
