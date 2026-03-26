/* ============================================================
   CHUNK 1: Navigation + IntersectionObserver
   ============================================================ */
(function () {
  'use strict';

  /* ---- State ---- */
  var currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  var detailVisible = false;   // global simple/detail toggle preference
  var mermaidReady = false;

  /* ---- Navigation: smooth scroll ---- */
  document.querySelectorAll('.nav-link[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Close mobile sidebar
        closeSidebar();
      }
    });
  });

  /* ---- Mobile sidebar ---- */
  var sidebar = document.getElementById('sidebar');
  var navToggle = document.getElementById('nav-toggle');
  var overlay = document.getElementById('sidebar-overlay');

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('open');
    navToggle.classList.add('open');
    navToggle.setAttribute('aria-expanded', 'true');
  }
  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
    navToggle.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  }
  if (navToggle) {
    navToggle.addEventListener('click', function () {
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
  }
  if (overlay) overlay.addEventListener('click', closeSidebar);

  /* ---- Modules nav group toggle ---- */
  document.querySelectorAll('.nav-group-toggle').forEach(function (el) {
    el.addEventListener('click', function () {
      this.classList.toggle('open');
      var children = this.nextElementSibling;
      if (children && children.classList.contains('nav-group-children')) {
        children.classList.toggle('open');
      }
    });
  });

  /* ---- Active section tracking via IntersectionObserver ---- */
  var navLinks = document.querySelectorAll('.nav-link[data-section]');
  var sections = document.querySelectorAll('.section[id]');

  if ('IntersectionObserver' in window && sections.length > 0) {
    var activeId = null;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          activeId = entry.target.id;
          navLinks.forEach(function (link) {
            var isActive = link.getAttribute('data-section') === activeId ||
                           link.getAttribute('href') === '#' + activeId;
            link.classList.toggle('active', isActive);
          });
        }
      });
    }, {
      rootMargin: '-20% 0px -60% 0px',
      threshold: 0
    });

    sections.forEach(function (sec) { observer.observe(sec); });
  }

  /* ---- Mermaid: clickable architecture nodes ---- */
  function hookMermaidClicks() {
    setTimeout(function () {
      document.querySelectorAll('.mermaid[data-clickable] .node').forEach(function (node) {
        node.style.cursor = 'pointer';
        node.addEventListener('click', function () {
          var label = this.querySelector('text, span');
          if (!label) return;
          var text = label.textContent.trim().toLowerCase().replace(/\s+/g, '-');
          var target = document.getElementById('module-' + text);
          if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });
    }, 800);
  }

  /* exposed for chunk 3 */
  window._RT = window._RT || {};
  window._RT.hookMermaidClicks = hookMermaidClicks;
  window._RT.getCurrentTheme = function () { return currentTheme; };

/* ============================================================
   CHUNK 2: Search Engine
   ============================================================ */

  var searchModal = document.getElementById('search-modal');
  var searchInput = document.getElementById('search-input');
  var searchResults = document.getElementById('search-results');
  var searchEmpty = document.getElementById('search-empty');
  var searchTrigger = document.getElementById('search-trigger');
  var searchClose = document.getElementById('search-close');
  var focusedIdx = -1;

  function openSearch() {
    if (!searchModal) return;
    searchModal.removeAttribute('hidden');
    searchInput && searchInput.focus();
    focusedIdx = -1;
  }
  function closeSearch() {
    if (!searchModal) return;
    searchModal.setAttribute('hidden', '');
    searchInput && (searchInput.value = '');
    renderResults([]);
  }

  if (searchTrigger) searchTrigger.addEventListener('click', openSearch);
  if (searchClose) searchClose.addEventListener('click', closeSearch);
  if (searchModal) {
    searchModal.querySelector('.search-modal-backdrop')
      .addEventListener('click', closeSearch);
  }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      searchModal && searchModal.hasAttribute('hidden') ? openSearch() : closeSearch();
    }
    if (e.key === 'Escape') closeSearch();

    if (!searchModal || searchModal.hasAttribute('hidden')) return;

    var items = searchResults ? searchResults.querySelectorAll('.search-result') : [];
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIdx = Math.min(focusedIdx + 1, items.length - 1);
      updateFocus(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIdx = Math.max(focusedIdx - 1, 0);
      updateFocus(items);
    } else if (e.key === 'Enter' && focusedIdx >= 0 && items[focusedIdx]) {
      items[focusedIdx].click();
    }
  });

  function updateFocus(items) {
    items.forEach(function (item, i) {
      item.classList.toggle('focused', i === focusedIdx);
    });
    if (items[focusedIdx]) items[focusedIdx].scrollIntoView({ block: 'nearest' });
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      var q = this.value.trim().toLowerCase();
      focusedIdx = -1;
      if (!q) { renderResults([]); return; }
      var results = search(q);
      renderResults(results);
    });
  }

  function search(query) {
    var index = window.SEARCH_INDEX || [];
    if (!index.length) return [];
    var terms = query.split(/\s+/).filter(Boolean);
    var scored = [];

    index.forEach(function (entry) {
      var text = (entry.text || '').toLowerCase();
      var score = 0;
      terms.forEach(function (term) {
        if (text.includes(term)) score += (term.length * 2);
      });
      if (score > 0) scored.push({ entry: entry, score: score });
    });

    scored.sort(function (a, b) { return b.score - a.score; });
    return scored.slice(0, 8).map(function (s) { return s.entry; });
  }

  function renderResults(results) {
    if (!searchResults) return;
    if (!results.length) {
      searchResults.innerHTML = '';
      searchEmpty && (searchInput && searchInput.value.trim()
        ? searchEmpty.removeAttribute('hidden')
        : searchEmpty.setAttribute('hidden', ''));
      return;
    }
    searchEmpty && searchEmpty.setAttribute('hidden', '');
    searchResults.innerHTML = results.map(function (r, i) {
      var snippet = (r.snippet || r.text || '').slice(0, 120);
      var highlighted = snippet.replace(
        new RegExp(searchInput.value.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'),
        function (m) { return '<mark>' + m + '</mark>'; }
      );
      return '<div class="search-result" role="option" data-id="' + (r.id || '') + '" tabindex="-1">' +
        '<span class="search-result-section">' + escHtml(r.section || '') + '</span>' +
        '<span class="search-result-snippet">' + highlighted + '</span>' +
        '</div>';
    }).join('');

    searchResults.querySelectorAll('.search-result').forEach(function (el) {
      el.addEventListener('click', function () {
        var id = this.getAttribute('data-id');
        var target = id ? document.getElementById(id) : null;
        if (target) {
          closeSearch();
          setTimeout(function () { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 80);
        }
      });
    });
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

/* ============================================================
   CHUNK 3: Toggle System + Mermaid Init
   ============================================================ */

  /* ---- Simple / Detailed toggle ---- */
  document.querySelectorAll('.toggle-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var card = this.closest('[data-toggleable]') || this.parentElement;
      var simple = card.querySelector('.simple-view');
      var detail = card.querySelector('.detail-view');
      if (!simple || !detail) return;

      var showing = detail.classList.contains('visible');
      if (showing) {
        detail.classList.remove('visible');
        simple.classList.remove('hidden');
        this.textContent = 'Show Details';
      } else {
        detail.classList.add('visible');
        simple.classList.add('hidden');
        this.textContent = 'Show Overview';
      }
    });
  });

  /* ---- Global toggle "expand all" shortcut (double-click on section header) ---- */
  document.querySelectorAll('.section-title').forEach(function (title) {
    title.addEventListener('dblclick', function () {
      var section = this.closest('.section');
      if (!section) return;
      var allDetail = section.querySelectorAll('.detail-view');
      var allSimple = section.querySelectorAll('.simple-view');
      var anyHidden = Array.prototype.some.call(allDetail, function (d) {
        return !d.classList.contains('visible');
      });
      allDetail.forEach(function (d) { d.classList.toggle('visible', anyHidden); });
      allSimple.forEach(function (s) { s.classList.toggle('hidden', anyHidden); });
    });
  });

  /* ---- Mermaid initialization ---- */
  function initMermaid(theme) {
    if (window.MERMAID_FAILED) {
      showMermaidFallbacks();
      return;
    }
    if (typeof mermaid === 'undefined') {
      setTimeout(function () { initMermaid(theme); }, 300);
      return;
    }
    try {
      mermaid.initialize({
        startOnLoad: false,
        theme: theme === 'dark' ? 'dark' : 'default',
        securityLevel: 'loose',
        fontFamily: 'inherit',
        flowchart: { curve: 'basis', htmlLabels: true },
        sequence: { actorMargin: 60 }
      });

      /* render all .mermaid blocks */
      var blocks = document.querySelectorAll('.mermaid');
      if (blocks.length === 0) { mermaidReady = true; return; }

      blocks.forEach(function (block, idx) {
        var code = block.getAttribute('data-diagram') || block.textContent;
        if (!code || !code.trim()) return;
        var id = 'mermaid-graph-' + idx;
        mermaid.render(id, code.trim()).then(function (result) {
          block.innerHTML = result.svg;
          block.removeAttribute('data-diagram');
          mermaidReady = true;
          window._RT.hookMermaidClicks();
        }).catch(function (err) {
          console.warn('Mermaid render error:', err);
          block.innerHTML = '<pre class="mermaid-fallback">' + escHtml(code) + '</pre>';
        });
      });
    } catch (e) {
      console.warn('Mermaid init error:', e);
      showMermaidFallbacks();
    }
  }

  function showMermaidFallbacks() {
    document.querySelectorAll('.mermaid').forEach(function (block) {
      var code = block.getAttribute('data-diagram') || block.textContent;
      if (code) {
        block.innerHTML = '<pre class="mermaid-fallback"><code>' + escHtml(code.trim()) + '</code></pre>' +
          '<p class="mermaid-fallback" style="font-size:0.75rem">Diagram rendering unavailable offline.</p>';
      }
    });
  }

  /* Prepare mermaid blocks: move content to data-diagram to avoid flash */
  document.querySelectorAll('.mermaid').forEach(function (block) {
    if (block.textContent.trim() && !block.getAttribute('data-diagram')) {
      block.setAttribute('data-diagram', block.textContent.trim());
      block.textContent = '';
    }
  });

  /* Expose for dark mode toggle in chunk 4 */
  window._RT.reinitMermaid = function (theme) {
    document.querySelectorAll('.mermaid').forEach(function (block) {
      var orig = block.getAttribute('data-diagram');
      if (!orig && block.querySelector('svg')) {
        orig = block.querySelector('svg').getAttribute('aria-label') || '';
      }
      if (orig) block.setAttribute('data-diagram', orig);
      block.innerHTML = '';
    });
    initMermaid(theme);
  };

/* ============================================================
   CHUNK 4: Dark Mode + Deploy Dropdown + Print + Boot
   ============================================================ */

  /* ---- Dark / Light mode ---- */
  function applyTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    /* re-init mermaid with new theme if already loaded */
    if (mermaidReady || typeof mermaid !== 'undefined') {
      window._RT.reinitMermaid(theme);
    }
  }

  /* Detect system preference on first load */
  (function () {
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(prefersDark ? 'dark' : 'light');
  })();

  /* Manual toggle */
  var themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });
  }

  /* System preference change listener */
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  /* ---- Deploy dropdown ---- */
  var deployToggle = document.getElementById('deploy-toggle');
  var deployMenu = document.querySelector('.deploy-menu');

  if (deployToggle && deployMenu) {
    deployToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = !deployMenu.hasAttribute('hidden');
      deployMenu.toggleAttribute('hidden', isOpen);
      deployToggle.setAttribute('aria-expanded', String(!isOpen));
    });

    document.addEventListener('click', function () {
      deployMenu.setAttribute('hidden', '');
      deployToggle.setAttribute('aria-expanded', 'false');
    });

    deployMenu.addEventListener('click', function (e) { e.stopPropagation(); });
  }

  /* Copy to clipboard for deploy commands */
  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item = this.closest('.deploy-item');
      var cmd = item ? item.getAttribute('data-cmd') : '';
      if (!cmd) return;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cmd).then(function () {
          markCopied(btn);
        });
      } else {
        /* Fallback for sandboxed environments */
        var ta = document.createElement('textarea');
        ta.value = cmd;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); markCopied(btn); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  });

  function markCopied(btn) {
    var orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(function () {
      btn.textContent = orig;
      btn.classList.remove('copied');
    }, 2000);
  }

  /* ---- Print button (optional) ---- */
  document.querySelectorAll('[data-action="print"]').forEach(function (btn) {
    btn.addEventListener('click', function () { window.print(); });
  });

  /* ---- Boot sequence ---- */
  /* 1. Init mermaid after DOM is ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { initMermaid(currentTheme); });
  } else {
    initMermaid(currentTheme);
  }

  /* 2. Scroll section animations: use IntersectionObserver to stagger fade-in */
  if ('IntersectionObserver' in window) {
    var fadeObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.animationDelay = '0ms';
          fadeObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05 });

    document.querySelectorAll('.section, .module-card, .stack-card').forEach(function (el) {
      el.style.animationDelay = '200ms';
      el.style.animationFillMode = 'both';
      fadeObserver.observe(el);
    });
  }

}()); /* end IIFE */