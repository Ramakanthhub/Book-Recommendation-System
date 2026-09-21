/**
 * Student-Centric Book Recommendation System - Client Logic
 */

// --- 1. Theme Management (Dark / Light Mode) ---
function initTheme() {
  const savedTheme = localStorage.getItem('edu_book_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  const toggleBtn = document.getElementById('themeToggleBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('edu_book_theme', newTheme);
      updateThemeIcon(newTheme);
    });
  }
}

function updateThemeIcon(theme) {
  const toggleBtn = document.getElementById('themeToggleBtn');
  if (toggleBtn) {
    toggleBtn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
    toggleBtn.setAttribute('title', theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
  }
}

// --- 2. Study Shelf (LocalStorage Persistence) ---
const SHELF_STORAGE_KEY = 'edu_study_shelf_v1';

function getShelf() {
  try {
    return JSON.parse(localStorage.getItem(SHELF_STORAGE_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function saveShelf(shelf) {
  localStorage.setItem(SHELF_STORAGE_KEY, JSON.stringify(shelf));
  updateShelfBadge();
}

function isBookInShelf(title) {
  const shelf = getShelf();
  return shelf.some(b => b.title.toLowerCase() === title.toLowerCase());
}

function toggleShelf(book) {
  let shelf = getShelf();
  const index = shelf.findIndex(b => b.title.toLowerCase() === book.title.toLowerCase());
  
  if (index > -1) {
    shelf.splice(index, 1);
    saveShelf(shelf);
    showToast(`Removed "${book.title}" from Study Shelf`);
    updateBookmarkButtons();
    return false;
  } else {
    shelf.push({
      title: book.title,
      author: book.author || 'Unknown Author',
      image: book.image || '',
      rating: book.rating || 'N/A',
      votes: book.votes || '0',
      status: 'want_to_study',
      addedAt: new Date().toISOString()
    });
    saveShelf(shelf);
    showToast(`Added "${book.title}" to Study Shelf! 📚`);
    updateBookmarkButtons();
    return true;
  }
}

function updateShelfBadge() {
  const shelf = getShelf();
  const badge = document.getElementById('shelfCountBadge');
  if (badge) {
    badge.textContent = shelf.length;
    badge.style.display = shelf.length > 0 ? 'inline-block' : 'none';
  }
}

function updateBookmarkButtons() {
  const buttons = document.querySelectorAll('.bookmark-btn');
  buttons.forEach(btn => {
    const title = btn.getAttribute('data-title');
    if (title && isBookInShelf(title)) {
      btn.classList.add('saved');
      btn.innerHTML = '★';
      btn.setAttribute('title', 'Saved in Study Shelf');
    } else {
      btn.classList.remove('saved');
      btn.innerHTML = '☆';
      btn.setAttribute('title', 'Add to Study Shelf');
    }
  });
}

// --- 3. Autocomplete Search Component ---
function initAutocomplete(inputId, dropdownId, formId) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  const form = document.getElementById(formId);
  if (!input || !dropdown) return;

  let debounceTimer = null;
  let currentSelection = -1;

  input.addEventListener('input', () => {
    const query = input.value.trim();
    clearTimeout(debounceTimer);
    if (query.length < 2) {
      dropdown.classList.remove('active');
      dropdown.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(() => {
      fetch(`/api/search_suggestions?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          dropdown.innerHTML = '';
          currentSelection = -1;
          if (data && data.length > 0) {
            data.forEach(item => {
              const div = document.createElement('div');
              div.className = 'autocomplete-item';
              div.innerHTML = `
                <span>${highlightMatch(item.title, query)}</span>
                <span class="autocomplete-badge">${item.recommendable ? 'Verified Vector' : 'Catalog'}</span>
              `;
              div.addEventListener('click', () => {
                input.value = item.title;
                dropdown.classList.remove('active');
                if (form) form.submit();
              });
              dropdown.appendChild(div);
            });
            dropdown.classList.add('active');
          } else {
            dropdown.classList.remove('active');
          }
        })
        .catch(err => {
          console.error('Autocomplete error:', err);
          dropdown.classList.remove('active');
        });
    }, 150);
  });

  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.autocomplete-item');
    if (!items.length || !dropdown.classList.contains('active')) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      currentSelection = (currentSelection + 1) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      currentSelection = (currentSelection - 1 + items.length) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'Enter') {
      if (currentSelection >= 0 && currentSelection < items.length) {
        e.preventDefault();
        items[currentSelection].click();
      }
    } else if (e.key === 'Escape') {
      dropdown.classList.remove('active');
    }
  });

  function updateActiveItem(items) {
    items.forEach((it, idx) => {
      it.classList.toggle('selected', idx === currentSelection);
      if (idx === currentSelection) {
        it.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.remove('active');
    }
  });
}

function highlightMatch(text, query) {
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  const before = text.slice(0, idx);
  const match = text.slice(idx, idx + query.length);
  const after = text.slice(idx + query.length);
  return `${before}<strong style="color:var(--accent-primary);">${match}</strong>${after}`;
}

// --- 4. Quick Search Chips ---
function initQuickChips() {
  const chips = document.querySelectorAll('.chip-btn');
  const searchInput = document.getElementById('heroSearchInput') || document.getElementById('book_input');
  const form = searchInput ? searchInput.closest('form') : null;

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const book = chip.getAttribute('data-book');
      if (searchInput && book) {
        searchInput.value = book;
        if (form) form.submit();
      }
    });
  });
}

// --- 5. Category Tabs Filter (Home Page) ---
function initCategoryTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  const cards = document.querySelectorAll('.book-card');
  if (!tabs.length || !cards.length) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const category = tab.getAttribute('data-category');
      cards.forEach(card => {
        const cardCats = (card.getAttribute('data-categories') || 'all').split(' ');
        if (category === 'all' || cardCats.includes(category)) {
          card.style.display = 'flex';
          card.style.opacity = '1';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

// --- 6. Toast System ---
function showToast(message) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>📖</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2800);
}

// --- 7. Fallback Image Handler ---
function handleImageFallback(img, title) {
  const initials = (title || 'Book').split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
  const svgData = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="150" height="220" viewBox="0 0 150 220"><rect width="150" height="220" fill="%231e293b"/><text x="50%" y="45%" fill="%236366f1" font-size="28" font-family="sans-serif" font-weight="bold" text-anchor="middle">${initials}</text><text x="50%" y="65%" fill="%2394a3b8" font-size="10" font-family="sans-serif" text-anchor="middle">Academic Pick</text></svg>`;
  img.src = svgData;
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initAutocomplete('heroSearchInput', 'searchDropdown', 'searchForm');
  initAutocomplete('book_input', 'searchDropdown', 'recommendForm');
  initQuickChips();
  initCategoryTabs();
  updateShelfBadge();
  updateBookmarkButtons();
  initPomodoroTimer();

  // Attach bookmark clicks globally
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.bookmark-btn');
    if (btn) {
      e.preventDefault();
      const book = {
        title: btn.getAttribute('data-title') || '',
        author: btn.getAttribute('data-author') || '',
        image: btn.getAttribute('data-image') || '',
        rating: btn.getAttribute('data-rating') || '',
        votes: btn.getAttribute('data-votes') || ''
      };
      toggleShelf(book);
      return;
    }

    // Attach Cite Book clicks
    const citeBtn = e.target.closest('.cite-btn');
    if (citeBtn) {
      e.preventDefault();
      const title = citeBtn.getAttribute('data-title');
      const author = citeBtn.getAttribute('data-author');
      const year = citeBtn.getAttribute('data-year');
      const publisher = citeBtn.getAttribute('data-publisher');
      openCitationModal(title, author, year, publisher);
      return;
    }

    // Attach AI Brief clicks
    const aiBtn = e.target.closest('.btn-ai-brief');
    if (aiBtn) {
      e.preventDefault();
      const title = aiBtn.getAttribute('data-title');
      const author = aiBtn.getAttribute('data-author');
      openAiBriefModal(title, author);
      return;
    }

    // Attach Flashcards clicks
    const flashBtn = e.target.closest('.btn-flashcards');
    if (flashBtn) {
      e.preventDefault();
      const title = flashBtn.getAttribute('data-title');
      const author = flashBtn.getAttribute('data-author');
      openFlashcardsModal(title, author);
      return;
    }
  });
});

// --- 8. Academic Citation Generator (APA, MLA, Chicago) ---
let currentCitationData = { title: '', author: '', year: '2020', publisher: 'Academic Press' };

function generateCitation(format, book) {
  const author = book.author || 'Author, Unknown';
  const title = book.title || 'Book Title';
  const year = book.year || 'n.d.';
  const publisher = book.publisher || 'Publishing House';

  let authorParts = author.trim().split(' ');
  let formattedAuthor = author;
  if (authorParts.length >= 2) {
    const lastName = authorParts[authorParts.length - 1];
    const firstInitials = authorParts.slice(0, -1).join(' ');
    formattedAuthor = `${lastName}, ${firstInitials}`;
  }

  if (format === 'apa') {
    return `${formattedAuthor} (${year}). ${title}. ${publisher}.`;
  } else if (format === 'mla') {
    return `${formattedAuthor}. "${title}." ${publisher}, ${year}.`;
  } else if (format === 'chicago') {
    return `${formattedAuthor}. ${title}. ${publisher}, ${year}.`;
  }
  return `${author}. (${year}). ${title}. ${publisher}.`;
}

function openCitationModal(title, author, year, publisher) {
  currentCitationData = {
    title: title || 'Selected Book',
    author: author || 'Unknown Author',
    year: year || '2004',
    publisher: publisher || 'Publisher'
  };

  let modal = document.getElementById('citationModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'citationModal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-card">
        <button class="modal-close" onclick="closeCitationModal()">✕</button>
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
          <span style="font-size: 1.5rem;">📝</span>
          <h2 style="font-size: 1.35rem; margin: 0;">Academic Citation Generator</h2>
        </div>
        <p style="color: var(--text-secondary); font-size: 0.88rem;">
          Instant citations formatted for research papers, reading logs, and course bibliographies.
        </p>

        <div class="citation-tabs">
          <button class="citation-tab-btn active" data-format="apa">APA 7th</button>
          <button class="citation-tab-btn" data-format="mla">MLA 9th</button>
          <button class="citation-tab-btn" data-format="chicago">Chicago 17th</button>
        </div>

        <div id="citationOutput" class="citation-box"></div>

        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.8rem;">
          <button id="copyCitationBtn" class="search-btn" style="position: static; padding: 0.65rem 1.4rem;">
            <span>📋</span> Copy Citation
          </button>
          <a id="openLibraryLink" href="#" target="_blank" rel="noopener" class="btn-secondary" style="font-size: 0.85rem;">
            <span>📖</span> Open Library Record ↗
          </a>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelectorAll('.citation-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        modal.querySelectorAll('.citation-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const format = btn.getAttribute('data-format');
        document.getElementById('citationOutput').textContent = generateCitation(format, currentCitationData);
      });
    });

    document.getElementById('copyCitationBtn').addEventListener('click', () => {
      const text = document.getElementById('citationOutput').textContent;
      navigator.clipboard.writeText(text).then(() => {
        showToast('Citation copied to clipboard! 📋');
      }).catch(() => {
        showToast('Citation copied!');
      });
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeCitationModal();
    });
  }

  document.getElementById('citationOutput').textContent = generateCitation('apa', currentCitationData);
  const olLink = document.getElementById('openLibraryLink');
  if (olLink) {
    olLink.href = `https://openlibrary.org/search?q=${encodeURIComponent(currentCitationData.title)}`;
  }
  modal.classList.add('active');
}

function closeCitationModal() {
  const modal = document.getElementById('citationModal');
  if (modal) modal.classList.remove('active');
}

// --- 9. Batch Add Whole Track to Study Shelf ---
function addTrackToShelf(trackTitle, booksArray) {
  let shelf = getShelf();
  let addedCount = 0;
  booksArray.forEach(b => {
    if (!shelf.some(existing => existing.title.toLowerCase() === b.title.toLowerCase())) {
      shelf.push({
        title: b.title,
        author: b.author || 'Academic Author',
        image: b.image || '',
        rating: b.rating || '4.8',
        votes: b.votes || '250',
        status: 'want_to_study',
        notes: `From Syllabus Track: ${trackTitle}`,
        progress: 0,
        addedAt: new Date().toISOString()
      });
      addedCount++;
    }
  });
  saveShelf(shelf);
  updateBookmarkButtons();
  showToast(`Added ${addedCount} books from "${trackTitle}" to your Study Shelf! 🎓`);
}

// --- 10. AI Concept Brief Modal ---
function openAiBriefModal(title, author) {
  let modal = document.getElementById('aiBriefModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'aiBriefModal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-card" style="max-width: 680px; max-height: 88vh; overflow-y: auto;">
        <button class="modal-close" onclick="closeAiBriefModal()">✕</button>
        <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.25rem;">
          <span class="ai-badge">⚡ AI Concept Brief</span>
          <span id="aiDifficultyBadge" class="track-level-badge badge-intermediate">Intermediate</span>
        </div>
        
        <h2 id="aiBookTitle" style="font-size: 1.45rem; margin-top: 0.4rem; line-height: 1.3;">Book Title</h2>
        <p id="aiBookAuthor" style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.25rem;">by Author</p>

        <!-- Executive Thesis -->
        <div style="background: var(--bg-primary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1.15rem; margin-bottom: 1.25rem;">
          <div style="font-size: 0.78rem; font-weight: 800; color: var(--accent-primary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;">
            📌 Core Thesis & Executive Summary
          </div>
          <p id="aiCoreThesis" style="font-size: 0.92rem; color: var(--text-primary); line-height: 1.55; margin: 0;"></p>
        </div>

        <!-- High-Yield Concepts -->
        <div style="margin-bottom: 1.25rem;">
          <div style="font-size: 0.8rem; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
            🎯 High-Yield Syllabus Concepts
          </div>
          <div id="aiConceptList" class="concept-grid"></div>
        </div>

        <!-- Prerequisites & Relevance -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.5rem;">
          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem;">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.2rem;">PREREQUISITES</div>
            <div id="aiPrereqs" style="font-size: 0.85rem; color: var(--text-primary);">None</div>
          </div>
          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem;">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.2rem;">RELEVANT COURSES</div>
            <div id="aiCourses" style="font-size: 0.85rem; color: var(--text-primary);">General Humanities</div>
          </div>
        </div>

        <!-- 1-Click Study Prompts -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div style="font-size: 0.8rem; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em;">
              🤖 1-Click AI Study Prompts (ChatGPT / Gemini / Claude)
            </div>
          </div>
          <div id="aiPromptsContainer"></div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeAiBriefModal();
    });
  }

  // Populate loading state
  document.getElementById('aiBookTitle').textContent = title;
  document.getElementById('aiBookAuthor').textContent = `by ${author || 'Academic Author'}`;
  document.getElementById('aiCoreThesis').textContent = 'Analyzing and synthesizing syllabus brief with AI...';
  document.getElementById('aiConceptList').innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">Loading concepts...</div>';
  document.getElementById('aiPromptsContainer').innerHTML = '';
  modal.classList.add('active');

  fetch(`/api/ai_brief/${encodeURIComponent(title)}?author=${encodeURIComponent(author || '')}`)
    .then(res => res.json())
    .then(data => {
      document.getElementById('aiCoreThesis').textContent = data.core_thesis;
      document.getElementById('aiPrereqs').textContent = data.prerequisites;
      document.getElementById('aiCourses').textContent = data.course_relevance;
      document.getElementById('aiDifficultyBadge').textContent = data.difficulty || 'Intermediate';

      const conceptsContainer = document.getElementById('aiConceptList');
      conceptsContainer.innerHTML = '';
      (data.key_concepts || []).forEach(c => {
        const div = document.createElement('div');
        div.className = 'concept-item';
        div.textContent = c;
        conceptsContainer.appendChild(div);
      });

      const promptsContainer = document.getElementById('aiPromptsContainer');
      promptsContainer.innerHTML = '';
      (data.ai_prompts || []).forEach(p => {
        const card = document.createElement('div');
        card.className = 'prompt-card';
        card.innerHTML = `
          <div class="prompt-text">"${escapeHtml(p)}"</div>
          <button class="prompt-copy-btn"><span>📋</span> Copy Prompt</button>
        `;
        card.querySelector('.prompt-copy-btn').addEventListener('click', () => {
          navigator.clipboard.writeText(p).then(() => {
            showToast('Study prompt copied for ChatGPT/Gemini! 🤖');
          }).catch(() => {
            showToast('Prompt copied!');
          });
        });
        promptsContainer.appendChild(card);
      });
    })
    .catch(err => {
      console.error('Error fetching AI brief:', err);
      document.getElementById('aiCoreThesis').textContent = 'Error loading AI Concept Brief. Please try again.';
    });
}

function closeAiBriefModal() {
  const modal = document.getElementById('aiBriefModal');
  if (modal) modal.classList.remove('active');
}

// --- 11. Pomodoro Focus Timer (25 min study / 5 min break) ---
let pomodoroSeconds = 25 * 60;
let pomodoroInterval = null;
let isPomodoroRunning = false;

function initPomodoroTimer() {
  const display = document.getElementById('pomodoroTime');
  const toggleBtn = document.getElementById('pomodoroToggleBtn');
  const resetBtn = document.getElementById('pomodoroResetBtn');
  if (!display || !toggleBtn) return;

  // Restore session time if exists
  const savedSec = sessionStorage.getItem('edu_pomodoro_sec');
  if (savedSec !== null) {
    pomodoroSeconds = parseInt(savedSec);
  }
  updatePomodoroDisplay();

  toggleBtn.addEventListener('click', () => {
    if (isPomodoroRunning) {
      pausePomodoro();
    } else {
      startPomodoro();
    }
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      pausePomodoro();
      pomodoroSeconds = 25 * 60;
      sessionStorage.setItem('edu_pomodoro_sec', pomodoroSeconds);
      updatePomodoroDisplay();
      showToast('Pomodoro reset to 25:00 ⏱️');
    });
  }
}

function updatePomodoroDisplay() {
  const display = document.getElementById('pomodoroTime');
  if (!display) return;
  const mins = Math.floor(pomodoroSeconds / 60);
  const secs = pomodoroSeconds % 60;
  display.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function startPomodoro() {
  const toggleBtn = document.getElementById('pomodoroToggleBtn');
  isPomodoroRunning = true;
  if (toggleBtn) toggleBtn.textContent = '⏸';
  showToast('Study timer started (25 mins focus) ⏱️');

  pomodoroInterval = setInterval(() => {
    if (pomodoroSeconds > 0) {
      pomodoroSeconds--;
      sessionStorage.setItem('edu_pomodoro_sec', pomodoroSeconds);
      updatePomodoroDisplay();
    } else {
      pausePomodoro();
      pomodoroSeconds = 5 * 60; // 5 min break
      sessionStorage.setItem('edu_pomodoro_sec', pomodoroSeconds);
      updatePomodoroDisplay();
      showToast('🎉 Focus block completed! Take a 5-minute break.');
    }
  }, 1000);
}

function pausePomodoro() {
  const toggleBtn = document.getElementById('pomodoroToggleBtn');
  isPomodoroRunning = false;
  if (toggleBtn) toggleBtn.textContent = '▶';
  clearInterval(pomodoroInterval);
}

// --- 12. 3D Active-Recall Flashcards Modal ---
let flashcardDeck = [];
let currentCardIndex = 0;

function openFlashcardsModal(title, author) {
  let modal = document.getElementById('flashcardsModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'flashcardsModal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-card" style="max-width: 600px;">
        <button class="modal-close" onclick="closeFlashcardsModal()">✕</button>
        
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.35rem;">🎴</span>
            <h2 style="font-size: 1.25rem; margin: 0;">Active-Recall Flashcards</h2>
          </div>
          <span id="cardCounter" style="font-size: 0.8rem; font-weight: 800; color: var(--accent-primary);">Card 1 / 4</span>
        </div>

        <p id="cardBookSubtitle" style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">Book Title</p>

        <!-- 3D Card Scene -->
        <div class="flashcard-scene" onclick="toggleCardFlip()">
          <div id="flashcardInner" class="flashcard-inner">
            <div class="flashcard-face flashcard-front">
              <span class="flashcard-prompt-label">❓ Concept Challenge (Click to Flip)</span>
              <div id="cardQuestion" class="flashcard-text">Loading question...</div>
              <span class="flashcard-hint">💡 Tap or Spacebar to reveal answer</span>
            </div>
            <div class="flashcard-face flashcard-back">
              <span class="flashcard-prompt-label" style="color: #34d399;">✅ Verified Concept Answer</span>
              <div id="cardAnswer" class="flashcard-text">Loading answer...</div>
              <span class="flashcard-hint" style="color: #34d399;">Tap again to flip back</span>
            </div>
          </div>
        </div>

        <!-- Deck Navigation -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
          <button id="prevCardBtn" class="btn-secondary" onclick="prevCard()">← Previous</button>
          <button class="btn-recommend" onclick="toggleCardFlip()" style="padding: 0.65rem 1.2rem;">🔄 Flip Card</button>
          <button id="nextCardBtn" class="search-btn" style="position: static; padding: 0.65rem 1.4rem;" onclick="nextCard()">Next →</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeFlashcardsModal();
    });

    document.addEventListener('keydown', (e) => {
      if (!modal.classList.contains('active')) return;
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        toggleCardFlip();
      } else if (e.key === 'ArrowRight') {
        nextCard();
      } else if (e.key === 'ArrowLeft') {
        prevCard();
      } else if (e.key === 'Escape') {
        closeFlashcardsModal();
      }
    });
  }

  document.getElementById('cardBookSubtitle').textContent = `${title} • by ${author || 'Author'}`;
  modal.classList.add('active');
  const inner = document.getElementById('flashcardInner');
  if (inner) inner.classList.remove('is-flipped');

  // Fetch Deck
  fetch(`/api/flashcards/${encodeURIComponent(title)}?author=${encodeURIComponent(author || '')}`)
    .then(res => res.json())
    .then(data => {
      flashcardDeck = data.cards || [];
      currentCardIndex = 0;
      displayCurrentCard();
    })
    .catch(err => {
      console.error('Error loading flashcards:', err);
      document.getElementById('cardQuestion').textContent = 'Error loading flashcards. Please retry.';
    });
}

function displayCurrentCard() {
  if (!flashcardDeck.length) return;
  const card = flashcardDeck[currentCardIndex];
  document.getElementById('cardQuestion').textContent = card.q;
  document.getElementById('cardAnswer').textContent = card.a;
  document.getElementById('cardCounter').textContent = `Card ${currentCardIndex + 1} / ${flashcardDeck.length}`;
  
  const inner = document.getElementById('flashcardInner');
  if (inner) inner.classList.remove('is-flipped');
}

function toggleCardFlip() {
  const inner = document.getElementById('flashcardInner');
  if (inner) inner.classList.toggle('is-flipped');
}

function nextCard() {
  if (!flashcardDeck.length) return;
  currentCardIndex = (currentCardIndex + 1) % flashcardDeck.length;
  displayCurrentCard();
}

function prevCard() {
  if (!flashcardDeck.length) return;
  currentCardIndex = (currentCardIndex - 1 + flashcardDeck.length) % flashcardDeck.length;
  displayCurrentCard();
}

function closeFlashcardsModal() {
  const modal = document.getElementById('flashcardsModal');
  if (modal) modal.classList.remove('active');
}



