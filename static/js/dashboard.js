/* ============================================================
   HireReady — dashboard.js
   Location: static/js/dashboard.js
   ============================================================ */

/* ============================================================
   FEATURE 1 — LIGHT / DARK MODE
   - Default: dark
   - Saves to localStorage key 'hireready_theme'
   - Applied on every page load before render (no flash)
   - 0.3s ease transition on all elements
   ============================================================ */

const THEME_KEY = 'hireready_theme';

// Apply theme immediately on load (before DOM ready to avoid flash)
(function applyThemeEarly() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'light') {
    document.documentElement.classList.add('light-mode-pending');
  }
})();

function toggleTheme() {
  const isLight = document.body.classList.contains('light-mode');

  if (isLight) {
    // → Switch to DARK
    document.body.classList.remove('light-mode');
    localStorage.setItem(THEME_KEY, 'dark');
    updateThemeUI(false);
  } else {
    // → Switch to LIGHT
    document.body.classList.add('light-mode');
    localStorage.setItem(THEME_KEY, 'light');
    updateThemeUI(true);
  }
}

function updateThemeUI(isLight) {
  const icon  = document.getElementById('themeIcon');
  const label = document.getElementById('themeLabel');
  if (icon)  icon.textContent  = isLight ? '☀️' : '🌙';
  if (label) label.textContent = isLight ? 'Light mode' : 'Dark mode';
}

function restoreTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  // Default is dark — only apply light if explicitly saved
  if (saved === 'light') {
    document.body.classList.add('light-mode');
    updateThemeUI(true);
  } else {
    // Ensure dark mode UI labels are correct on first load
    updateThemeUI(false);
  }
}


/* ============================================================
   FEATURE 2 — LOGOUT
   - Clears localStorage (theme + sidebar state)
   - Clears sessionStorage
   - Redirects to /logout (Flask clears server session)
   ============================================================ */

function handleLogout() {
  // Clear any client-side stored data
  localStorage.removeItem('hireready_theme');
  localStorage.removeItem('sidebar_collapsed');
  sessionStorage.clear();

  // Redirect to Flask logout route which clears server session
  window.location.href = '/logout';
}


/* ============================================================
   SIDEBAR — collapse / expand + mobile slide
   ============================================================ */

const COLLAPSE_KEY = 'sidebar_collapsed';

function isMobile() {
  return window.innerWidth <= 768;
}

function toggleSidebar() {
  if (isMobile()) {
    const isOpen = document.getElementById('sidebar').classList.contains('open');
    isOpen ? closeMobileSidebar() : openMobileSidebar();
  } else {
    const isCollapsed = document.body.classList.contains('sidebar-collapsed');
    isCollapsed ? expandSidebar() : collapseSidebar();
  }
}

function collapseSidebar() {
  document.body.classList.add('sidebar-collapsed');
  localStorage.setItem(COLLAPSE_KEY, 'true');
}

function expandSidebar() {
  document.body.classList.remove('sidebar-collapsed');
  localStorage.setItem(COLLAPSE_KEY, 'false');
}

function openMobileSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('overlay').classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() { closeMobileSidebar(); }

function closeMobileSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (isMobile()) closeMobileSidebar();
    else expandSidebar();
  }
});

window.addEventListener('resize', () => {
  if (!isMobile()) {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
    document.body.style.overflow = '';
  }
});


/* ============================================================
   DOM READY — run after page loads
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  // 1. Restore theme
  restoreTheme();

  // 2. Restore sidebar collapse state
  if (!isMobile() && localStorage.getItem(COLLAPSE_KEY) === 'true') {
    document.body.classList.add('sidebar-collapsed');
  }

  // 3. Active nav item highlight
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('href') === currentPath) {
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      item.classList.add('active');
    }
  });

  // 4. Weak topic bars — animate width
  document.querySelectorAll('.weak-fill').forEach(fill => {
    const target = fill.style.width;
    fill.style.width = '0%';
    setTimeout(() => { fill.style.width = target; }, 200);
  });

  // 5. Stat cards — stagger fade-in
  document.querySelectorAll('.stat-card').forEach((card, i) => {
    card.style.opacity   = '0';
    card.style.transform = 'translateY(12px)';
    card.style.transition = `opacity 0.35s ease ${i * 0.07}s, transform 0.35s ease ${i * 0.07}s`;
    setTimeout(() => {
      card.style.opacity   = '1';
      card.style.transform = 'translateY(0)';
    }, 50);
  });

  // 6. Subject cards — scroll fade-in
  const sqCards = document.querySelectorAll('.sq-card');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity   = '1';
          entry.target.style.transform = 'translateY(0)';
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    sqCards.forEach((card, i) => {
      card.style.opacity    = '0';
      card.style.transform  = 'translateY(10px)';
      card.style.transition = `opacity 0.3s ease ${i * 0.06}s, transform 0.3s ease ${i * 0.06}s`;
      obs.observe(card);
    });
  }

});