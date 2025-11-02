const categoryContainer = document.getElementById('category-list');
const patternContainer = document.getElementById('pattern-list');
const tutorialContainer = document.getElementById('tutorial-content');
const problemTable = document.getElementById('problem-table');
const dataSourceIndicator = document.getElementById('data-source');
const questionForm = document.getElementById('question-form');
const questionInput = document.getElementById('question-input');
const questionResponse = document.getElementById('question-response');
const relatedList = document.getElementById('related-problems');
const refreshButton = document.getElementById('refresh-button');

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

function createTag(text) {
  const span = document.createElement('span');
  span.className = 'tag';
  span.textContent = text;
  return span;
}

function renderCategories(data) {
  categoryContainer.innerHTML = '';
  Object.entries(data).forEach(([topic, info]) => {
    const card = document.createElement('article');
    card.className = 'card';

    const title = document.createElement('h3');
    title.textContent = `${topic} \u2022 ${info.count} problems`;
    card.appendChild(title);

    const difficultiesRow = document.createElement('div');
    difficultiesRow.className = 'meta-row';
    difficultiesRow.textContent = `Difficulty mix: ${Object.entries(info.difficulties)
      .map(([diff, count]) => `${diff} (${count})`)
      .join(', ')}`;
    card.appendChild(difficultiesRow);

    if (info.patterns && Object.keys(info.patterns).length) {
      const patternRow = document.createElement('div');
      patternRow.className = 'tag-row';
      Object.keys(info.patterns)
        .slice(0, 4)
        .forEach((pattern) => {
          patternRow.appendChild(createTag(pattern));
        });
      card.appendChild(patternRow);
    }

    categoryContainer.appendChild(card);
  });
}

function renderPatterns(data) {
  patternContainer.innerHTML = '';
  Object.entries(data).forEach(([pattern, info]) => {
    const card = document.createElement('article');
    card.className = 'card pattern-card';

    const title = document.createElement('h3');
    title.textContent = pattern;
    card.appendChild(title);

    const summary = document.createElement('p');
    summary.className = 'pattern-details';
    summary.innerHTML = `
      <strong>${info.count}</strong> problems • Dominant topics: ${Object.keys(info.topics)
        .slice(0, 3)
        .join(', ') || '—'}`;
    card.appendChild(summary);

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.textContent = 'Show examples';
    card.appendChild(toggle);

    const details = document.createElement('div');
    details.className = 'pattern-details';
    details.hidden = true;
    details.innerHTML = `
      <p>${info.why_it_matters || ''}</p>
      <ul>
        ${info.examples
          .map(
            (example) => `
              <li>
                <a class="problem-link" href="${example.url}" target="_blank" rel="noopener">${example.title}</a>
                <span>(${example.difficulty} • ${example.topic})</span>
              </li>
            `
          )
          .join('')}
      </ul>
    `;
    card.appendChild(details);

    toggle.addEventListener('click', () => {
      const hidden = details.hidden;
      details.hidden = !hidden;
      toggle.textContent = hidden ? 'Hide examples' : 'Show examples';
    });

    patternContainer.appendChild(card);
  });
}

function renderTutorial(tutorial) {
  tutorialContainer.innerHTML = '';

  const highlights = document.createElement('div');
  highlights.className = 'tutorial-step';
  highlights.innerHTML = `
    <h3>Category highlights</h3>
    <ul>
      ${tutorial.category_highlights
        .map(
          (item) => `
            <li>
              <strong>${item.topic}</strong> — ${item.count} problems · Key patterns: ${item.key_patterns.join(', ') || 'varied'}
            </li>
          `
        )
        .join('')}
    </ul>
  `;
  tutorialContainer.appendChild(highlights);

  const patternSpotlight = document.createElement('div');
  patternSpotlight.className = 'tutorial-step';
  patternSpotlight.innerHTML = `
    <h3>Pattern spotlights</h3>
    <ul>
      ${tutorial.pattern_spotlight
        .map(
          (item) => `
            <li>
              <strong>${item.pattern}</strong> — ${item.why_it_matters} Top topics: ${item.top_topics.join(', ') || 'varied'}
            </li>
          `
        )
        .join('')}
    </ul>
  `;
  tutorialContainer.appendChild(patternSpotlight);

  tutorial.study_plan.forEach((segment) => {
    const step = document.createElement('div');
    step.className = 'tutorial-step';
    step.innerHTML = `
      <h3>${segment.title}</h3>
      <ul>${segment.steps.map((stepItem) => `<li>${stepItem}</li>`).join('')}</ul>
    `;
    tutorialContainer.appendChild(step);
  });
}

function renderProblems(problems) {
  problemTable.innerHTML = '';
  problems.forEach((problem) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><a class="problem-link" href="${problem.url}" target="_blank" rel="noopener">${problem.title}</a></td>
      <td>${problem.topic}</td>
      <td>${problem.patterns.join(', ')}</td>
      <td>${problem.difficulty}</td>
    `;
    problemTable.appendChild(row);
  });
}

function renderMeta(meta) {
  if (!meta) {
    dataSourceIndicator.textContent = '';
    return;
  }

  const { source, last_refreshed: lastRefreshed } = meta;
  const parts = [];
  if (source) {
    parts.push(`Data source: ${source}`);
  }
  if (lastRefreshed) {
    const refreshedDate = new Date(lastRefreshed);
    if (!Number.isNaN(refreshedDate.valueOf())) {
      parts.push(`Last refreshed: ${refreshedDate.toLocaleString()}`);
    }
  }
  dataSourceIndicator.textContent = parts.join(' • ');
}

async function hydrate() {
  try {
    const [meta, categoryData, patternData, tutorialData, problemsData] = await Promise.all([
      fetchJson('/api/meta'),
      fetchJson('/api/categories'),
      fetchJson('/api/patterns'),
      fetchJson('/api/tutorial'),
      fetchJson('/api/problems'),
    ]);

    renderMeta(meta);
    renderCategories(categoryData.categories);
    renderPatterns(patternData.patterns);
    renderTutorial(tutorialData.tutorial);
    renderProblems(problemsData.problems);
  } catch (error) {
    console.error('Failed to load data', error);
    alert('Unable to load insights. Please ensure the Flask server is running.');
  }
}

questionForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) {
    return;
  }

  questionResponse.textContent = 'Thinking...';
  relatedList.innerHTML = '';

  try {
    const { answer, related_problems: related } = await fetchJson('/api/questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    questionResponse.textContent = answer;
    if (related.length) {
      relatedList.innerHTML = related
        .map(
          (item) => `
            <li>
              <a class="problem-link" href="${item.url}" target="_blank" rel="noopener">${item.title}</a>
              <span>${item.topic} • ${item.difficulty}</span>
            </li>
          `
        )
        .join('');
    }
  } catch (error) {
    console.error('Question request failed', error);
    questionResponse.textContent = 'I could not answer right now. Please try again.';
  }
});

refreshButton.addEventListener('click', async () => {
  refreshButton.disabled = true;
  const originalLabel = refreshButton.textContent;
  refreshButton.textContent = 'Refreshing...';

  try {
    await fetchJson('/api/refresh', { method: 'POST' });
    await hydrate();
  } catch (error) {
    console.error('Failed to refresh data', error);
    alert('Refresh failed. Check the leetcode-mcp-server connection or try again.');
  } finally {
    refreshButton.textContent = originalLabel;
    refreshButton.disabled = false;
  }
});

document.addEventListener('DOMContentLoaded', hydrate);
