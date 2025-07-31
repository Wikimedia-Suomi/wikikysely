function initSortableTables(selector, defaultIndex = 0, defaultDirection = 'desc') {
    document.querySelectorAll(selector).forEach(table => {
        const headers = table.querySelectorAll('th');
        if (!headers.length) return;
        const baseTexts = Array.from(headers, h => h.textContent.trim());
        const directions = Array.from(headers, () => null);
        const mobileButtons = [];
        const container = document.createElement('div');
        container.className = 'mobile-sort mb-2';

        function updateLabels() {
            headers.forEach((h, i) => {
                const arrow = directions[i] === 'asc' ? ' \u2191' : directions[i] === 'desc' ? ' \u2193' : '';
                h.textContent = baseTexts[i] + arrow;
                if (mobileButtons[i]) mobileButtons[i].textContent = baseTexts[i] + arrow;
            });
        }

        function sortTable(index, direction) {
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const multiplier = direction === 'asc' ? 1 : -1;
            rows.sort((a, b) => {
                const aText = a.children[index].textContent.trim();
                const bText = b.children[index].textContent.trim();
                const aDate = Date.parse(aText);
                const bDate = Date.parse(bText);
                if (!isNaN(aDate) && !isNaN(bDate)) {
                    return (aDate - bDate) * multiplier;
                }
                const aNum = parseFloat(aText);
                const bNum = parseFloat(bText);
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return (aNum - bNum) * multiplier;
                }
                return aText.localeCompare(bText, undefined, {numeric: true}) * multiplier;
            });
            rows.forEach(r => tbody.appendChild(r));
        }

        function toggleSort(i) {
            const current = directions[i] === 'asc' ? 'desc' : 'asc';
            directions.fill(null);
            directions[i] = current;
            updateLabels();
            sortTable(i, current);
        }

        headers.forEach((header, i) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => toggleSort(i));
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary btn-sm me-2';
            btn.textContent = baseTexts[i];
            btn.addEventListener('click', () => toggleSort(i));
            container.appendChild(btn);
            mobileButtons.push(btn);
        });

        table.parentNode.insertBefore(container, table);

        if (defaultIndex < headers.length) {
            directions[defaultIndex] = defaultDirection;
            updateLabels();
            sortTable(defaultIndex, defaultDirection);
        }
    });
}
if (typeof window !== 'undefined') {
    window.initSortableTables = initSortableTables;
}
