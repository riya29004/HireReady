/* ============================================================
   HireReady — login.js
   Location: static/js/login.js
   ============================================================ */

/* ----------------------------------------------------------
   1. TAB SWITCH — toggle between Login and Signup forms
---------------------------------------------------------- */
function switchTab(tab) {
  const formLogin  = document.getElementById('form-login');
  const formSignup = document.getElementById('form-signup');
  const tabLogin   = document.getElementById('tab-login');
  const tabSignup  = document.getElementById('tab-signup');

  if (tab === 'login') {
    formLogin.classList.remove('hidden');
    formSignup.classList.add('hidden');
    tabLogin.classList.add('active');
    tabSignup.classList.remove('active');
  } else {
    formSignup.classList.remove('hidden');
    formLogin.classList.add('hidden');
    tabSignup.classList.add('active');
    tabLogin.classList.remove('active');
  }
}


/* ----------------------------------------------------------
   2. PASSWORD VISIBILITY TOGGLE
---------------------------------------------------------- */
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;

  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁';
  }
}


/* ----------------------------------------------------------
   3. AUTO-SWITCH TO SIGNUP TAB
      If URL has ?tab=signup (e.g. from Sign up button on Index)
---------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('tab') === 'signup') {
    switchTab('signup');
  }
});
