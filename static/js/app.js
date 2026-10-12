// HEALORA Smart Hospital Client
const API_BASE = '/api/v1';

// Seeded test accounts for quick 1-click persona switching
const PERSONAS = {
  PATIENT: {
    email: 'patient@healora.com',
    password: 'PatientPass123!',
    name: 'John Doe',
    roleLabel: 'Patient Portal',
    initials: 'JD'
  },
  DOCTOR: {
    email: 'dr.sarah@healora.com',
    password: 'DoctorPass123!',
    name: 'Dr. Sarah Lin (Cardiology)',
    roleLabel: 'Physician Portal',
    initials: 'SL'
  },
  ADMIN: {
    email: 'admin@healora.com',
    password: 'AdminPass123!',
    name: 'Hospital Administrator',
    roleLabel: 'Admin & Governance',
    initials: 'HA'
  }
};

let currentRole = 'PATIENT';
let authToken = null;
let currentProfile = null;
let doctorsList = [];

// Tab configuration per role
const TABS = {
  PATIENT: [
    { id: 'patient-tab-triage', label: '⚡ AI Triage & Intake' },
    { id: 'patient-tab-appointments', label: '📅 Consultations' },
    { id: 'patient-tab-records', label: '💊 Prescriptions & Records' }
  ],
  DOCTOR: [
    { id: 'doctor-tab-inbox', label: '📥 Triage Inbox & Review' },
    { id: 'doctor-tab-schedule', label: '🗓️ Clinic Schedule' },
    { id: 'doctor-tab-prescribe', label: '✍️ Issue Prescription' }
  ],
  ADMIN: [
    { id: 'admin-tab-metrics', label: '📊 System Metrics & Audits' }
  ]
};

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// Authenticated fetch wrapper
async function apiCall(endpoint, options = {}) {
  const headers = options.headers || {};
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (res.status === 401 && endpoint !== '/auth/login') {
      showToast('Session expired, re-authenticating...', 'warning');
      await loginPersona(currentRole);
      return apiCall(endpoint, options);
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = data.detail || (typeof data === 'string' ? data : 'API Error');
      throw new Error(err);
    }
    return data;
  } catch (error) {
    showToast(error.message, 'error');
    throw error;
  }
}

// Log in as a given persona
async function loginPersona(role) {
  const p = PERSONAS[role];
  try {
    const data = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: p.email, password: p.password })
    });
    authToken = data.access_token;
    currentProfile = data;
    return data;
  } catch (err) {
    console.error('Failed to login persona:', err);
  }
}

// Switch Persona UI
async function switchPersona(role) {
  currentRole = role;

  // Update role buttons
  document.querySelectorAll('.role-pill').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`btn-role-${role.toLowerCase()}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update user badge
  const p = PERSONAS[role];
  document.getElementById('user-avatar-initials').innerText = p.initials;
  document.getElementById('user-display-name').innerText = p.name;
  document.getElementById('user-display-role').innerText = p.roleLabel;

  // Toggle portal views
  document.getElementById('view-patient-portal').style.display = role === 'PATIENT' ? 'block' : 'none';
  document.getElementById('view-doctor-portal').style.display = role === 'DOCTOR' ? 'block' : 'none';
  document.getElementById('view-admin-portal').style.display = role === 'ADMIN' ? 'block' : 'none';

  // Render Tabs
  renderTabs(role);

  // Authenticate
  await loginPersona(role);

  // Load relevant data
  if (role === 'PATIENT') {
    await loadDoctors();
    await loadPatientQueries();
    await loadAppointments();
    await loadPatientPrescriptions();
    await loadPatientRecords();
  } else if (role === 'DOCTOR') {
    await loadDoctorInbox();
    await loadDoctorSchedule();
  } else if (role === 'ADMIN') {
    await loadAdminStats();
    await loadAuditLogs();
  }

  showToast(`Switched to ${p.roleLabel}`, 'success');
}

// Render dynamic tabs
function renderTabs(role) {
  const tabBar = document.getElementById('portal-tab-bar');
  tabBar.innerHTML = '';
  const tabs = TABS[role] || [];
  tabs.forEach((tab, index) => {
    const btn = document.createElement('button');
    btn.className = `portal-tab ${index === 0 ? 'active' : ''}`;
    btn.innerText = tab.label;
    btn.onclick = () => activateTab(tab.id, btn);
    tabBar.appendChild(btn);
  });

  // Activate first tab by default
  if (tabs.length > 0) {
    activateTab(tabs[0].id, tabBar.firstChild);
  }
}

function activateTab(tabId, btn) {
  document.querySelectorAll('.portal-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  document.querySelectorAll('.tab-pane').forEach(p => {
    p.style.display = 'none';
  });
  const activePane = document.getElementById(tabId);
  if (activePane) activePane.style.display = 'block';
}

// ----------------- PATIENT LOGIC -----------------

// Submit AI Triage
async function handleTriageSubmit(e) {
  e.preventDefault();
  const title = document.getElementById('input-query-title').value.trim();
  const description = document.getElementById('input-query-desc').value.trim();
  const spinner = document.getElementById('triage-spinner');
  spinner.style.display = 'inline';

  try {
    const res = await apiCall('/queries', {
      method: 'POST',
      body: JSON.stringify({ title, description })
    });

    // Update Live AI Assessment Card
    document.getElementById('ai-assessment-placeholder').style.display = 'none';
    const resultBox = document.getElementById('ai-assessment-result');
    resultBox.style.display = 'block';

    const urgencyBadge = document.getElementById('triage-urgency-badge');
    urgencyBadge.innerText = res.urgency;
    urgencyBadge.className = `badge badge-${res.urgency.toLowerCase()}`;

    document.getElementById('routed-dept-pill').innerText = res.department;
    document.getElementById('ai-structured-summary').innerText = res.ai_summary;
    document.getElementById('assigned-doctor-name').innerText = res.doctor_id ? `Assigned Doctor ID #${res.doctor_id}` : 'General Clinical Triage Pool';

    showToast('AI Clinical Triage Completed & Ticket Created!', 'success');
    document.getElementById('form-patient-triage').reset();
    await loadPatientQueries();
  } finally {
    spinner.style.display = 'none';
  }
}

// Load patient query stream
async function loadPatientQueries() {
  const container = document.getElementById('patient-queries-list');
  try {
    const queries = await apiCall('/queries');
    if (!queries || queries.length === 0) {
      container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 2rem;">No symptom queries submitted yet.</div>';
      return;
    }

    container.innerHTML = queries.map(q => `
      <div class="stream-item">
        <div class="stream-header">
          <span class="stream-title">${escapeHtml(q.title)}</span>
          <span class="badge badge-${q.urgency.toLowerCase()}">${q.urgency}</span>
        </div>
        <p class="stream-desc">${escapeHtml(q.description)}</p>
        <div class="stream-meta">
          <span>🏥 Dept: <strong>${escapeHtml(q.department || 'General')}</strong></span>
          <span>● Status: <strong>${q.status}</strong></span>
          <span>📅 ${new Date(q.created_at).toLocaleDateString()}</span>
        </div>
        ${q.responses && q.responses.length > 0 ? `
          <div style="margin-top: 0.85rem; padding: 0.75rem; background: rgba(16, 185, 129, 0.08); border-left: 3px solid var(--emerald); border-radius: 4px;">
            <div style="font-weight: 700; font-size: 0.8rem; color: var(--emerald); margin-bottom: 0.25rem;">🩺 Verified Physician Response:</div>
            <div style="font-size: 0.85rem; color: #e2e8f0;">${escapeHtml(q.responses[0].response_text)}</div>
            ${q.responses[0].recommendations ? `<div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.35rem;">💡 Recommendation: ${escapeHtml(q.responses[0].recommendations)}</div>` : ''}
          </div>
        ` : '<div style="margin-top: 0.6rem; font-size: 0.75rem; color: var(--amber);">⏳ Awaiting physician review</div>'}
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div style="color: var(--rose); text-align: center; padding: 1rem;">Failed to load query history.</div>';
  }
}

// Load approved doctors
async function loadDoctors() {
  try {
    doctorsList = await apiCall('/doctors');
    const select = document.getElementById('select-doctor');
    select.innerHTML = '<option value="">Select Specialist...</option>';
    doctorsList.forEach(doc => {
      const opt = document.createElement('option');
      opt.value = doc.id;
      opt.innerText = `${doc.user ? doc.user.full_name : 'Doctor'} - ${doc.specialization} (${doc.department}) - $${doc.consultation_fee}`;
      select.appendChild(opt);
    });

    // Set default date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dateInput = document.getElementById('input-appt-date');
    if (!dateInput.value) {
      dateInput.value = tomorrow.toISOString().split('T')[0];
    }
  } catch (e) {
    console.error('Error loading doctors:', e);
  }
}

// Load doctor slots
async function loadDoctorSlots() {
  const doctorId = document.getElementById('select-doctor').value;
  const dateVal = document.getElementById('input-appt-date').value;
  const slotSelect = document.getElementById('select-slot');

  if (!doctorId || !dateVal) {
    slotSelect.innerHTML = '<option value="">Select doctor & date first</option>';
    return;
  }

  try {
    const slots = await apiCall(`/appointments/available-slots?doctor_id=${doctorId}&date=${dateVal}`);
    slotSelect.innerHTML = '';
    if (slots.length === 0) {
      slotSelect.innerHTML = '<option value="">No available slots for this date</option>';
      return;
    }
    slots.forEach(slot => {
      const opt = document.createElement('option');
      opt.value = slot;
      opt.innerText = slot;
      slotSelect.appendChild(opt);
    });
  } catch (e) {
    // Default fallback slots
    slotSelect.innerHTML = `
      <option value="09:00:00">09:00 AM</option>
      <option value="10:00:00">10:00 AM</option>
      <option value="11:30:00">11:30 AM</option>
      <option value="14:00:00">02:00 PM</option>
      <option value="15:30:00">03:30 PM</option>
    `;
  }
}

// Book appointment
async function handleBookAppointment(e) {
  e.preventDefault();
  const doctorId = parseInt(document.getElementById('select-doctor').value);
  const appointmentDate = document.getElementById('input-appt-date').value;
  const startTime = document.getElementById('select-slot').value;
  const reason = document.getElementById('input-appt-reason').value.trim();

  try {
    await apiCall('/appointments', {
      method: 'POST',
      body: JSON.stringify({
        doctor_id: doctorId,
        appointment_date: appointmentDate,
        start_time: startTime,
        reason
      })
    });
    showToast('Consultation successfully booked!', 'success');
    document.getElementById('form-book-appointment').reset();
    await loadAppointments();
  } catch (err) {
    // Error toast is handled by apiCall
  }
}

// Load appointments
async function loadAppointments() {
  const container = document.getElementById('patient-appointments-list');
  try {
    const appts = await apiCall('/appointments');
    if (!appts || appts.length === 0) {
      container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 2rem;">No consultations scheduled yet.</div>';
      return;
    }

    container.innerHTML = appts.map(a => `
      <div class="stream-item">
        <div class="stream-header">
          <span class="stream-title">Consultation with Doctor #${a.doctor_id}</span>
          <span class="badge badge-${a.status === 'CONFIRMED' ? 'success' : 'medium'}">${a.status}</span>
        </div>
        <div class="stream-desc"><strong>Reason:</strong> ${escapeHtml(a.reason || 'General Follow-up')}</div>
        <div class="stream-meta">
          <span>📅 Date: ${a.appointment_date}</span>
          <span>⏰ Time: ${a.start_time} - ${a.end_time}</span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div style="color: var(--rose); text-align: center; padding: 1rem;">Failed to load appointments.</div>';
  }
}

// Load prescriptions
async function loadPatientPrescriptions() {
  const container = document.getElementById('patient-prescriptions-list');
  try {
    const rxList = await apiCall('/prescriptions');
    if (!rxList || rxList.length === 0) {
      container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 2rem;">No active prescriptions found.</div>';
      return;
    }

    container.innerHTML = rxList.map(rx => `
      <div class="stream-item">
        <div class="stream-header">
          <span class="stream-title">Rx Diagnosis: ${escapeHtml(rx.diagnosis || 'Clinical Prescription')}</span>
          <span class="badge badge-success">Active Rx</span>
        </div>
        <div style="margin: 0.5rem 0;">
          ${(rx.medications || []).map(m => `
            <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 6px; margin-top: 0.35rem; font-size: 0.85rem;">
              <strong>💊 ${escapeHtml(m.name)}</strong> - ${escapeHtml(m.dosage)} (${escapeHtml(m.frequency)}) | <em>${escapeHtml(m.duration || '')}</em>
              ${m.instructions ? `<div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(m.instructions)}</div>` : ''}
            </div>
          `).join('')}
        </div>
        <div class="stream-meta">
          <span>Notes: ${escapeHtml(rx.notes || 'None')}</span>
          <span>📅 ${new Date(rx.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div style="color: var(--rose); text-align: center; padding: 1rem;">Failed to load prescriptions.</div>';
  }
}

// Upload record
async function handleUploadRecord(e) {
  e.preventDefault();
  const title = document.getElementById('input-record-title').value.trim();
  const recordType = document.getElementById('select-record-type').value;
  const fileInput = document.getElementById('input-record-file');

  if (!fileInput.files || fileInput.files.length === 0) {
    showToast('Please select a file to upload', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('title', title);
  formData.append('record_type', recordType);
  formData.append('file', fileInput.files[0]);

  try {
    await apiCall('/records/upload', {
      method: 'POST',
      body: formData
    });
    showToast('Medical record securely uploaded!', 'success');
    document.getElementById('form-upload-record').reset();
    await loadPatientRecords();
  } catch (err) {
    // handled
  }
}

async function loadPatientRecords() {
  const container = document.getElementById('patient-records-list');
  try {
    const records = await apiCall('/records');
    if (!records || records.length === 0) {
      container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 1rem;">No uploaded documents yet.</div>';
      return;
    }

    container.innerHTML = records.map(r => `
      <div class="stream-item" style="padding: 0.75rem;">
        <div class="stream-header">
          <span style="font-weight: 700; font-size: 0.88rem;">📄 ${escapeHtml(r.title)}</span>
          <span class="badge badge-medium">${r.record_type}</span>
        </div>
        <div class="stream-meta">
          <span>File: ${escapeHtml(r.file_name)}</span>
          <span>📅 ${new Date(r.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 1rem;">No uploaded documents.</div>';
  }
}

// ----------------- DOCTOR LOGIC -----------------

// Load Doctor Triage Queue
async function loadDoctorInbox() {
  const container = document.getElementById('doctor-inbox-list');
  try {
    const queries = await apiCall('/queries');
    if (!queries || queries.length === 0) {
      container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 2rem;">No pending triage tickets.</div>';
      return;
    }

    container.innerHTML = queries.map(q => `
      <div class="stream-item" onclick="selectQueryForDoctorReply(${q.id})" style="cursor: pointer;">
        <div class="stream-header">
          <span class="stream-title">${escapeHtml(q.title)}</span>
          <span class="badge badge-${q.urgency.toLowerCase()}">${q.urgency}</span>
        </div>
        <p class="stream-desc">${escapeHtml(q.description)}</p>
        <div class="stream-meta">
          <span>Dept: <strong>${escapeHtml(q.department || 'Cardiology')}</strong></span>
          <span>● Status: <strong>${q.status}</strong></span>
        </div>
      </div>
    `).join('');

    // Preselect first query
    if (queries.length > 0) {
      selectQueryForDoctorReply(queries[0].id, queries[0]);
    }
  } catch (e) {
    container.innerHTML = '<div style="color: var(--rose); text-align: center; padding: 1rem;">Failed to load inbox.</div>';
  }
}

async function selectQueryForDoctorReply(queryId, preloadedData) {
  let query = preloadedData;
  if (!query) {
    try {
      query = await apiCall(`/queries/${queryId}`);
    } catch (e) { return; }
  }

  document.getElementById('reply-query-id').value = query.id;
  document.getElementById('doctor-selected-query-info').innerHTML = `
    <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.35rem;">Ticket #${query.id}: ${escapeHtml(query.title)}</div>
    <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">${escapeHtml(query.description)}</div>
    <div class="badge badge-${query.urgency.toLowerCase()}">${query.urgency}</div>
    <div style="margin-top: 0.5rem; font-size: 0.8rem; background: rgba(0,0,0,0.3); padding: 0.6rem; border-radius: 6px;">
      <strong>AI Handoff Note:</strong><br>${escapeHtml(query.ai_summary || 'Standard triage assessment.')}
    </div>
  `;
  document.getElementById('form-doctor-response').style.display = 'block';
}

async function handleDoctorResponseSubmit(e) {
  e.preventDefault();
  const queryId = document.getElementById('reply-query-id').value;
  const responseText = document.getElementById('input-doctor-reply-text').value.trim();
  const recommendations = document.getElementById('input-doctor-recommendations').value.trim();

  try {
    await apiCall(`/queries/${queryId}/respond`, {
      method: 'POST',
      body: JSON.stringify({
        response_text: responseText,
        recommendations,
        is_clinical_advice: true
      })
    });
    showToast('Clinical response signed & dispatched to patient!', 'success');
    document.getElementById('form-doctor-response').reset();
    await loadDoctorInbox();
  } catch (e) {
    // handled
  }
}

async function loadDoctorSchedule() {
  const container = document.getElementById('doctor-schedule-list');
  try {
    const appts = await apiCall('/appointments');
    if (!appts || appts.length === 0) {
      container.innerHTML = '<div style="color: var(--text-dim); text-align: center; padding: 2rem;">No clinic appointments scheduled today.</div>';
      return;
    }

    container.innerHTML = appts.map(a => `
      <div class="stream-item">
        <div class="stream-header">
          <span class="stream-title">Patient #${a.patient_id} - ${escapeHtml(a.reason || 'Checkup')}</span>
          <span class="badge badge-${a.status === 'CONFIRMED' ? 'success' : 'medium'}">${a.status}</span>
        </div>
        <div class="stream-meta">
          <span>📅 ${a.appointment_date}</span>
          <span>⏰ ${a.start_time} - ${a.end_time}</span>
          <span>Status: <strong>${a.status}</strong></span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div style="color: var(--rose); text-align: center; padding: 1rem;">Failed to load schedule.</div>';
  }
}

async function handleCreatePrescription(e) {
  e.preventDefault();
  const patientId = parseInt(document.getElementById('prescribe-patient-id').value);
  const diagnosis = document.getElementById('prescribe-diagnosis').value.trim();
  const notes = document.getElementById('prescribe-notes').value.trim();

  const medication = {
    name: document.getElementById('med-name').value.trim(),
    dosage: document.getElementById('med-dosage').value.trim(),
    frequency: document.getElementById('med-freq').value.trim(),
    duration: document.getElementById('med-duration').value.trim()
  };

  try {
    await apiCall('/prescriptions', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        diagnosis,
        notes,
        medications: [medication]
      })
    });
    showToast('Prescription issued successfully!', 'success');
    document.getElementById('form-create-prescription').reset();
  } catch (e) {
    // handled
  }
}

// ----------------- ADMIN LOGIC -----------------

async function loadAdminStats() {
  try {
    const stats = await apiCall('/admin/stats');
    if (stats) {
      document.getElementById('stat-total-users').innerText = stats.total_users || '4';
      document.getElementById('stat-total-doctors').innerText = stats.total_doctors || '2';
      document.getElementById('stat-total-appts').innerText = stats.total_appointments || '1';
      document.getElementById('stat-total-queries').innerText = stats.total_queries || '1';
    }
  } catch (e) {
    console.error('Error loading stats:', e);
  }
}

async function loadAuditLogs() {
  const tbody = document.getElementById('tbody-audit-logs');
  try {
    const logs = await apiCall('/admin/audit-logs');
    if (!logs || logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem;">No audit records available.</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
        <td style="padding: 0.75rem 1rem; color: var(--text-dim); font-size: 0.8rem;">${new Date(l.timestamp).toLocaleString()}</td>
        <td style="padding: 0.75rem 1rem; font-weight: 700; color: var(--primary);">${escapeHtml(l.action)}</td>
        <td style="padding: 0.75rem 1rem;"><span class="badge badge-medium">${escapeHtml(l.resource)}</span></td>
        <td style="padding: 0.75rem 1rem; color: var(--text-muted);">${l.user_id ? `User #${l.user_id}` : 'System'}</td>
        <td style="padding: 0.75rem 1rem; color: var(--text-muted); font-size: 0.82rem;">${escapeHtml(l.details || '-')}</td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem; color: var(--rose);">Failed to load audit logs.</td></tr>';
  }
}

// Utility: Escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Initial Boot
document.addEventListener('DOMContentLoaded', () => {
  switchPersona('PATIENT');
});
