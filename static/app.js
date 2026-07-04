const themeToggle = document.getElementById('theme-toggle');
const root = document.documentElement;

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const current = document.body.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', next);
    root.setAttribute('data-theme', next);
    themeToggle.textContent = next === 'dark' ? '☀︎' : '☾';
  });
}

async function loadPrayers() {
  const list = document.getElementById('prayer-list');
  const summary = document.getElementById('prayer-summary');
  if (!list && !summary) return;
  const response = await fetch('/api/prayers');
  const prayers = await response.json();
  if (list) {
    list.innerHTML = prayers.length ? prayers.map((prayer) => `
      <article class="journal-item">
        <div class="card-heading">
          <h4>${prayer.title}</h4>
          <span class="chip">${prayer.answered ? 'Answered' : 'Active'}</span>
        </div>
        <p>${prayer.body}</p>
      </article>
    `).join('') : '<p>No prayers yet.</p>';
  }
  if (summary) {
    summary.innerHTML = prayers.length ? `<p>${prayers[0].title}</p>` : '<p>Start a prayer journal entry.</p>';
  }
}

const prayerForm = document.getElementById('prayer-form');
if (prayerForm) {
  prayerForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      title: document.getElementById('prayer-title').value,
      body: document.getElementById('prayer-body').value,
    };
    const response = await fetch('/api/prayers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (response.ok) {
      prayerForm.reset();
      loadPrayers();
    }
  });
}

async function searchBible() {
  const input = document.getElementById('verse-search');
  const results = document.getElementById('reader-results');
  if (!input || !results) return;
  const query = input.value.trim();
  const response = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
  const payload = await response.json();
  results.innerHTML = payload.length ? payload.map((item) => `
    <article class="journal-item">
      <div class="card-heading">
        <h4>${item.reference}</h4>
        <span class="chip">${item.topic}</span>
      </div>
      <p>${item.text}</p>
    </article>
  `).join('') : '<p>No verses found.</p>';
}

const verseSearch = document.getElementById('verse-search');
if (verseSearch) {
  verseSearch.addEventListener('input', () => searchBible());
  verseSearch.addEventListener('keyup', () => searchBible());
}

function addLinkField() {
  const container = document.getElementById('link-blocks');
  if (!container) return;
  const index = container.children.length / 2 + 1;
  const wrapper = document.createElement('div');
  wrapper.className = 'link-block';
  wrapper.innerHTML = `
    <label>Link ${index} title
      <input name="link_title" placeholder="Social">
    </label>
    <label>Link ${index} URL
      <input name="link_url" placeholder="https://example.com">
    </label>
  `;
  container.appendChild(wrapper);
}

function copyShareLink(path) {
  const url = `${window.location.origin}${path}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => {
      window.alert('Share link copied!');
    });
    return;
  }
  window.prompt('Copy this link', url);
}

loadPrayers();
searchBible();
