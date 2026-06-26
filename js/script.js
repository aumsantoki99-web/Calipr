/* ==========================================================================
   CALIPR — Interactive Landing Page Script
   Handles navbar scroll, mobile menu, scroll reveal, metric counters,
   and the interactive candidate radar chart.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initMobileMenu();
  initCandidateDemo();
  initAuth();
});

const PRODUCT_URLS = {
  free: 'https://huggingface.co/spaces/Aumus/calipr',
  pro: 'https://huggingface.co/spaces/Aumus/calipr'
};

const SUPABASE_URL = 'https://vvakfljeslxhwceidxvi.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2YWtmbGplc2x4aHdjZWlkeHZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE4MzA4MDAsImV4cCI6MjA5NzQwNjgwMH0.faZg4fylypLfjVcswbWQrC47nIvI-CDIO3nHU5Fvyho';
const STORAGE_KEYS = {
  plan: 'calipr_pending_plan',
  target: 'calipr_pending_target',
  redirect: 'calipr_auto_redirect'
};

let supabaseClient = null;
let authMode = 'signin';
let authElements = null;

async function initAuth() {
  if (!window.supabase || !window.supabase.createClient) return;

  supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      flowType: 'pkce',
      detectSessionInUrl: true,
      persistSession: true,
      autoRefreshToken: true
    }
  });

  authElements = {
    modal: document.getElementById('authModal'),
    title: document.getElementById('authModalTitle'),
    copy: document.getElementById('authModalCopy'),
    status: document.getElementById('authStatus'),
    form: document.getElementById('authForm'),
    name: document.getElementById('authName'),
    email: document.getElementById('authEmail'),
    password: document.getElementById('authPassword'),
    submit: document.getElementById('authSubmitButton'),
    google: document.getElementById('authGoogleButton'),
    tabs: Array.from(document.querySelectorAll('.auth-tab')),
    triggers: Array.from(document.querySelectorAll('[data-auth-trigger]')),
    closers: Array.from(document.querySelectorAll('[data-auth-close]'))
  };

  bindAuthEvents();
  setAuthMode('signin');

  const { data: { session } } = await supabaseClient.auth.getSession();
  if (session) {
    await updateSignedInState(session);
    await maybeRedirectAuthenticatedUser(session);
  }

  supabaseClient.auth.onAuthStateChange(async (event, session) => {
    if (!session) return;
    if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'INITIAL_SESSION') {
      await updateSignedInState(session);
      await maybeRedirectAuthenticatedUser(session);
    }
  });
}

function bindAuthEvents() {
  authElements.triggers.forEach((trigger) => {
    trigger.addEventListener('click', async () => {
      const plan = trigger.dataset.authPlan || 'pro';
      const target = trigger.dataset.authTarget || PRODUCT_URLS[plan] || PRODUCT_URLS.pro;
      setPendingDestination(plan, target, true);

      const { data: { session } } = await supabaseClient.auth.getSession();
      if (session) {
        await updateSignedInState(session);
        redirectToPendingDestination();
        return;
      }

      updateModalCopy(plan);
      openAuthModal();
    });
  });

  authElements.closers.forEach((closer) => {
    closer.addEventListener('click', closeAuthModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeAuthModal();
  });

  authElements.tabs.forEach((tab) => {
    tab.addEventListener('click', () => setAuthMode(tab.dataset.authMode || 'signin'));
  });

  authElements.google.addEventListener('click', handleGoogleAuth);
  authElements.form.addEventListener('submit', handleEmailAuth);
}

function setPendingDestination(plan, target, shouldRedirect) {
  localStorage.setItem(STORAGE_KEYS.plan, plan);
  localStorage.setItem(STORAGE_KEYS.target, target);
  localStorage.setItem(STORAGE_KEYS.redirect, shouldRedirect ? 'true' : 'false');
}

function getPendingPlan() {
  return localStorage.getItem(STORAGE_KEYS.plan) || 'pro';
}

function getPendingTarget() {
  return localStorage.getItem(STORAGE_KEYS.target) || PRODUCT_URLS[getPendingPlan()] || PRODUCT_URLS.pro;
}

function clearAuthStatus() {
  authElements.status.textContent = '';
  authElements.status.className = 'auth-status';
}

function setAuthStatus(message, tone) {
  authElements.status.textContent = message;
  authElements.status.className = `auth-status${tone ? ` is-${tone}` : ''}`;
}

function setAuthMode(mode) {
  authMode = mode;
  authElements.modal.dataset.authMode = mode;
  authElements.tabs.forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.authMode === mode);
  });
  authElements.submit.textContent = mode === 'signup' ? 'Create Account' : 'Sign In';
  authElements.password.autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
  clearAuthStatus();
}

function updateModalCopy(plan) {
  const copy = plan === 'free'
    ? 'Create your Calipr account to continue into the sandbox experience.'
    : 'Sign in to continue into the full Calipr workspace.';
  authElements.copy.textContent = copy;
}

function openAuthModal() {
  authElements.modal.classList.add('is-open');
  authElements.modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeAuthModal() {
  authElements.modal.classList.remove('is-open');
  authElements.modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

async function handleGoogleAuth() {
  try {
    clearAuthStatus();
    const plan = getPendingPlan();
    updateModalCopy(plan);
    const { error } = await supabaseClient.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}${window.location.pathname}`,
        queryParams: {
          prompt: 'select_account'
        }
      }
    });
    if (error) {
      throw error;
    }
  } catch (error) {
    setAuthStatus(error.message || 'Google sign-in could not be started.', 'error');
  }
}

async function handleEmailAuth(event) {
  event.preventDefault();
  clearAuthStatus();

  const fullName = authElements.name.value.trim();
  const email = authElements.email.value.trim();
  const password = authElements.password.value;
  const plan = getPendingPlan();

  if (!email || !password) {
    setAuthStatus('Email and password are required.', 'error');
    return;
  }

  if (authMode === 'signup' && !fullName) {
    setAuthStatus('Full name is required to create an account.', 'error');
    return;
  }

  try {
    if (authMode === 'signup') {
      const { data, error } = await supabaseClient.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}${window.location.pathname}`,
          data: {
            full_name: fullName,
            plan
          }
        }
      });

      if (error) throw error;

      if (data.session) {
        await updateSignedInState(data.session);
        redirectToPendingDestination();
        return;
      }

      setAuthStatus('Account created. Check your inbox to verify your email, then sign in.', 'success');
      setAuthMode('signin');
      return;
    }

    const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
    if (error) throw error;
    await updateSignedInState(data.session);
    redirectToPendingDestination();
  } catch (error) {
    setAuthStatus(error.message || 'Authentication failed. Please try again.', 'error');
  }
}

async function updateSignedInState(session) {
  const user = session?.user;
  if (!user) return;

  const selectedPlan = getPendingPlan();
  const userMeta = user.user_metadata || {};
  if (userMeta.plan !== selectedPlan) {
    await supabaseClient.auth.updateUser({
      data: {
        ...userMeta,
        plan: selectedPlan
      }
    });
  }

  const displayName = userMeta.full_name || user.email || 'Account';
  document.querySelectorAll('#nav-sign-in, #mobile-sign-in').forEach((button) => {
    button.textContent = displayName.split(' ')[0];
  });
  closeAuthModal();
}

async function maybeRedirectAuthenticatedUser(session) {
  if (localStorage.getItem(STORAGE_KEYS.redirect) !== 'true') return;
  if (!session?.user) return;
  redirectToPendingDestination();
}

function redirectToPendingDestination() {
  const target = getPendingTarget();
  localStorage.removeItem(STORAGE_KEYS.redirect);
  window.location.href = target;
}

/* ==========================================================================
   1. NAVBAR SCROLL EFFECT
   ========================================================================== */
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  const handleScroll = () => {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };

  window.addEventListener('scroll', handleScroll);
  // Run once initially in case page is refreshed while scrolled down
  handleScroll();
}

/* ==========================================================================
   2. MOBILE HAMBURGER MENU
   ========================================================================== */
function initMobileMenu() {
  const navToggle = document.getElementById('navToggle');
  const mobileMenu = document.getElementById('mobileMenu');
  if (!navToggle || !mobileMenu) return;

  navToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    navToggle.classList.toggle('active');
    mobileMenu.classList.toggle('active');
    document.body.style.overflow = mobileMenu.classList.contains('active') ? 'hidden' : '';
  });

  // Close mobile menu when clicking a link
  const mobileLinks = mobileMenu.querySelectorAll('.mobile-link, .btn');
  mobileLinks.forEach(link => {
    link.addEventListener('click', () => {
      navToggle.classList.remove('active');
      mobileMenu.classList.remove('active');
      document.body.style.overflow = '';
    });
  });

  // Close mobile menu when clicking outside
  document.addEventListener('click', (e) => {
    if (mobileMenu.classList.contains('active') && !mobileMenu.contains(e.target) && e.target !== navToggle) {
      navToggle.classList.remove('active');
      mobileMenu.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
}



/* ==========================================================================
   5. INTERACTIVE CANDIDATE RADAR CHART DEMO
   ========================================================================== */
// Candidate profiles data
const candidateData = [
  {
    name: "Alex Chen",
    title: "Staff Engineer · 10 years",
    avatar: "AC",
    score: 0.87,
    skills: ["Python", "React", "FastAPI", "PostgreSQL", "Docker"],
    scores: {
      semantic: 0.92,
      skills: 0.88,
      trajectory: 0.78,
      behavioral: 0.85,
      domain: 0.90
    }
  },
  {
    name: "Maria Santos",
    title: "Senior ML Engineer · 6 years",
    avatar: "MS",
    score: 0.91,
    skills: ["Python", "PyTorch", "scikit-learn", "AWS", "Kubernetes"],
    scores: {
      semantic: 0.95,
      skills: 0.92,
      trajectory: 0.88,
      behavioral: 0.80,
      domain: 0.94
    }
  },
  {
    name: "Rohan Gupta",
    title: "Associate Software Engineer · 1 year",
    avatar: "RG",
    score: 0.62,
    skills: ["Java", "C++", "SQL", "Git", "HTML/CSS"],
    scores: {
      semantic: 0.70,
      skills: 0.60,
      trajectory: 0.45,
      behavioral: 0.80,
      domain: 0.65
    }
  }
];

let activeCandidateIdx = 0;
let radarChartInstance = null;

function initCandidateDemo() {
  const canvas = document.getElementById('radarChart');
  if (!canvas) return;

  // Set up canvas context and scaling for High DPI screens
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  // Radar chart config
  const radarConfig = {
    labels: ["Semantic Fit", "Skills Match", "Career", "Behavioral", "Domain"],
    axesCount: 5,
    centerX: rect.width / 2,
    centerY: rect.height / 2,
    radius: Math.min(rect.width, rect.height) * 0.38,
    animationDuration: 500, // ms
    colors: {
      grid: '#e4e2e2',
      gridText: '#757170',
      axis: '#e4e2e2',
      polygonBorder: '#156cc2',
      polygonFill: 'rgba(132, 185, 239, 0.35)',
      dots: '#156cc2'
    }
  };

  // Interpolation state
  let currentValues = [0, 0, 0, 0, 0];
  let targetValues = getTargetValues(activeCandidateIdx);
  let animStartTime = null;

  function getTargetValues(index) {
    const p = candidateData[index].scores;
    return [p.semantic, p.skills, p.trajectory, p.behavioral, p.domain];
  }

  // Draw loop
  function drawRadar(timestamp) {
    if (!animStartTime) animStartTime = timestamp;
    const elapsed = timestamp - animStartTime;
    const progress = Math.min(elapsed / radarConfig.animationDuration, 1);

    // Easing out cubic
    const easeProgress = 1 - Math.pow(1 - progress, 3);

    // Interpolate current values
    const displayedValues = currentValues.map((curr, i) => {
      const target = targetValues[i];
      return curr + (target - curr) * easeProgress;
    });

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Draw grid lines & background rings
    const ringCount = 5;
    for (let r = 1; r <= ringCount; r++) {
      const ringRadius = (r / ringCount) * radarConfig.radius;
      ctx.beginPath();
      for (let i = 0; i < radarConfig.axesCount; i++) {
        const angle = (i * 2 * Math.PI / radarConfig.axesCount) - (Math.PI / 2);
        const x = radarConfig.centerX + ringRadius * Math.cos(angle);
        const y = radarConfig.centerY + ringRadius * Math.sin(angle);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.closePath();
      ctx.strokeStyle = radarConfig.colors.grid;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Add grid ring values (e.g. 0.2, 0.4...)
      ctx.fillStyle = radarConfig.colors.gridText;
      ctx.font = '10px "Fragment Mono", monospace';
      ctx.fillText((r / ringCount).toFixed(1), radarConfig.centerX + 5, radarConfig.centerY - ringRadius + 3);
    }

    // Draw axes lines and labels
    for (let i = 0; i < radarConfig.axesCount; i++) {
      const angle = (i * 2 * Math.PI / radarConfig.axesCount) - (Math.PI / 2);
      
      // Axis line
      const outerX = radarConfig.centerX + radarConfig.radius * Math.cos(angle);
      const outerY = radarConfig.centerY + radarConfig.radius * Math.sin(angle);
      
      ctx.beginPath();
      ctx.moveTo(radarConfig.centerX, radarConfig.centerY);
      ctx.lineTo(outerX, outerY);
      ctx.strokeStyle = radarConfig.colors.axis;
      ctx.stroke();

      // Axis label
      const labelDistance = radarConfig.radius + 18;
      const labelX = radarConfig.centerX + labelDistance * Math.cos(angle);
      const labelY = radarConfig.centerY + labelDistance * Math.sin(angle);
      
      ctx.fillStyle = '#1a1615';
      ctx.font = 'bold 12px "Inter", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // Adjust alignments slightly based on angle
      const cos = Math.cos(angle);
      if (Math.abs(cos) < 0.1) {
        ctx.textAlign = 'center';
      } else if (cos > 0) {
        ctx.textAlign = 'left';
      } else {
        ctx.textAlign = 'right';
      }

      ctx.fillText(radarConfig.labels[i], labelX, labelY);
    }

    // Draw candidate score polygon
    ctx.beginPath();
    for (let i = 0; i < radarConfig.axesCount; i++) {
      const angle = (i * 2 * Math.PI / radarConfig.axesCount) - (Math.PI / 2);
      const valRadius = displayedValues[i] * radarConfig.radius;
      const x = radarConfig.centerX + valRadius * Math.cos(angle);
      const y = radarConfig.centerY + valRadius * Math.sin(angle);
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.closePath();
    ctx.fillStyle = radarConfig.colors.polygonFill;
    ctx.fill();
    ctx.strokeStyle = radarConfig.colors.polygonBorder;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Draw dots at vertices
    for (let i = 0; i < radarConfig.axesCount; i++) {
      const angle = (i * 2 * Math.PI / radarConfig.axesCount) - (Math.PI / 2);
      const valRadius = displayedValues[i] * radarConfig.radius;
      const x = radarConfig.centerX + valRadius * Math.cos(angle);
      const y = radarConfig.centerY + valRadius * Math.sin(angle);

      ctx.beginPath();
      ctx.arc(x, y, 4.5, 0, 2 * Math.PI);
      ctx.fillStyle = radarConfig.colors.dots;
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    if (progress < 1) {
      requestAnimationFrame(drawRadar);
    } else {
      // Save current values to state for next animation transition
      currentValues = [...targetValues];
    }
  }

  // Initial draw
  requestAnimationFrame((ts) => {
    // Warm up from 0
    currentValues = [0, 0, 0, 0, 0];
    animStartTime = ts;
    drawRadar(ts);
  });

  // Global switch candidate function
  window.switchCandidate = function(idx) {
    if (idx === activeCandidateIdx) return;
    
    // Update active tab styles
    const tabs = document.querySelectorAll('.demo-tab');
    tabs.forEach((tab, i) => {
      if (i === idx) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    activeCandidateIdx = idx;
    const c = candidateData[idx];

    // Animate updating details in candidate info card
    const avatar = document.getElementById('candidateAvatar');
    const name = document.getElementById('candidateName');
    const title = document.getElementById('candidateTitle');
    const scoreVal = document.querySelector('.score-number');
    const skillsContainer = document.getElementById('candidateSkills');
    const breakdownFillBars = document.querySelectorAll('.breakdown-fill');
    const breakdownTextVals = document.querySelectorAll('.breakdown-row span:last-child');

    // Fade out briefly then update text
    [avatar, name, title, scoreVal, skillsContainer].forEach(el => {
      el.style.opacity = 0.3;
      el.style.transition = 'opacity 200ms ease';
    });

    setTimeout(() => {
      avatar.textContent = c.avatar;
      // Assign background colors to avatars dynamically
      const avatarColors = [
        'linear-gradient(135deg, #84b9ef, #156cc2)',
        'linear-gradient(135deg, #0ea158, #0b7a42)',
        'linear-gradient(135deg, #cf8d13, #a06f0e)'
      ];
      avatar.style.background = avatarColors[idx];
      name.textContent = c.name;
      title.textContent = c.title;
      scoreVal.textContent = c.score.toFixed(2);

      // Re-populate skills tags
      skillsContainer.innerHTML = '';
      c.skills.forEach(skill => {
        const tag = document.createElement('span');
        tag.className = 'skill-tag';
        tag.textContent = skill;
        skillsContainer.appendChild(tag);
      });

      // Update breakdown bars & text
      const scoresArr = [c.scores.semantic, c.scores.skills, c.scores.trajectory, c.scores.behavioral, c.scores.domain];
      breakdownFillBars.forEach((bar, i) => {
        bar.style.width = `${scoresArr[i] * 100}%`;
      });
      breakdownTextVals.forEach((span, i) => {
        span.textContent = scoresArr[i].toFixed(2);
      });

      [avatar, name, title, scoreVal, skillsContainer].forEach(el => {
        el.style.opacity = 1;
      });

      // Trigger radar chart update
      targetValues = getTargetValues(idx);
      animStartTime = null;
      requestAnimationFrame(drawRadar);
    }, 200);
  };
}
