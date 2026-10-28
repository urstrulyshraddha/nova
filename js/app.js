let currentStories = [];

async function init() {
  // Trigger typewriter effect immediately
  typeWriter("Shraddha", "typewriterText", 90);

  try {
    const res = await fetch('data/briefing.json?nocache=' + Date.now());
    if (!res.ok) throw new Error('Failed to load dispatch.');
    const data = await res.json();

    document.getElementById('editionDate').textContent = data.edition_date || 'Live';
    document.getElementById('lastUpdated').textContent = `Sync: ${new Date(data.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

    // Render Daily Quote
    if (data.daily_quote) {
      document.getElementById('quoteText').textContent = `“${data.daily_quote.quote}”`;
      const metaText = data.daily_quote.source
        ? `${data.daily_quote.author} (${data.daily_quote.source})`
        : data.daily_quote.author;
      document.getElementById('quoteMeta').textContent = `— ${metaText}`;
    }

    currentStories = data.stories || [];
    renderStories(currentStories);
  } catch (err) {
    document.getElementById('feedCarousel').innerHTML = `
      <div style="padding: 2rem; color: var(--color-muted); font-family: var(--font-mono); font-size: 0.8rem;">
        [!] Unable to load briefing data.
      </div>`;
  }
}

function typeWriter(text, elementId, speed = 80) {
  const el = document.getElementById(elementId);
  el.textContent = '';
  let i = 0;
  function step() {
    if (i < text.length) {
      el.textContent += text.charAt(i);
      i++;
      setTimeout(step, speed);
    }
  }
  step();
}

function renderStories(stories) {
  const container = document.getElementById('feedCarousel');
  if (stories.length === 0) {
    container.innerHTML = `
      <div style="padding: 2rem; color: var(--color-muted); font-family: var(--font-mono); font-size: 0.8rem;">
        No active items in this category.
      </div>`;
    return;
  }

  container.innerHTML = stories.map(story => `
    <article class="story-card">
      <div class="card-top">
        <div class="card-pill-bar">
          <span class="category-tag">${escapeHtml(story.category)}</span>
          <span class="card-source">${escapeHtml(story.source_name)}</span>
        </div>
        <a class="card-title" href="${escapeHtml(story.source_url)}" target="_blank" rel="noopener noreferrer">
          ${escapeHtml(story.title)}
        </a>
        <p class="card-summary">${escapeHtml(story.summary)}</p>
      </div>

      <div class="card-bottom">
        ${story.why_it_matters ? `
          <div class="why-block">
            <span class="why-label">SIGNIFICANCE</span>
            ${escapeHtml(story.why_it_matters)}
          </div>
        ` : ''}
        <div class="card-action-bar">
          <span class="time-stamp">${timeAgo(story.published_at)}</span>
          <a href="${escapeHtml(story.source_url)}" target="_blank" rel="noopener noreferrer" class="read-btn">Read ↗</a>
        </div>
      </div>
    </article>
  `).join('');

  container.scrollLeft = 0;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function timeAgo(dateString) {
  const diff = (new Date() - new Date(dateString)) / 1000;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

document.getElementById('categoryNav').addEventListener('click', (e) => {
  if (!e.target.classList.contains('nav-pill')) return;

  document.querySelectorAll('.nav-pill').forEach(btn => btn.classList.remove('active'));
  e.target.classList.add('active');

  const cat = e.target.getAttribute('data-cat');
  if (cat === 'all') {
    renderStories(currentStories);
  } else {
    renderStories(currentStories.filter(s => s.category.toLowerCase() === cat.toLowerCase()));
  }
});

document.addEventListener('DOMContentLoaded', init);
