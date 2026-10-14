/**
 * ================================================================
 * HEALORA – Smart Hospital Communication Platform
 * Frontend JavaScript (SPA)
 * ================================================================
 * Connects to FastAPI backend at BASE_URL.
 * Handles: auth, routing, patient & doctor flows, real API calls.
 * ================================================================
 */

'use strict';

// ── CONFIG ──────────────────────────────────────────────────────
const BASE_URL = 'http://127.0.0.1:8000';
const API      = `${BASE_URL}/api/v1`;

// ── STATE ────────────────────────────────────────────────────────
let _state = {
  token:        localStorage.getItem('healora_token') || null,
  refreshToken: localStorage.getItem('healora_refresh') || null,
  user:         JSON.parse(localStorage.getItem('healora_user') || 'null'),
  currentSection: null,
  allDoctors:   [],
  bookDoctor:   null,
  bookSlot:     null,
  replyQueryId: null,
  notifications: [],
};

// ── UTILITY: HTTP ────────────────────────────────────────────────
async function request(method, path, body, auth = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && _state.token) headers['Authorization'] = `Bearer ${_state.token}`;
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  let res = await fetch(`${API}${path}`, opts);

  // Try token refresh on 401
  if (res.status === 401 && _state.refreshToken) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${_state.token}`;
      res = await fetch(`${API}${path}`, { ...opts, headers });
    } else {
      handleLogout();
      return null;
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || JSON.stringify(err));
  }
  const ct = res.headers.get('content-type');
  if (ct && ct.includes('application/json')) return res.json();
  return null;
}

async function tryRefresh() {
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: _state.refreshToken }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    _state.token = data.access_token;
    localStorage.setItem('healora_token', data.access_token);
    return true;
  } catch { return false; }
}

const get  = (path) => request('GET',    path, null);
const post = (path, body) => request('POST',   path, body);
const put  = (path, body) => request('PUT',    path, body);
const del  = (path) => request('DELETE', path, null);

// ── UTILITY: DOM ─────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const show = (id) => $(id) && $(id).classList.remove('hidden');
const hide = (id) => $(id) && $(id).classList.add('hidden');
function esc(str) {
  const d = document.createElement('div');
  d.textContent = String(str ?? '');
  return d.innerHTML;
}
function fmtDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
function fmtDateOnly(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
function initials(name) {
  if (!name) return '?';
  return name.split(' ').map(p => p[0]).join('').toUpperCase().slice(0, 2);
}
function badgeHtml(status) {
  const cls = {
    PENDING: 'badge-pending', CONFIRMED: 'badge-confirmed',
    COMPLETED: 'badge-completed', CANCELLED: 'badge-cancelled',
    RESCHEDULED: 'badge-rescheduled', EMERGENCY: 'badge-emergency',
    HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low',
    SUBMITTED: 'badge-submitted', ASSIGNED: 'badge-assigned',
    RESOLVED: 'badge-resolved', REVIEWED: 'badge-reviewed',
  }[status] || 'badge-submitted';
  return `<span class="badge ${cls}">${esc(status)}</span>`;
}

// ── TOAST ────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-ico">${icons[type]}</span><span>${esc(msg)}</span>`;
  $('toast-container').appendChild(t);
  setTimeout(() => {
    t.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => t.remove(), 320);
  }, 3500);
}

// ── MODAL ────────────────────────────────────────────────────────
function openModal(id)  { $(id) && $(id).classList.add('open'); }
function closeModal(id) { $(id) && $(id).classList.remove('open'); }

// ── AUTH TAB SWITCH ──────────────────────────────────────────────
function switchAuthTab(tab) {
  $('tab-login').classList.toggle('active', tab === 'login');
  $('tab-register').classList.toggle('active', tab === 'register');
  $('form-login').classList.toggle('hidden', tab !== 'login');
  $('form-register').classList.toggle('hidden', tab !== 'register');
}

function toggleDoctorFields() {
  const role = $('reg-role').value;
  const df = $('doctor-fields');
  df.classList.toggle('visible', role === 'DOCTOR');
}

// ── LOGIN ────────────────────────────────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  const errEl = $('login-error');
  errEl.classList.remove('visible');
  const btn = $('btn-login');
  btn.disabled = true; btn.textContent = 'Signing in…';

  try {
    // FastAPI OAuth2 expects form data for /token
    const formData = new URLSearchParams();
    formData.append('username', $('login-email').value.trim());
    formData.append('password', $('login-password').value);

    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Invalid credentials');
    }

    const data = await res.json();
    _state.token = data.access_token;
    _state.refreshToken = data.refresh_token || null;
    localStorage.setItem('healora_token', data.access_token);
    if (data.refresh_token) localStorage.setItem('healora_refresh', data.refresh_token);

    // Fetch user info
    const me = await get('/auth/me');
    _state.user = me;
    localStorage.setItem('healora_user', JSON.stringify(me));

    bootApp();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('visible');
  } finally {
    btn.disabled = false; btn.textContent = 'Sign In to HEALORA';
  }
}

// ── REGISTER ─────────────────────────────────────────────────────
async function handleRegister(e) {
  e.preventDefault();
  const errEl = $('register-error');
  errEl.classList.remove('visible');
  const btn = $('btn-register');
  btn.disabled = true; btn.textContent = 'Creating account…';

  try {
    const role = $('reg-role').value;
    const payload = {
      email:      $('reg-email').value.trim(),
      password:   $('reg-password').value,
      first_name: $('reg-fname').value.trim(),
      last_name:  $('reg-lname').value.trim(),
      phone_number: $('reg-phone').value.trim() || undefined,
      role,
    };
    if (role === 'DOCTOR') {
      payload.license_number  = $('reg-license').value.trim();
      payload.specialization  = $('reg-spec').value.trim();
      payload.department      = $('reg-dept').value.trim();
      payload.years_of_experience = parseInt($('reg-exp').value) || 0;
    }

    await post('/auth/register', payload);
    toast('Account created! Please sign in.', 'success');
    switchAuthTab('login');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('visible');
  } finally {
    btn.disabled = false; btn.textContent = 'Create Account';
  }
}

// ── LOGOUT ───────────────────────────────────────────────────────
function handleLogout() {
  // Best-effort server logout
  if (_state.token) {
    fetch(`${API}/auth/logout`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${_state.token}` },
    }).catch(() => {});
  }
  _state.token = null; _state.refreshToken = null; _state.user = null;
  localStorage.removeItem('healora_token');
  localStorage.removeItem('healora_refresh');
  localStorage.removeItem('healora_user');
  hide('app-shell'); show('auth-screen');
  toast('Signed out successfully.', 'info');
}

// ── BOOT APP ─────────────────────────────────────────────────────
async function bootApp() {
  hide('auth-screen');
  show('app-shell');

  const u = _state.user;
  const fullName = `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.email;
  const role = u.role;

  // Sidebar user
  $('sb-user-name').textContent = fullName;
  $('sb-user-role').textContent = role;
  $('sb-user-role').className = `sidebar-user-role role-${role.toLowerCase()}`;
  $('topbar-avatar').textContent = initials(fullName);

  buildNav(role);
  setGreeting();

  // Navigate to appropriate home
  if (role === 'DOCTOR') navigateTo('doctor-dashboard');
  else navigateTo('dashboard');
}

// ── NAV BUILD ────────────────────────────────────────────────────
const patientNav = [
  { id: 'dashboard',        icon: '🏠', label: 'Dashboard' },
  { id: 'find-doctors',     icon: '🔍', label: 'Find Doctors' },
  { id: 'book-appointment', icon: '📅', label: 'Book Appointment' },
  { id: 'appointments',     icon: '🗂️', label: 'My Appointments' },
  { id: 'queries',          icon: '💬', label: 'Health Queries' },
  { id: 'records',          icon: '📋', label: 'Medical Records' },
  { id: 'profile',          icon: '👤', label: 'My Profile' },
  { id: 'notifications',    icon: '🔔', label: 'Notifications' },
];
const doctorNav = [
  { id: 'doctor-dashboard',     icon: '🏠', label: 'Dashboard' },
  { id: 'doctor-appointments',  icon: '📅', label: 'Appointments' },
  { id: 'doctor-queries',       icon: '💬', label: 'Patient Queries' },
  { id: 'doctor-profile',       icon: '👤', label: 'My Profile' },
  { id: 'notifications',        icon: '🔔', label: 'Notifications' },
];

function buildNav(role) {
  const items = role === 'DOCTOR' ? doctorNav : patientNav;
  const nav = $('sidebar-nav');
  nav.innerHTML = items.map(it => `
    <button class="nav-item" id="nav-${it.id}" onclick="navigateTo('${it.id}')">
      <span class="nav-icon">${it.icon}</span>
      <span>${esc(it.label)}</span>
    </button>
  `).join('');
}

// ── ROUTING ──────────────────────────────────────────────────────
function navigateTo(sectionId) {
  // hide all sections
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));

  const sec = $(`sec-${sectionId}`);
  if (!sec) return;
  sec.classList.add('active');

  const navBtn = $(`nav-${sectionId}`);
  if (navBtn) navBtn.classList.add('active');

  const title = sec.dataset.title || '';
  $('topbar-title').textContent = title;
  _state.currentSection = sectionId;
  closeSidebar();

  // Load data for section
  loadSection(sectionId);
}

async function loadSection(id) {
  try {
    switch (id) {
      case 'dashboard':         await loadPatientDashboard(); break;
      case 'doctor-dashboard':  await loadDoctorDashboard();  break;
      case 'find-doctors':      await loadDoctors();          break;
      case 'book-appointment':  await initBooking();          break;
      case 'appointments':      await loadPatientAppointments(); break;
      case 'queries':           await loadPatientQueries();   break;
      case 'records':           await loadMedicalRecords();   break;
      case 'profile':           await loadPatientProfile();   break;
      case 'doctor-appointments': await loadDoctorAppointments(); break;
      case 'doctor-queries':    await loadDoctorQueries();    break;
      case 'doctor-profile':    await loadDoctorProfile();    break;
      case 'notifications':     await loadNotifications();    break;
    }
  } catch (err) {
    console.error(`Error loading section ${id}:`, err);
    toast(`Failed to load data: ${err.message}`, 'error');
  }
}

// ── GREETING ─────────────────────────────────────────────────────
function setGreeting() {
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  const name = _state.user?.first_name || '';
  const greet = `${g}${name ? ', ' + name : ''} 👋`;
  if ($('dash-greeting'))   $('dash-greeting').textContent  = greet;
  if ($('doc-dash-greeting')) $('doc-dash-greeting').textContent = greet.replace('👋', '👨‍⚕️');
}

// ── SIDEBAR MOBILE ───────────────────────────────────────────────
function toggleSidebar() {
  $('sidebar').classList.toggle('open');
  $('sidebar-overlay').classList.toggle('visible');
}
function closeSidebar() {
  $('sidebar').classList.remove('open');
  $('sidebar-overlay').classList.remove('visible');
}

// ════════════════════════════════════════════
// PATIENT DASHBOARD
// ════════════════════════════════════════════
async function loadPatientDashboard() {
  // Load stats & recent data in parallel
  const [appts, queries] = await Promise.allSettled([
    get('/appointments/my'),
    get('/queries/my'),
  ]);

  // Stats
  const apptList = appts.status === 'fulfilled' ? (appts.value?.appointments || appts.value || []) : [];
  const queryList = queries.status === 'fulfilled' ? (queries.value?.queries || queries.value || []) : [];
  const upcoming = apptList.filter(a => ['PENDING','CONFIRMED'].includes(a.status)).length;

  $('st-upcoming').textContent        = upcoming;
  $('st-total-appt').textContent      = apptList.length;
  $('st-queries').textContent         = queryList.length;
  $('st-prescriptions').textContent   = '—';

  // Upcoming appointments (top 3)
  const upAppts = apptList.filter(a => ['PENDING','CONFIRMED'].includes(a.status)).slice(0, 3);
  $('dash-appt-list').innerHTML = upAppts.length
    ? upAppts.map(a => miniApptCard(a)).join('')
    : emptyMini('No upcoming appointments');

  // Recent queries (top 3)
  const recentQ = queryList.slice(0, 3);
  $('dash-query-list').innerHTML = recentQ.length
    ? recentQ.map(q => miniQueryCard(q)).join('')
    : emptyMini('No health queries yet');
}

function miniApptCard(a) {
  const docName = a.doctor_name || a.doctor?.full_name || `Dr. ID#${a.doctor_id}`;
  return `
    <div style="padding:12px;border-radius:var(--radius-sm);background:rgba(255,255,255,0.04);margin-bottom:8px;">
      <div style="font-size:14px;font-weight:700;">Dr. ${esc(docName)}</div>
      <div style="font-size:12px;color:var(--text-2);margin-top:2px;">${fmtDate(a.appointment_datetime || a.scheduled_time)}</div>
      <div style="margin-top:6px;">${badgeHtml(a.status)}</div>
    </div>`;
}

function miniQueryCard(q) {
  return `
    <div style="padding:12px;border-radius:var(--radius-sm);background:rgba(255,255,255,0.04);margin-bottom:8px;">
      <div style="font-size:14px;font-weight:700;">${esc(q.title || q.subject || 'Health Query')}</div>
      <div style="font-size:12px;color:var(--text-2);margin-top:2px;">${fmtDate(q.created_at)}</div>
      <div style="margin-top:6px;">${badgeHtml(q.status)}</div>
    </div>`;
}

function emptyMini(msg) {
  return `<div style="text-align:center;padding:24px;color:var(--text-3);font-size:13px;">${esc(msg)}</div>`;
}

// ════════════════════════════════════════════
// DOCTOR DASHBOARD
// ════════════════════════════════════════════
async function loadDoctorDashboard() {
  // Show approval banner if not approved
  const u = _state.user;
  if (!u?.is_approved) {
    $('approval-banner-wrap').innerHTML = `
      <div class="appr-banner">
        <span class="appr-icon">⏳</span>
        <span>Your account is pending admin approval. Some features may be restricted until approved.</span>
      </div>`;
  }

  const [appts, queries] = await Promise.allSettled([
    get('/appointments/doctor'),
    get('/queries/assigned'),
  ]);

  const apptList  = appts.status === 'fulfilled'  ? (appts.value?.appointments  || appts.value  || []) : [];
  const queryList = queries.status === 'fulfilled' ? (queries.value?.queries || queries.value || []) : [];

  const today = new Date().toDateString();
  const todayAppts = apptList.filter(a => {
    const d = a.appointment_datetime || a.scheduled_time;
    return d && new Date(d).toDateString() === today;
  });

  $('doc-today').textContent     = todayAppts.length;
  $('doc-pending-q').textContent = queryList.filter(q => q.status === 'SUBMITTED' || q.status === 'ASSIGNED').length;
  $('doc-total-appt').textContent = apptList.length;
  $('doc-patients').textContent  = [...new Set(apptList.map(a => a.patient_id))].length;

  // Today's schedule
  $('doc-appt-list').innerHTML = todayAppts.length
    ? todayAppts.slice(0, 4).map(a => miniDocApptCard(a)).join('')
    : emptyMini('No appointments today');

  // Recent queries
  $('doc-query-list').innerHTML = queryList.length
    ? queryList.slice(0, 4).map(q => miniQueryCard(q)).join('')
    : emptyMini('No pending queries');
}

function miniDocApptCard(a) {
  const pName = a.patient_name || a.patient?.full_name || `Patient #${a.patient_id}`;
  return `
    <div style="padding:12px;border-radius:var(--radius-sm);background:rgba(255,255,255,0.04);margin-bottom:8px;">
      <div style="font-size:14px;font-weight:700;">${esc(pName)}</div>
      <div style="font-size:12px;color:var(--text-2);margin-top:2px;">${fmtDate(a.appointment_datetime || a.scheduled_time)}</div>
      <div style="margin-top:6px;">${badgeHtml(a.status)}</div>
    </div>`;
}

// ════════════════════════════════════════════
// FIND DOCTORS
// ════════════════════════════════════════════
async function loadDoctors() {
  $('doctors-grid').innerHTML = '<div class="loading-state" style="grid-column:1/-1"><div class="spinner"></div><p>Loading doctors…</p></div>';
  const data = await get('/doctors/');
  _state.allDoctors = data?.doctors || data || [];

  // Build department filter
  const depts = [...new Set(_state.allDoctors.map(d => d.department).filter(Boolean))];
  const sel = $('dept-filter');
  sel.innerHTML = '<option value="">All Departments</option>' +
    depts.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('');

  renderDoctorGrid(_state.allDoctors);
}

function filterDoctors() {
  const q    = $('doctor-search').value.toLowerCase();
  const dept = $('dept-filter').value;
  const avail = $('avail-filter').value;
  let list = _state.allDoctors;
  if (q)     list = list.filter(d => (d.full_name||'').toLowerCase().includes(q) || (d.specialization||'').toLowerCase().includes(q));
  if (dept)  list = list.filter(d => d.department === dept);
  if (avail) list = list.filter(d => d.is_available !== false);
  renderDoctorGrid(list);
}

function renderDoctorGrid(doctors) {
  if (!doctors.length) {
    $('doctors-grid').innerHTML = `<div class="t-empty" style="grid-column:1/-1"><div class="t-empty-icon">🔍</div><div class="t-empty-text">No doctors found</div></div>`;
    return;
  }
  $('doctors-grid').innerHTML = doctors.map(d => `
    <div class="doctor-card" onclick="selectDoctorBook(${d.id})">
      <div style="display:flex;gap:14px;align-items:center;margin-bottom:14px;">
        <div class="doc-avatar">${initials(d.full_name)}</div>
        <div>
          <div class="doc-name">Dr. ${esc(d.full_name)}</div>
          <div class="doc-spec">${esc(d.specialization || '—')}</div>
          <div class="doc-dept">${esc(d.department || '')}</div>
        </div>
      </div>
      <div style="font-size:12px;color:var(--text-2);margin-bottom:12px;">
        ${d.years_of_experience ? `${d.years_of_experience} yrs exp · ` : ''}
        ${d.consultation_fee ? `₹${d.consultation_fee} fee` : ''}
      </div>
      <button class="btn btn-primary btn-sm" style="width:100%">📅 Book Appointment</button>
    </div>
  `).join('');
}

// ════════════════════════════════════════════
// BOOK APPOINTMENT
// ════════════════════════════════════════════
async function initBooking() {
  // Set min date to today
  const today = new Date().toISOString().split('T')[0];
  $('appt-date').min = today;

  if (!_state.allDoctors.length) {
    const data = await get('/doctors/');
    _state.allDoctors = data?.doctors || data || [];
  }
  renderBookDoctorList(_state.allDoctors);
}

function filterBookDoctors() {
  const q = $('book-doc-search').value.toLowerCase();
  const list = _state.allDoctors.filter(d =>
    (d.full_name||'').toLowerCase().includes(q) ||
    (d.specialization||'').toLowerCase().includes(q)
  );
  renderBookDoctorList(list);
}

function renderBookDoctorList(doctors) {
  $('book-doc-list').innerHTML = doctors.slice(0, 10).map(d => `
    <div class="doctor-card" onclick="selectDoctorForBooking(${JSON.stringify(d).replace(/"/g,'&quot;')})"
         style="${_state.bookDoctor?.id === d.id ? 'border-color:var(--cyan);background:var(--cyan-dim)' : ''}">
      <div style="display:flex;gap:12px;align-items:center;">
        <div class="doc-avatar" style="width:40px;height:40px;font-size:16px;">${initials(d.full_name)}</div>
        <div>
          <div class="doc-name" style="font-size:14px;">Dr. ${esc(d.full_name)}</div>
          <div class="doc-spec" style="font-size:12px;">${esc(d.specialization || '—')}</div>
        </div>
      </div>
    </div>
  `).join('');
}

function selectDoctorBook(doctorId) {
  const doc = _state.allDoctors.find(d => d.id === doctorId);
  if (doc) { selectDoctorForBooking(doc); navigateTo('book-appointment'); }
}

function selectDoctorForBooking(doc) {
  if (typeof doc === 'string') { try { doc = JSON.parse(doc); } catch { return; } }
  _state.bookDoctor = doc;
  _state.bookSlot   = null;
  $('selected-doc-display').textContent = `Dr. ${doc.full_name} — ${doc.specialization || 'General'}`;
  $('btn-book-appt').disabled = true;
  renderBookDoctorList(_state.allDoctors.filter(d =>
    ($('book-doc-search').value ? (d.full_name||'').toLowerCase().includes($('book-doc-search').value.toLowerCase()) : true)
  ));
  loadSlots();
}

async function loadSlots() {
  const doc  = _state.bookDoctor;
  const date = $('appt-date').value;
  if (!doc || !date) return;

  $('slot-grid').innerHTML = '<div class="spinner" style="margin:16px auto;"></div>';

  try {
    const data = await get(`/appointments/availability/${doc.id}?date=${date}`);
    const slots = data?.available_slots || data || [];

    if (!slots.length) {
      $('slot-grid').innerHTML = '<p class="text-muted text-sm">No slots available for this date.</p>';
      return;
    }
    $('slot-grid').innerHTML = slots.map(s => {
      const time = typeof s === 'string' ? s : (s.time || s.slot || s);
      const booked = s.booked || false;
      return `<button class="slot-btn ${booked ? 'booked' : ''}" onclick="selectSlot('${esc(time)}')">${esc(time)}</button>`;
    }).join('');
  } catch {
    $('slot-grid').innerHTML = '<p class="text-muted text-sm">Could not load slots. Pick a date and try again.</p>';
  }
}

function selectSlot(time) {
  _state.bookSlot = time;
  document.querySelectorAll('.slot-btn').forEach(b => {
    b.classList.toggle('selected', b.textContent === time);
  });
  $('btn-book-appt').disabled = !(_state.bookDoctor && _state.bookSlot);
}

async function submitBooking() {
  const doc  = _state.bookDoctor;
  const slot = _state.bookSlot;
  const date = $('appt-date').value;
  if (!doc || !slot || !date) { toast('Please select a doctor, date and time slot.', 'warning'); return; }

  const btn = $('btn-book-appt');
  btn.disabled = true; btn.textContent = 'Booking…';

  try {
    const datetime = `${date}T${slot}:00`;
    await post('/appointments/', {
      doctor_id:            doc.id,
      appointment_datetime: datetime,
      appointment_type:     $('appt-type').value,
      reason_for_visit:     $('appt-reason').value.trim(),
    });
    toast('Appointment booked successfully! 🎉', 'success');
    resetBookingForm();
    navigateTo('appointments');
  } catch (err) {
    toast(`Booking failed: ${err.message}`, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '📅 Confirm Booking';
  }
}

function resetBookingForm() {
  _state.bookDoctor = null; _state.bookSlot = null;
  $('appt-date').value = ''; $('appt-reason').value = '';
  $('selected-doc-display').textContent = 'No doctor selected yet.';
  $('slot-grid').innerHTML = '<p class="text-muted text-sm">Select a doctor and date first.</p>';
  $('btn-book-appt').disabled = true;
  renderBookDoctorList(_state.allDoctors);
}

// ════════════════════════════════════════════
// PATIENT APPOINTMENTS
// ════════════════════════════════════════════
let _patientAppts = [];

async function loadPatientAppointments() {
  $('appt-tbody').innerHTML = '<tr><td colspan="6"><div class="loading-state"><div class="spinner"></div></div></td></tr>';
  const data = await get('/appointments/my');
  _patientAppts = data?.appointments || data || [];
  renderPatientAppts(_patientAppts);
}

function filterAppointments() {
  const q  = $('appt-search').value.toLowerCase();
  const st = $('appt-status-filter').value;
  let list = _patientAppts;
  if (q)  list = list.filter(a => JSON.stringify(a).toLowerCase().includes(q));
  if (st) list = list.filter(a => a.status === st);
  renderPatientAppts(list);
}

function renderPatientAppts(list) {
  if (!list.length) {
    $('appt-tbody').innerHTML = `<tr><td colspan="6"><div class="t-empty"><div class="t-empty-icon">📅</div><div class="t-empty-text">No appointments found</div><div class="t-empty-sub">Book your first appointment above.</div></div></td></tr>`;
    return;
  }
  $('appt-tbody').innerHTML = list.map(a => {
    const docName = a.doctor_name || a.doctor?.full_name || `Doctor #${a.doctor_id}`;
    const dt = a.appointment_datetime || a.scheduled_time;
    const canCancel = ['PENDING','CONFIRMED'].includes(a.status);
    return `<tr>
      <td><strong>Dr. ${esc(docName)}</strong></td>
      <td>${fmtDate(dt)}</td>
      <td>${esc(a.appointment_type || a.type || '—')}</td>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(a.reason_for_visit || '—')}</td>
      <td>${badgeHtml(a.status)}</td>
      <td>
        <div style="display:flex;gap:6px;">
          <button class="btn btn-sm btn-secondary" onclick="viewApptDetail(${a.id})">View</button>
          ${canCancel ? `<button class="btn btn-sm btn-danger" onclick="cancelAppointment(${a.id})">Cancel</button>` : ''}
        </div>
      </td>
    </tr>`;
  }).join('');
}

async function cancelAppointment(id) {
  if (!confirm('Cancel this appointment?')) return;
  try {
    await put(`/appointments/${id}/cancel`);
    toast('Appointment cancelled.', 'info');
    await loadPatientAppointments();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

async function viewApptDetail(id) {
  const appt = _patientAppts.find(a => a.id === id);
  if (!appt) return;
  const docName = appt.doctor_name || appt.doctor?.full_name || `Doctor #${appt.doctor_id}`;
  $('appt-detail-title').textContent = 'Appointment Details';
  $('appt-detail-body').innerHTML = `
    <div class="detail-grid">
      <div class="detail-item"><label>Doctor</label><span>Dr. ${esc(docName)}</span></div>
      <div class="detail-item"><label>Date & Time</label><span>${fmtDate(appt.appointment_datetime || appt.scheduled_time)}</span></div>
      <div class="detail-item"><label>Type</label><span>${esc(appt.appointment_type || appt.type || '—')}</span></div>
      <div class="detail-item"><label>Status</label><span>${badgeHtml(appt.status)}</span></div>
    </div>
    <div class="form-group"><label class="form-label">Reason for Visit</label>
      <div style="padding:12px;background:rgba(255,255,255,0.04);border-radius:var(--radius-sm);">${esc(appt.reason_for_visit || '—')}</div>
    </div>
    ${appt.notes ? `<div class="form-group"><label class="form-label">Doctor Notes</label>
      <div style="padding:12px;background:rgba(255,255,255,0.04);border-radius:var(--radius-sm);">${esc(appt.notes)}</div>
    </div>` : ''}
    <div class="modal-actions"><button class="btn btn-secondary" onclick="closeModal('modal-appt-detail')">Close</button></div>
  `;
  openModal('modal-appt-detail');
}

// ════════════════════════════════════════════
// PATIENT QUERIES
// ════════════════════════════════════════════
async function loadPatientQueries() {
  $('queries-list').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  const data = await get('/queries/my');
  const list = data?.queries || data || [];
  if (!list.length) {
    $('queries-list').innerHTML = `<div class="t-empty"><div class="t-empty-icon">💬</div><div class="t-empty-text">No queries yet</div><div class="t-empty-sub">Submit a health query to get expert advice.</div></div>`;
    return;
  }
  $('queries-list').innerHTML = list.map(q => queryCardHtml(q, false)).join('');
}

function queryCardHtml(q, isDoctor = false) {
  const hasReply = q.response || q.doctor_response;
  return `
    <div class="query-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
        <div>
          <div class="q-title">${esc(q.title || q.subject || 'Health Query')}</div>
          <div class="q-meta">${fmtDate(q.created_at)} · ${badgeHtml(q.priority || 'MEDIUM')} · ${badgeHtml(q.status)}</div>
        </div>
        ${isDoctor ? `<button class="btn btn-sm btn-primary" onclick="openReplyModal(${q.id}, '${esc(q.title||'')}', '${esc(q.description||'')}')">💬 Reply</button>` : ''}
      </div>
      <div class="q-body">${esc(q.description || q.body || '')}</div>
      ${q.ai_suggestion ? `<div class="ai-box"><div class="ai-lbl">🤖 AI Suggestion</div><div class="ai-txt">${esc(q.ai_suggestion)}</div></div>` : ''}
      ${hasReply ? `<div class="resp-block"><div class="resp-hdr">👨‍⚕️ Doctor's Response</div><p style="font-size:13px;color:var(--text-2);">${esc(q.response || q.doctor_response)}</p></div>` : ''}
    </div>`;
}

async function openQueryModal() {
  // Pre-fill doctor list
  if (!_state.allDoctors.length) {
    const data = await get('/doctors/');
    _state.allDoctors = data?.doctors || data || [];
  }
  $('q-doctor').innerHTML = '<option value="">— Auto assign —</option>' +
    _state.allDoctors.map(d => `<option value="${d.id}">Dr. ${esc(d.full_name)} — ${esc(d.specialization || '')}</option>`).join('');
  openModal('modal-query');
}

async function submitQuery() {
  const title    = $('q-title').value.trim();
  const body     = $('q-body').value.trim();
  const priority = $('q-priority').value;
  const docId    = $('q-doctor').value;
  if (!title || !body) { toast('Please fill in all required fields.', 'warning'); return; }

  try {
    await post('/queries/', {
      title, description: body, priority,
      doctor_id: docId ? parseInt(docId) : undefined,
    });
    toast('Query submitted successfully! ✉️', 'success');
    closeModal('modal-query');
    $('q-title').value = ''; $('q-body').value = '';
    navigateTo('queries');
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ════════════════════════════════════════════
// MEDICAL RECORDS
// ════════════════════════════════════════════
async function loadMedicalRecords() {
  $('prescriptions-list').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  $('lab-results-list').innerHTML   = '<div class="loading-state"><div class="spinner"></div></div>';
  try {
    const data = await get('/medical-records/my');
    const records = data?.records || data || [];
    const prescriptions = records.filter(r => r.record_type === 'PRESCRIPTION' || r.type === 'PRESCRIPTION');
    const labs = records.filter(r => r.record_type === 'LAB_RESULT' || r.type === 'LAB_RESULT');

    $('prescriptions-list').innerHTML = prescriptions.length
      ? prescriptions.map(r => `<div style="padding:12px;border-radius:var(--radius-sm);background:rgba(255,255,255,0.04);margin-bottom:8px;font-size:14px;">${esc(r.title || r.description || 'Prescription')} <span style="color:var(--text-3);font-size:12px;">— ${fmtDateOnly(r.created_at)}</span></div>`).join('')
      : emptyMini('No prescriptions on record');

    $('lab-results-list').innerHTML = labs.length
      ? labs.map(r => `<div style="padding:12px;border-radius:var(--radius-sm);background:rgba(255,255,255,0.04);margin-bottom:8px;font-size:14px;">${esc(r.title || r.description || 'Lab Result')} <span style="color:var(--text-3);font-size:12px;">— ${fmtDateOnly(r.created_at)}</span></div>`).join('')
      : emptyMini('No lab results on record');
  } catch {
    $('prescriptions-list').innerHTML = emptyMini('Could not load records');
    $('lab-results-list').innerHTML   = emptyMini('Could not load records');
  }
}

// ════════════════════════════════════════════
// PATIENT PROFILE
// ════════════════════════════════════════════
async function loadPatientProfile() {
  const data = await get('/patients/profile');
  const u = data || _state.user;

  const fullName = `${u.first_name||''} ${u.last_name||''}`.trim() || u.email;
  $('profile-avatar-lg').textContent   = initials(fullName);
  $('profile-full-name').textContent   = fullName;
  $('profile-email-display').textContent = u.email || '—';
  $('profile-phone-display').textContent = u.phone_number || '';

  $('personal-info-grid').innerHTML = detailItem('First Name', u.first_name) +
    detailItem('Last Name', u.last_name) + detailItem('Email', u.email) +
    detailItem('Phone', u.phone_number) + detailItem('Gender', u.gender) +
    detailItem('Date of Birth', fmtDateOnly(u.date_of_birth)) +
    detailItem('Address', u.address);

  const h = u.health_info || u;
  $('health-info-grid').innerHTML = detailItem('Blood Type', h.blood_type) +
    detailItem('Height', h.height ? `${h.height} cm` : null) +
    detailItem('Weight', h.weight ? `${h.weight} kg` : null) +
    detailItem('Allergies', h.allergies) + detailItem('Conditions', h.chronic_conditions) +
    detailItem('Medications', h.current_medications) +
    detailItem('Emergency Contact', h.emergency_contact_phone);

  // Prefill edit modals
  $('ep-fname').value = u.first_name || '';
  $('ep-lname').value = u.last_name  || '';
  $('ep-phone').value = u.phone_number || '';
  $('ep-address').value = u.address || '';
  if (u.date_of_birth) $('ep-dob').value = u.date_of_birth.split('T')[0];
  if (u.gender) $('ep-gender').value = u.gender;

  $('eh-blood').value     = h.blood_type || '';
  $('eh-height').value    = h.height || '';
  $('eh-weight').value    = h.weight || '';
  $('eh-emergency').value = h.emergency_contact_phone || '';
  $('eh-allergies').value = h.allergies || '';
  $('eh-conditions').value = h.chronic_conditions || '';
  $('eh-meds').value      = h.current_medications || '';
}

function detailItem(label, val) {
  return `<div class="detail-item"><label>${esc(label)}</label><span>${esc(val || '—')}</span></div>`;
}

function openEditProfileModal()  { openModal('modal-edit-profile'); }
function openEditHealthModal()   { openModal('modal-edit-health'); }

async function saveProfile() {
  try {
    await put('/patients/profile', {
      first_name:  $('ep-fname').value.trim(),
      last_name:   $('ep-lname').value.trim(),
      phone_number: $('ep-phone').value.trim(),
      address:     $('ep-address').value.trim(),
      date_of_birth: $('ep-dob').value || undefined,
      gender:      $('ep-gender').value,
    });
    toast('Profile updated! ✅', 'success');
    closeModal('modal-edit-profile');
    await loadPatientProfile();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

async function saveHealthInfo() {
  try {
    await put('/patients/health-info', {
      blood_type:              $('eh-blood').value || undefined,
      height:                  parseFloat($('eh-height').value) || undefined,
      weight:                  parseFloat($('eh-weight').value) || undefined,
      emergency_contact_phone: $('eh-emergency').value.trim() || undefined,
      allergies:               $('eh-allergies').value.trim() || undefined,
      chronic_conditions:      $('eh-conditions').value.trim() || undefined,
      current_medications:     $('eh-meds').value.trim() || undefined,
    });
    toast('Health information updated! ✅', 'success');
    closeModal('modal-edit-health');
    await loadPatientProfile();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ════════════════════════════════════════════
// DOCTOR APPOINTMENTS
// ════════════════════════════════════════════
let _docAppts = [];

async function loadDoctorAppointments() {
  $('doc-appt-tbody').innerHTML = '<tr><td colspan="6"><div class="loading-state"><div class="spinner"></div></div></td></tr>';
  const data = await get('/appointments/doctor');
  _docAppts = data?.appointments || data || [];
  renderDocAppts(_docAppts);
}

function filterDocAppointments() {
  const st = $('doc-appt-filter').value;
  renderDocAppts(st ? _docAppts.filter(a => a.status === st) : _docAppts);
}

function renderDocAppts(list) {
  if (!list.length) {
    $('doc-appt-tbody').innerHTML = `<tr><td colspan="6"><div class="t-empty"><div class="t-empty-icon">📅</div><div class="t-empty-text">No appointments</div></div></td></tr>`;
    return;
  }
  $('doc-appt-tbody').innerHTML = list.map(a => {
    const pName = a.patient_name || a.patient?.full_name || `Patient #${a.patient_id}`;
    const dt = a.appointment_datetime || a.scheduled_time;
    const isPending = a.status === 'PENDING';
    const isConfirmed = a.status === 'CONFIRMED';
    return `<tr>
      <td><strong>${esc(pName)}</strong></td>
      <td>${fmtDate(dt)}</td>
      <td>${esc(a.appointment_type || a.type || '—')}</td>
      <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(a.reason_for_visit || '—')}</td>
      <td>${badgeHtml(a.status)}</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          ${isPending ? `<button class="btn btn-sm btn-success" onclick="updateApptStatus(${a.id},'CONFIRMED')">✓ Confirm</button>` : ''}
          ${isConfirmed ? `<button class="btn btn-sm btn-success" onclick="updateApptStatus(${a.id},'COMPLETED')">✓ Complete</button>` : ''}
          ${(isPending||isConfirmed) ? `<button class="btn btn-sm btn-danger" onclick="updateApptStatus(${a.id},'CANCELLED')">✕ Cancel</button>` : ''}
        </div>
      </td>
    </tr>`;
  }).join('');
}

async function updateApptStatus(id, status) {
  try {
    await put(`/appointments/${id}/status`, { status });
    toast(`Appointment ${status.toLowerCase()}.`, 'success');
    await loadDoctorAppointments();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ════════════════════════════════════════════
// DOCTOR QUERIES
// ════════════════════════════════════════════
let _docQueries = [];

async function loadDoctorQueries() {
  $('doc-queries-list').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  const data = await get('/queries/assigned');
  _docQueries = data?.queries || data || [];
  renderDocQueries(_docQueries);
}

function filterDocQueries() {
  const st = $('query-status-filter').value;
  renderDocQueries(st ? _docQueries.filter(q => q.status === st) : _docQueries);
}

function renderDocQueries(list) {
  if (!list.length) {
    $('doc-queries-list').innerHTML = `<div class="t-empty"><div class="t-empty-icon">💬</div><div class="t-empty-text">No queries assigned</div></div>`;
    return;
  }
  $('doc-queries-list').innerHTML = list.map(q => queryCardHtml(q, true)).join('');
}

function openReplyModal(qId, title, desc) {
  _state.replyQueryId = qId;
  $('reply-query-preview').innerHTML = `<div class="ai-lbl">Patient Query</div><div class="ai-txt">${esc(desc)}</div>`;
  $('reply-body').value = '';
  $('reply-status').value = 'ASSIGNED';
  openModal('modal-reply');
}

async function submitReply() {
  const id   = _state.replyQueryId;
  const body = $('reply-body').value.trim();
  const status = $('reply-status').value;
  if (!body) { toast('Please enter a response.', 'warning'); return; }

  try {
    await put(`/queries/${id}/respond`, { response: body, status });
    toast('Reply sent! ✅', 'success');
    closeModal('modal-reply');
    await loadDoctorQueries();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ════════════════════════════════════════════
// DOCTOR PROFILE
// ════════════════════════════════════════════
async function loadDoctorProfile() {
  const data = await get('/doctors/profile');
  const d = data || _state.user;

  const fullName = d.full_name || `${d.first_name||''} ${d.last_name||''}`.trim() || d.email;
  $('doc-profile-avatar').textContent = initials(fullName);
  $('doc-profile-name').textContent  = `Dr. ${fullName}`;
  $('doc-profile-spec').textContent  = d.specialization || '—';
  $('doc-profile-dept').textContent  = d.department || '';

  $('doc-details-grid').innerHTML =
    detailItem('License #', d.license_number) +
    detailItem('Specialization', d.specialization) +
    detailItem('Department', d.department) +
    detailItem('Years of Experience', d.years_of_experience) +
    detailItem('Consultation Fee', d.consultation_fee ? `₹${d.consultation_fee}` : null) +
    detailItem('Languages', Array.isArray(d.languages) ? d.languages.join(', ') : d.languages) +
    detailItem('Rating', d.rating ? `⭐ ${d.rating}` : null);

  // Prefill edit modal
  $('edp-spec').value  = d.specialization || '';
  $('edp-dept').value  = d.department     || '';
  $('edp-fee').value   = d.consultation_fee || '';
  $('edp-exp').value   = d.years_of_experience || '';
  $('edp-bio').value   = d.bio || '';
  $('edp-langs').value = Array.isArray(d.languages) ? d.languages.join(', ') : (d.languages || '');

  // Availability
  renderAvailabilityDisplay(d.availability || []);
}

function renderAvailabilityDisplay(slots) {
  if (!slots.length) {
    $('avail-display').innerHTML = emptyMini('No schedule set — click Manage to configure.');
    return;
  }
  $('avail-display').innerHTML = slots.map(s => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--glass-border);font-size:13px;">
      <strong style="min-width:100px;">${esc(s.day_of_week)}</strong>
      <span>${esc(s.start_time)} – ${esc(s.end_time)}</span>
      <span style="color:var(--text-3);">${esc(s.slot_duration_minutes||30)} min slots</span>
    </div>`).join('');
}

function openEditDocProfileModal() { openModal('modal-edit-doc-profile'); }

async function saveDocProfile() {
  try {
    const langs = $('edp-langs').value.split(',').map(l => l.trim()).filter(Boolean);
    await put('/doctors/profile', {
      specialization:     $('edp-spec').value.trim(),
      department:         $('edp-dept').value.trim(),
      consultation_fee:   parseFloat($('edp-fee').value) || undefined,
      years_of_experience: parseInt($('edp-exp').value)  || undefined,
      bio:                $('edp-bio').value.trim(),
      languages:          langs,
    });
    toast('Profile updated! ✅', 'success');
    closeModal('modal-edit-doc-profile');
    await loadDoctorProfile();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ── AVAILABILITY MODAL ───────────────────────────────────────────
const DAYS = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY'];

function openAvailabilityModal() {
  $('avail-form-body').innerHTML = DAYS.map(day => `
    <div class="avail-row">
      <div class="avail-day">${day.charAt(0)+day.slice(1).toLowerCase()}</div>
      <label style="display:flex;align-items:center;gap:6px;font-size:13px;">
        <input type="checkbox" id="avail-${day}" onchange="toggleAvailDay('${day}')"> Active
      </label>
      <div>
        <label class="form-label" style="font-size:11px;">Start</label>
        <input type="time" class="form-control" id="avail-start-${day}" value="09:00" style="padding:6px 10px;font-size:13px;" disabled>
      </div>
      <div>
        <label class="form-label" style="font-size:11px;">End</label>
        <input type="time" class="form-control" id="avail-end-${day}" value="17:00" style="padding:6px 10px;font-size:13px;" disabled>
      </div>
      <div>
        <label class="form-label" style="font-size:11px;">Slot (min)</label>
        <select class="form-control" id="avail-dur-${day}" style="padding:6px 10px;font-size:13px;" disabled>
          <option value="15">15</option><option value="30" selected>30</option>
          <option value="45">45</option><option value="60">60</option>
        </select>
      </div>
    </div>`).join('');
  openModal('modal-availability');
}

function toggleAvailDay(day) {
  const checked = $(`avail-${day}`).checked;
  $(`avail-start-${day}`).disabled = !checked;
  $(`avail-end-${day}`).disabled   = !checked;
  $(`avail-dur-${day}`).disabled   = !checked;
}

async function saveAvailability() {
  const slots = [];
  DAYS.forEach(day => {
    if ($(`avail-${day}`)?.checked) {
      slots.push({
        day_of_week: day,
        start_time:  $(`avail-start-${day}`).value,
        end_time:    $(`avail-end-${day}`).value,
        slot_duration_minutes: parseInt($(`avail-dur-${day}`).value),
        is_available: true,
      });
    }
  });
  try {
    await put('/doctors/availability', { availability: slots });
    toast('Availability saved! ✅', 'success');
    closeModal('modal-availability');
    await loadDoctorProfile();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ════════════════════════════════════════════
// NOTIFICATIONS
// ════════════════════════════════════════════
async function loadNotifications() {
  $('notif-list').innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
  try {
    const data = await get('/notifications/');
    _state.notifications = data?.notifications || data || [];
    renderNotifications(_state.notifications);
    const unread = _state.notifications.filter(n => !n.is_read).length;
    $('notif-dot').style.display = unread ? 'block' : 'none';
  } catch {
    $('notif-list').innerHTML = emptyMini('Could not load notifications');
  }
}

function renderNotifications(list) {
  if (!list.length) {
    $('notif-list').innerHTML = `<div class="t-empty"><div class="t-empty-icon">🔔</div><div class="t-empty-text">No notifications</div></div>`;
    return;
  }
  $('notif-list').innerHTML = list.map(n => `
    <div class="notif-row ${n.is_read ? '' : 'unread'}">
      <div class="notif-ico" style="background:var(--blue-dim);">🔔</div>
      <div class="notif-body">
        <div class="notif-title">${esc(n.title || n.notification_type || 'Notification')}</div>
        <div class="notif-msg">${esc(n.message || n.body || '')}</div>
        <div class="notif-time">${fmtDate(n.created_at)}</div>
      </div>
    </div>`).join('');
}

async function markAllRead() {
  try {
    await put('/notifications/mark-all-read');
    toast('All notifications marked as read.', 'success');
    await loadNotifications();
  } catch (err) { toast(`Failed: ${err.message}`, 'error'); }
}

// ════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════
(async function init() {
  // If already logged in, try to boot directly
  if (_state.token && _state.user) {
    try {
      const me = await get('/auth/me');
      _state.user = me;
      localStorage.setItem('healora_user', JSON.stringify(me));
      bootApp();
    } catch {
      // Token invalid — show auth
      hide('app-shell'); show('auth-screen');
    }
  } else {
    hide('app-shell'); show('auth-screen');
  }
})();
