/* ═══════════════════════════════════════════════════════════════
   OmniClass — Main JavaScript
   ═══════════════════════════════════════════════════════════════ */

'use strict';

// ── Sidebar Toggle ──────────────────────────────────────────────
const sidebar  = document.getElementById('sidebar');
const toggleBtn = document.getElementById('sidebarToggle');
let overlay;

function createOverlay() {
  if (overlay) return;
  overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', closeSidebar);
}

function openSidebar() {
  createOverlay();
  sidebar?.classList.add('open');
  overlay?.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  sidebar?.classList.remove('open');
  overlay?.classList.remove('show');
  document.body.style.overflow = '';
}

function toggleSidebar() {
  if (window.innerWidth < 992) {
    sidebar?.classList.contains('open') ? closeSidebar() : openSidebar();
  } else {
    const wrapper = document.querySelector('.main-wrapper');
    const isCollapsed = sidebar?.classList.toggle('collapsed');
    if (wrapper) wrapper.style.marginLeft = isCollapsed ? '72px' : 'var(--sidebar-w)';
  }
}

toggleBtn?.addEventListener('click', toggleSidebar);

// Auto-close on resize
window.addEventListener('resize', () => {
  if (window.innerWidth >= 992) closeSidebar();
});

// ── Notification Dropdown ───────────────────────────────────────
const notifDropdown = document.querySelector('[data-bs-toggle="dropdown"]');
if (notifDropdown) {
  notifDropdown.addEventListener('show.bs.dropdown', loadNotifications);
}

async function loadNotifications() {
  const list = document.getElementById('notif-list');
  if (!list) return;

  try {
    const res = await fetch('/api/v1/notifications');
    const data = await res.json();

    if (!data.length) {
      list.innerHTML = `
        <div class="text-center py-4 text-muted small">
          <i class="bi bi-bell-slash fs-2 d-block mb-2"></i>
          Tidak ada notifikasi baru
        </div>`;
      return;
    }

    list.innerHTML = data.map(n => `
      <a class="list-group-item list-group-item-action px-3 py-2"
         href="${n.link || '#'}" onclick="markRead(${n.id})">
        <div class="d-flex gap-2">
          <div class="mt-1 text-${n.type}">
            <i class="bi bi-bell-fill"></i>
          </div>
          <div class="flex-grow-1 min-w-0">
            <div class="d-flex justify-content-between">
              <strong class="small text-truncate">${n.title}</strong>
              <small class="text-muted ms-2 flex-shrink-0">${n.time_ago}</small>
            </div>
            <p class="mb-0 text-muted small text-truncate">${n.message}</p>
          </div>
        </div>
      </a>`).join('');
  } catch (e) {
    console.error('Failed to load notifications:', e);
  }
}

async function markRead(id) {
  try {
    await fetch(`/api/v1/notifications/${id}/read`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() }
    });
  } catch (e) { /* silent */ }
}

// ── Auto-dismiss Alerts ─────────────────────────────────────────
document.querySelectorAll('.alert:not(.alert-permanent)').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .4s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 400);
  }, 5000);
});

// ── CSRF Helper ─────────────────────────────────────────────────
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content
    || document.querySelector('input[name="csrf_token"]')?.value
    || '';
}

// ── Tooltips & Popovers Bootstrap ──────────────────────────────
document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
  new bootstrap.Tooltip(el, { trigger: 'hover' });
});

// ── Form Confirmation ────────────────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', function(e) {
    if (!confirm(this.dataset.confirm)) e.preventDefault();
  });
});

// ── Number Input Formatting ──────────────────────────────────────
document.querySelectorAll('input[type="number"].grade-input').forEach(inp => {
  inp.addEventListener('blur', function() {
    const v = parseFloat(this.value);
    if (!isNaN(v)) {
      this.value = Math.min(parseFloat(this.max || 100), Math.max(0, v));
    }
  });
});

// ── Active Nav Highlight ─────────────────────────────────────────
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(item => {
  const href = item.getAttribute('href');
  if (href && href !== '#' && currentPath.startsWith(href) && href !== '/') {
    item.classList.add('active');
  }
});

// ── Table Row Click ──────────────────────────────────────────────
document.querySelectorAll('tr[data-href]').forEach(row => {
  row.style.cursor = 'pointer';
  row.addEventListener('click', () => window.location.href = row.dataset.href);
});

// ── Toast Notification Helper ─────────────────────────────────────
window.showToast = function(message, type = 'success', duration = 3500) {
  const icons = { success: 'check-circle-fill', danger: 'exclamation-triangle-fill', warning: 'exclamation-circle-fill', info: 'info-circle-fill' };
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} shadow-lg position-fixed d-flex align-items-center gap-2`;
  toast.style.cssText = 'bottom:24px;right:24px;z-index:9999;min-width:280px;max-width:380px;animation:slideInRight .3s ease';
  toast.innerHTML = `<i class="bi bi-${icons[type] || 'info-circle-fill'}"></i><span>${message}</span>`;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity .3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
};

// ── Slide animation keyframe ────────────────────────────────────
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from { transform: translateX(100%); opacity: 0; }
    to   { transform: translateX(0);   opacity: 1; }
  }
`;
document.head.appendChild(style);

// ── Date/Time auto-set ───────────────────────────────────────────
const dateInputs = document.querySelectorAll('input[type="date"]:not([value])');
dateInputs.forEach(inp => {
  const today = new Date().toISOString().split('T')[0];
  inp.setAttribute('min', today);
});

// ── Sidebar Nav Label Collapse (desktop) ────────────────────────
function applySidebarCollapse() {
  if (!sidebar) return;
  const isCollapsed = sidebar.classList.contains('collapsed');
  sidebar.querySelectorAll('.nav-item span, .brand-text').forEach(el => {
    el.style.display = isCollapsed ? 'none' : '';
  });
  sidebar.querySelectorAll('.nav-item').forEach(el => {
    el.title = isCollapsed ? el.querySelector('span')?.textContent?.trim() || '' : '';
  });
  if (isCollapsed) sidebar.style.width = '72px';
  else sidebar.style.width = 'var(--sidebar-w)';
}

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Close mobile sidebar on nav click
  document.querySelectorAll('.nav-item[href]').forEach(item => {
    item.addEventListener('click', () => {
      if (window.innerWidth < 992) closeSidebar();
    });
  });

  // Responsive table overflow hint
  document.querySelectorAll('.table-responsive').forEach(t => {
    if (t.scrollWidth > t.clientWidth) {
      const hint = document.createElement('div');
      hint.className = 'text-muted text-end small py-1 pe-2';
      hint.innerHTML = '<i class="bi bi-arrow-left-right me-1"></i>Geser untuk melihat lebih';
      t.parentNode.insertBefore(hint, t.nextSibling);
    }
  });
});
