/* ============================================================
   HireReady — index.js
   Location: static/js/index.js
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ----------------------------------------------------------
     1. CHIP TOGGLE
  ---------------------------------------------------------- */
  const chips = document.querySelectorAll('.chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });


  /* ----------------------------------------------------------
     2. SEARCH — navigates to Flask /search?q=...
  ---------------------------------------------------------- */
  const searchInput = document.querySelector('.search-wrap input');
  const searchBtn   = document.querySelector('.search-btn');

  function handleSearch() {
    const query = searchInput ? searchInput.value.trim() : '';
    if (!query) return;
    window.location.href = `/search?q=${encodeURIComponent(query)}`;
  }

  if (searchBtn)   searchBtn.addEventListener('click', handleSearch);
  if (searchInput) searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleSearch();
  });


  /* ----------------------------------------------------------
     3. SCROLL FADE-IN — subject cards
  ---------------------------------------------------------- */
  const cards = document.querySelectorAll('.s-card');

  if ('IntersectionObserver' in window) {
    const cardObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          cardObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    cards.forEach((card, i) => {
      card.style.transitionDelay = `${i * 0.07}s`;
      cardObserver.observe(card);
    });

  } else {
    // Fallback if IntersectionObserver not supported
    cards.forEach(card => card.classList.add('visible'));
  }


  /* ----------------------------------------------------------
     4. ACTIVE NAV LINK on scroll
  ---------------------------------------------------------- */
  const sections = document.querySelectorAll('section[id], div[id]');
  const navLinks = document.querySelectorAll('.nav-links a');

  if (sections.length && navLinks.length) {
    const navObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('id');
          navLinks.forEach(link => {
            link.classList.toggle(
              'nav-active',
              link.getAttribute('href') === `#${id}`
            );
          });
        }
      });
    }, { threshold: 0.4 });

    sections.forEach(s => navObserver.observe(s));
  }


  /* ----------------------------------------------------------
     5. SMOOTH SCROLL for anchor links
  ---------------------------------------------------------- */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

});
