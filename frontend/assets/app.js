// ============================================================
//  GONZALO AGENTES IA — Marketing Dashboard v1.0
//  Frontend vanilla JS — no build step required
// ============================================================

const API = '';

// ── State ──
let state = {
  token: localStorage.getItem('ga_token') || '',
  user: JSON.parse(localStorage.getItem('ga_user') || 'null'),
  currentPage: 'dashboard',
  dashboard: null,
  contacts: [],
  conversations: [],
  selectedContact: null,
  products: [],
  campaigns: [],
  config: {},
  autoResponses: [],
  wspStatus: { connected: false },
};

// ── API Helpers ──
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); return null; }
  return res.json();
}

// ── Auth ──
async function login(username, password) {
  const data = await api('/api/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  if (data?.access_token) {
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem('ga_token', data.access_token);
    localStorage.setItem('ga_user', JSON.stringify(data.user));
    render();
    loadDashboard();
  }
  return data;
}

function logout() {
  state.token = '';
  state.user = null;
  localStorage.removeItem('ga_token');
  localStorage.removeItem('ga_user');
  render();
}

// ── Data Loaders ──
async function loadDashboard() {
  state.dashboard = await api('/api/dashboard');
  state.wspStatus = await api('/api/whatsapp-status') || { connected: false };
  render();
  renderChart();
}

async function loadContacts() {
  state.contacts = await api('/api/contacts') || [];
  render();
}

async function loadConversations(contactId) {
  state.conversations = await api(`/api/conversations/${contactId}`) || [];
  render();
  scrollChatBottom();
}

async function loadProducts() {
  state.products = await api('/api/products') || [];
  render();
}

async function loadCampaigns() {
  state.campaigns = await api('/api/campaigns') || [];
  render();
}

async function loadConfig() {
  state.config = await api('/api/config') || {};
  state.autoResponses = await api('/api/auto-responses') || [];
  render();
}

// ── Actions ──
async function sendMessage(phone, message) {
  await api('/api/send-message', {
    method: 'POST',
    body: JSON.stringify({ phone, message }),
  });
  if (state.selectedContact) loadConversations(state.selectedContact.id);
}

async function createProduct(product) {
  await api('/api/products', { method: 'POST', body: JSON.stringify(product) });
  loadProducts();
}

async function deleteProduct(id) {
  await api(`/api/products/${id}`, { method: 'DELETE' });
  loadProducts();
}

async function updateConfig(key, value) {
  await api('/api/config', { method: 'PUT', body: JSON.stringify({ key, value }) });
}

async function createAutoResponse(data) {
  await api('/api/auto-responses', { method: 'POST', body: JSON.stringify(data) });
  loadConfig();
}

async function deleteAutoResponse(id) {
  await api(`/api/auto-responses/${id}`, { method: 'DELETE' });
  loadConfig();
}

// ── Render ──
function render() {
  const app = document.getElementById('app');
  if (!state.token) {
    app.innerHTML = renderLogin();
    return;
  }
  app.innerHTML = `
    <div class="app-layout">
      ${renderSidebar()}
      <div class="main-content">
        ${renderTopBar()}
        <div class="content-area" id="content">
          ${renderPage()}
        </div>
      </div>
    </div>
    ${state._modal || ''}
  `;
}

function renderLogin() {
  return `
    <div class="login-screen">
      <div class="login-box">
        <div class="login-logo">
          <div class="icon">🤖</div>
          <h1>Gonzalo Agentes IA</h1>
          <p>Panel de Marketing y Ventas</p>
        </div>
        <div class="form-group">
          <label>Usuario</label>
          <input class="form-input" id="login-user" placeholder="admin" value="admin">
        </div>
        <div class="form-group">
          <label>Contraseña</label>
          <input class="form-input" id="login-pass" type="password" placeholder="••••••">
        </div>
        <button class="btn-primary" onclick="doLogin()">Iniciar Sesion</button>
        <div id="login-error" class="login-error"></div>
        <p style="text-align:center;margin-top:16px;font-size:11px;color:var(--t3)">
          Default: admin / GonzaloIA2026
        </p>
      </div>
    </div>
  `;
}

async function doLogin() {
  const u = document.getElementById('login-user').value;
  const p = document.getElementById('login-pass').value;
  const res = await login(u, p);
  if (!res?.access_token) {
    document.getElementById('login-error').textContent = 'Credenciales incorrectas';
  }
}

function renderSidebar() {
  const items = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'chat', icon: '💬', label: 'Conversaciones' },
    { id: 'contacts', icon: '👥', label: 'Contactos' },
    { id: 'products', icon: '📦', label: 'Productos' },
    { id: 'campaigns', icon: '📢', label: 'Campañas' },
    { id: 'whatsapp', icon: '📱', label: 'WhatsApp API' },
    { id: 'config', icon: '⚙️', label: 'Configuracion' },
  ];
  const navHtml = items.map(i => `
    <button class="nav-item ${state.currentPage === i.id ? 'active' : ''}"
            onclick="navigateTo('${i.id}')">
      <span class="nav-icon">${i.icon}</span>
      <span>${i.label}</span>
    </button>
  `).join('');

  const dotClass = state.wspStatus?.connected ? 'online' : 'offline';
  const dotLabel = state.wspStatus?.connected ? 'WhatsApp conectado' : 'WhatsApp desconectado';

  return `
    <div class="sidebar">
      <div class="sidebar-header">
        <h2>🤖 Agentes IA</h2>
        <p>Marketing v1.0</p>
      </div>
      <div class="sidebar-nav">${navHtml}</div>
      <div class="sidebar-footer">
        <div class="wsp-status">
          <span class="wsp-dot ${dotClass}"></span>
          <span class="wsp-label">${dotLabel}</span>
        </div>
      </div>
    </div>
  `;
}

function renderTopBar() {
  const titles = {
    dashboard: 'Dashboard',
    chat: 'Conversaciones en Vivo',
    contacts: 'Base de Contactos',
    products: 'Catalogo de Productos',
    campaigns: 'Campañas de Marketing',
    whatsapp: 'Conexion WhatsApp API',
    config: 'Configuracion del Agente',
  };
  return `
    <div class="top-bar">
      <h1>${titles[state.currentPage] || 'Dashboard'}</h1>
      <div class="top-bar-actions">
        <span style="font-size:12px;color:var(--t2)">👤 ${state.user?.username || 'admin'}</span>
        <button class="btn-sm" onclick="logout()">Salir</button>
      </div>
    </div>
  `;
}

function navigateTo(page) {
  state.currentPage = page;
  state._modal = '';
  render();
  if (page === 'dashboard') loadDashboard();
  if (page === 'chat' || page === 'contacts') loadContacts();
  if (page === 'products') loadProducts();
  if (page === 'campaigns') loadCampaigns();
  if (page === 'config') loadConfig();
  if (page === 'whatsapp') { api('/api/whatsapp-status').then(d => { state.wspStatus = d || {}; render(); }); }
}

function renderPage() {
  switch (state.currentPage) {
    case 'dashboard': return renderDashboard();
    case 'chat': return renderChat();
    case 'contacts': return renderContacts();
    case 'products': return renderProducts();
    case 'campaigns': return renderCampaigns();
    case 'whatsapp': return renderWhatsApp();
    case 'config': return renderConfig();
    default: return renderDashboard();
  }
}

// ── DASHBOARD ──
function renderDashboard() {
  const d = state.dashboard || {};
  return `
    <div class="stats-grid">
      <div class="stat-card green">
        <div class="stat-icon">💬</div>
        <div class="stat-value">${d.today_messages || 0}</div>
        <div class="stat-label">Mensajes hoy</div>
      </div>
      <div class="stat-card blue">
        <div class="stat-icon">👥</div>
        <div class="stat-value">${d.total_contacts || 0}</div>
        <div class="stat-label">Contactos totales</div>
      </div>
      <div class="stat-card purple">
        <div class="stat-icon">🎯</div>
        <div class="stat-value">${d.today_leads || 0}</div>
        <div class="stat-label">Leads nuevos hoy</div>
      </div>
      <div class="stat-card orange">
        <div class="stat-icon">📦</div>
        <div class="stat-value">${d.total_products || 0}</div>
        <div class="stat-label">Productos activos</div>
      </div>
    </div>

    <div class="chart-section">
      <div class="chart-card">
        <h3>📈 Mensajes ultimos 7 dias</h3>
        <div class="chart-container"><canvas id="mainChart"></canvas></div>
      </div>
      <div class="chart-card">
        <h3>👥 Segmentos de clientes</h3>
        <div class="chart-container"><canvas id="segmentChart"></canvas></div>
      </div>
    </div>

    <div class="table-card">
      <h3>💬 Ultimos mensajes</h3>
      <table>
        <thead><tr><th>Contacto</th><th>Mensaje</th><th>Tipo</th><th>Hora</th></tr></thead>
        <tbody>
          ${(d.recent_messages || []).map(m => `
            <tr>
              <td><strong>${m.name || m.phone}</strong></td>
              <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.message}</td>
              <td><span class="badge ${m.direction === 'in' ? 'blue' : 'green'}">${m.direction === 'in' ? 'Recibido' : 'Enviado'}</span></td>
              <td style="font-size:11px;color:var(--t2)">${formatTime(m.created_at)}</td>
            </tr>
          `).join('') || '<tr><td colspan="4" style="text-align:center;color:var(--t3)">Sin mensajes aun</td></tr>'}
        </tbody>
      </table>
    </div>
  `;
}

function renderChart() {
  const d = state.dashboard;
  if (!d) return;

  const ctx1 = document.getElementById('mainChart');
  if (ctx1) {
    new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: (d.chart_data || []).map(c => c.dia?.slice(5) || ''),
        datasets: [
          { label: 'Recibidos', data: (d.chart_data || []).map(c => c.entrantes || 0), backgroundColor: '#3b82f6', borderRadius: 6 },
          { label: 'Enviados', data: (d.chart_data || []).map(c => c.salientes || 0), backgroundColor: '#10b981', borderRadius: 6 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#94a3b8', font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: '#475569' }, grid: { color: 'rgba(42,58,80,.3)' } },
          y: { ticks: { color: '#475569' }, grid: { color: 'rgba(42,58,80,.3)' } },
        },
      },
    });
  }

  const ctx2 = document.getElementById('segmentChart');
  if (ctx2) {
    const segments = d.segments || {};
    new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: Object.keys(segments).length ? Object.keys(segments) : ['Sin datos'],
        datasets: [{
          data: Object.keys(segments).length ? Object.values(segments) : [1],
          backgroundColor: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899'],
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 }, padding: 12 } } },
      },
    });
  }
}

// ── CHAT ──
function renderChat() {
  const contactsList = state.contacts.map(c => `
    <div class="chat-contact ${state.selectedContact?.id === c.id ? 'active' : ''}"
         onclick="selectContact(${c.id})">
      <div class="chat-avatar">${(c.name || c.phone || '?')[0].toUpperCase()}</div>
      <div class="chat-contact-info">
        <div class="chat-contact-name">${c.name || c.phone}</div>
        <div class="chat-contact-last">${c.segment}</div>
      </div>
      <span class="chat-contact-time">${c.total_messages} msgs</span>
    </div>
  `).join('');

  const chatArea = state.selectedContact ? `
    <div class="chat-header">
      <div class="chat-avatar">${(state.selectedContact.name || '?')[0].toUpperCase()}</div>
      <div>
        <div class="chat-header-name">${state.selectedContact.name || 'Sin nombre'}</div>
        <div class="chat-header-phone">${state.selectedContact.phone} · ${state.selectedContact.segment}</div>
      </div>
    </div>
    <div class="chat-messages" id="chatMessages">
      ${state.conversations.map(m => `
        <div class="msg-bubble ${m.direction === 'in' ? 'msg-in' : 'msg-out'}">
          ${m.message}
          <div class="msg-time">${formatTime(m.created_at)}</div>
        </div>
      `).join('') || '<p style="text-align:center;color:var(--t3);margin-top:40px">Sin mensajes</p>'}
    </div>
    <div class="chat-input-area">
      <input id="chatInput" placeholder="Escribe un mensaje..." onkeydown="if(event.key==='Enter')sendChatMsg()">
      <button onclick="sendChatMsg()">Enviar</button>
    </div>
  ` : `
    <div class="chat-empty">
      <div class="icon">💬</div>
      <p>Selecciona un contacto para ver la conversacion</p>
    </div>
  `;

  return `
    <div class="chat-layout" style="height:calc(100vh - 120px)">
      <div class="chat-list">
        <div class="chat-search"><input placeholder="Buscar contacto..." oninput="filterContacts(this.value)"></div>
        <div class="chat-contacts" id="chatContacts">${contactsList || '<p style="padding:20px;color:var(--t3);text-align:center;font-size:13px">Sin contactos</p>'}</div>
      </div>
      <div class="chat-main">${chatArea}</div>
    </div>
  `;
}

function selectContact(id) {
  state.selectedContact = state.contacts.find(c => c.id === id);
  loadConversations(id);
}

function sendChatMsg() {
  const input = document.getElementById('chatInput');
  if (!input || !input.value.trim() || !state.selectedContact) return;
  sendMessage(state.selectedContact.phone, input.value.trim());
  input.value = '';
}

function scrollChatBottom() {
  setTimeout(() => {
    const el = document.getElementById('chatMessages');
    if (el) el.scrollTop = el.scrollHeight;
  }, 100);
}

function filterContacts(query) {
  const q = query.toLowerCase();
  document.querySelectorAll('.chat-contact').forEach(el => {
    const name = el.querySelector('.chat-contact-name')?.textContent.toLowerCase() || '';
    el.style.display = name.includes(q) ? '' : 'none';
  });
}

// ── CONTACTS ──
function renderContacts() {
  return `
    <div class="table-card">
      <h3>
        Base de contactos (${state.contacts.length})
        <button class="btn-sm green" onclick="showAddContactModal()">+ Nuevo contacto</button>
      </h3>
      <table>
        <thead><tr><th>Nombre</th><th>Telefono</th><th>Segmento</th><th>Mensajes</th><th>Ultimo mensaje</th></tr></thead>
        <tbody>
          ${state.contacts.map(c => `
            <tr>
              <td><strong>${c.name || 'Sin nombre'}</strong></td>
              <td>${c.phone}</td>
              <td><span class="badge ${segmentColor(c.segment)}">${c.segment}</span></td>
              <td>${c.total_messages}</td>
              <td style="font-size:11px;color:var(--t2)">${c.last_message_at ? formatTime(c.last_message_at) : '—'}</td>
            </tr>
          `).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--t3)">Sin contactos</td></tr>'}
        </tbody>
      </table>
    </div>
  `;
}

function showAddContactModal() {
  state._modal = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal" onclick="event.stopPropagation()">
        <h2>Nuevo Contacto <button class="modal-close" onclick="closeModal()">✕</button></h2>
        <div class="form-group"><label>Telefono (con codigo pais)</label><input class="form-input" id="mc-phone" placeholder="+51987654321"></div>
        <div class="form-group"><label>Nombre</label><input class="form-input" id="mc-name" placeholder="Juan Perez"></div>
        <div class="form-group"><label>Segmento</label>
          <select class="form-input" id="mc-segment">
            <option value="nuevo">Nuevo</option><option value="recurrente">Recurrente</option>
            <option value="vip">VIP</option><option value="inactivo">Inactivo</option>
          </select>
        </div>
        <button class="btn-primary" onclick="doCreateContact()">Guardar</button>
      </div>
    </div>
  `;
  render();
}

async function doCreateContact() {
  const phone = document.getElementById('mc-phone').value;
  const name = document.getElementById('mc-name').value;
  const segment = document.getElementById('mc-segment').value;
  if (!phone) return;
  await api('/api/contacts', { method: 'POST', body: JSON.stringify({ phone, name, segment }) });
  state._modal = '';
  loadContacts();
}

function closeModal(e) {
  if (e && e.target !== e.currentTarget) return;
  state._modal = '';
  render();
}

// ── PRODUCTS ──
function renderProducts() {
  return `
    <div style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:13px;color:var(--t2)">${state.products.length} productos</span>
      <button class="btn-sm green" onclick="showAddProductModal()">+ Nuevo producto</button>
    </div>
    <div class="products-grid">
      ${state.products.map(p => `
        <div class="product-card">
          <h4>${p.name}</h4>
          <div class="price">S/${Number(p.price).toFixed(2)}</div>
          <div class="category">${p.category || 'Sin categoria'}</div>
          <p style="font-size:12px;color:var(--t2);margin-top:6px">${p.description || ''}</p>
          <div class="stock">Stock: <strong style="color:${p.stock < 5 ? 'var(--red)' : 'var(--acc)'}">${p.stock}</strong></div>
          <div class="product-actions">
            <button class="btn-sm" onclick="deleteProduct(${p.id})" style="color:var(--red);border-color:var(--red)">Eliminar</button>
          </div>
        </div>
      `).join('') || '<p style="color:var(--t3)">No hay productos. Agrega tu primer producto.</p>'}
    </div>
  `;
}

function showAddProductModal() {
  state._modal = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal" onclick="event.stopPropagation()">
        <h2>Nuevo Producto <button class="modal-close" onclick="closeModal()">✕</button></h2>
        <div class="form-group"><label>Nombre</label><input class="form-input" id="mp-name" placeholder="Polo manga corta"></div>
        <div class="form-group"><label>Precio (S/)</label><input class="form-input" id="mp-price" type="number" placeholder="49.90"></div>
        <div class="form-group"><label>Categoria</label><input class="form-input" id="mp-cat" placeholder="Ropa"></div>
        <div class="form-group"><label>Descripcion</label><input class="form-input" id="mp-desc" placeholder="100% algodon, tallas S-XL"></div>
        <div class="form-group"><label>Stock</label><input class="form-input" id="mp-stock" type="number" placeholder="100"></div>
        <button class="btn-primary" onclick="doCreateProduct()">Guardar</button>
      </div>
    </div>
  `;
  render();
}

async function doCreateProduct() {
  const data = {
    name: document.getElementById('mp-name').value,
    price: parseFloat(document.getElementById('mp-price').value) || 0,
    category: document.getElementById('mp-cat').value,
    description: document.getElementById('mp-desc').value,
    stock: parseInt(document.getElementById('mp-stock').value) || 0,
  };
  if (!data.name) return;
  await createProduct(data);
  state._modal = '';
}

// ── CAMPAIGNS ──
function renderCampaigns() {
  return `
    <div style="margin-bottom:16px;display:flex;justify-content:space-between">
      <span style="font-size:13px;color:var(--t2)">${state.campaigns.length} campañas</span>
      <button class="btn-sm green" onclick="showAddCampaignModal()">+ Nueva campaña</button>
    </div>
    <div class="table-card">
      <table>
        <thead><tr><th>Nombre</th><th>Segmento</th><th>Estado</th><th>Enviados</th><th>Acciones</th></tr></thead>
        <tbody>
          ${state.campaigns.map(c => `
            <tr>
              <td><strong>${c.name}</strong></td>
              <td>${c.segment_filter}</td>
              <td><span class="badge ${c.status === 'sent' ? 'green' : c.status === 'scheduled' ? 'blue' : 'orange'}">${c.status}</span></td>
              <td>${c.sent_count}</td>
              <td>${c.status === 'draft' ? `<button class="btn-sm green" onclick="sendCampaign(${c.id})">Enviar</button>` : '—'}</td>
            </tr>
          `).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--t3)">Sin campañas</td></tr>'}
        </tbody>
      </table>
    </div>
  `;
}

function showAddCampaignModal() {
  state._modal = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal" onclick="event.stopPropagation()">
        <h2>Nueva Campaña <button class="modal-close" onclick="closeModal()">✕</button></h2>
        <div class="form-group"><label>Nombre</label><input class="form-input" id="mc2-name" placeholder="Promo Junio"></div>
        <div class="form-group"><label>Mensaje</label><textarea class="form-input" id="mc2-msg" rows="4" placeholder="Hola! Tenemos ofertas especiales..."></textarea></div>
        <div class="form-group"><label>Segmento</label>
          <select class="form-input" id="mc2-seg">
            <option value="todos">Todos</option><option value="nuevo">Nuevos</option>
            <option value="recurrente">Recurrentes</option><option value="vip">VIP</option>
          </select>
        </div>
        <button class="btn-primary" onclick="doCreateCampaign()">Crear campaña</button>
      </div>
    </div>
  `;
  render();
}

async function doCreateCampaign() {
  const data = {
    name: document.getElementById('mc2-name').value,
    message_template: document.getElementById('mc2-msg').value,
    segment_filter: document.getElementById('mc2-seg').value,
  };
  if (!data.name || !data.message_template) return;
  await api('/api/campaigns', { method: 'POST', body: JSON.stringify(data) });
  state._modal = '';
  loadCampaigns();
}

async function sendCampaign(id) {
  if (!confirm('Enviar esta campaña a todos los contactos del segmento?')) return;
  await api(`/api/campaigns/${id}/send`, { method: 'POST' });
  loadCampaigns();
}

// ── WHATSAPP ──
function renderWhatsApp() {
  const s = state.wspStatus || {};
  return `
    <div class="wsp-connect-card">
      <h2>📱 Conexion WhatsApp Business API</h2>
      <p>Conecta tu numero de WhatsApp Business para que el agente pueda recibir y enviar mensajes automaticamente 24/7.</p>

      <div class="connect-status ${s.connected ? 'ok' : 'pending'}">
        <span class="wsp-dot ${s.connected ? 'online' : 'offline'}"></span>
        ${s.connected
          ? `Conectado — Phone ID: ...${s.phone_id}`
          : 'No conectado — Configura tus credenciales'}
      </div>

      <h3 style="font-size:15px;font-weight:600;margin:24px 0 12px">Como conectar tu WhatsApp</h3>
      <ol class="connect-steps">
        <li><strong>Crear cuenta de Meta Business</strong><br>Ve a business.facebook.com y crea tu cuenta de negocio. Es gratuito.</li>
        <li><strong>Activar WhatsApp Business API</strong><br>En Meta Business Suite > WhatsApp > Comenzar. Sigue el asistente para verificar tu numero.</li>
        <li><strong>Obtener credenciales</strong><br>En la seccion de WhatsApp Business Platform, copia tu <strong>Phone Number ID</strong> y genera un <strong>Access Token permanente</strong>.</li>
        <li><strong>Configurar Webhook</strong><br>En la configuracion de tu app en Meta, agrega la URL del webhook:<br>
          <code style="background:var(--card2);padding:4px 10px;border-radius:6px;font-size:12px;display:inline-block;margin-top:6px">
            https://tu-servidor.com/webhook
          </code><br>
          Token de verificacion: <code style="background:var(--card2);padding:4px 10px;border-radius:6px;font-size:12px">gonzalo_agentes_2026</code>
        </li>
        <li><strong>Agregar variables de entorno</strong><br>En tu servidor, configura:<br>
          <code style="background:var(--card2);padding:4px 10px;border-radius:6px;font-size:12px;display:block;margin-top:6px;line-height:2">
            WHATSAPP_TOKEN=tu_token<br>
            WHATSAPP_PHONE_ID=tu_phone_id
          </code>
        </li>
        <li><strong>Reiniciar el servidor</strong><br>Una vez configuradas las variables, reinicia el backend y el status cambiara a "Conectado".</li>
      </ol>

      <div style="margin-top:20px">
        <button class="btn-sm green" onclick="checkWspStatus()" style="padding:10px 24px;font-size:13px">
          🔄 Verificar conexion
        </button>
      </div>
    </div>
  `;
}

async function checkWspStatus() {
  state.wspStatus = await api('/api/whatsapp-status') || { connected: false };
  render();
}

// ── CONFIG ──
function renderConfig() {
  const cfg = state.config || {};
  return `
    <div class="config-grid">
      <div class="config-card">
        <h3>🤖 Agente IA</h3>
        <div class="config-row">
          <label>Agente activo</label>
          <button class="toggle ${cfg.agent_active === 'true' ? 'on' : 'off'}"
                  onclick="toggleConfig('agent_active')">
            <span class="toggle-knob"></span>
          </button>
        </div>
        <div class="config-row">
          <label>IA (Claude) activa</label>
          <button class="toggle ${cfg.ai_enabled === 'true' ? 'on' : 'off'}"
                  onclick="toggleConfig('ai_enabled')">
            <span class="toggle-knob"></span>
          </button>
        </div>
        <div class="config-row">
          <label>Tono del agente</label>
          <select class="form-input" style="width:auto" onchange="updateConfig('tone',this.value)">
            <option ${cfg.tone === 'amigable' ? 'selected' : ''}>amigable</option>
            <option ${cfg.tone === 'formal' ? 'selected' : ''}>formal</option>
            <option ${cfg.tone === 'informal' ? 'selected' : ''}>informal</option>
          </select>
        </div>
      </div>
      <div class="config-card">
        <h3>🏪 Negocio</h3>
        <div class="form-group" style="margin-bottom:10px">
          <label style="font-size:11px;color:var(--t2)">Nombre del negocio</label>
          <input class="form-input" value="${cfg.business_name || ''}" onchange="updateConfig('business_name',this.value)">
        </div>
        <div class="form-group" style="margin-bottom:10px">
          <label style="font-size:11px;color:var(--t2)">Horario</label>
          <input class="form-input" value="${cfg.business_hours || ''}" onchange="updateConfig('business_hours',this.value)">
        </div>
        <div class="form-group">
          <label style="font-size:11px;color:var(--t2)">Direccion</label>
          <input class="form-input" value="${cfg.business_address || ''}" onchange="updateConfig('business_address',this.value)">
        </div>
      </div>
    </div>

    <div class="table-card" style="margin-top:16px">
      <h3>
        ⚡ Respuestas automaticas
        <button class="btn-sm green" onclick="showAddResponseModal()">+ Nueva</button>
      </h3>
      <table>
        <thead><tr><th>Palabra clave</th><th>Respuesta</th><th>Prioridad</th><th>Acciones</th></tr></thead>
        <tbody>
          ${state.autoResponses.map(r => `
            <tr>
              <td><strong>${r.trigger_keyword}</strong></td>
              <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.response_text}</td>
              <td>${r.priority}</td>
              <td><button class="btn-sm" style="color:var(--red)" onclick="deleteAutoResponse(${r.id})">✕</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

async function toggleConfig(key) {
  const current = state.config[key];
  const newVal = current === 'true' ? 'false' : 'true';
  await updateConfig(key, newVal);
  state.config[key] = newVal;
  render();
}

function showAddResponseModal() {
  state._modal = `
    <div class="modal-overlay" onclick="closeModal(event)">
      <div class="modal" onclick="event.stopPropagation()">
        <h2>Nueva Respuesta Automatica <button class="modal-close" onclick="closeModal()">✕</button></h2>
        <div class="form-group"><label>Palabra clave (trigger)</label><input class="form-input" id="mar-key" placeholder="promocion"></div>
        <div class="form-group"><label>Respuesta</label><textarea class="form-input" id="mar-resp" rows="3" placeholder="Tenemos promociones especiales..."></textarea></div>
        <div class="form-group"><label>Prioridad (1-10)</label><input class="form-input" id="mar-pri" type="number" value="5"></div>
        <button class="btn-primary" onclick="doCreateResponse()">Guardar</button>
      </div>
    </div>
  `;
  render();
}

async function doCreateResponse() {
  const data = {
    trigger_keyword: document.getElementById('mar-key').value,
    response_text: document.getElementById('mar-resp').value,
    priority: parseInt(document.getElementById('mar-pri').value) || 5,
  };
  if (!data.trigger_keyword || !data.response_text) return;
  await createAutoResponse(data);
  state._modal = '';
}

// ── Helpers ──
function formatTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString('es-PE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  } catch { return ts; }
}

function segmentColor(s) {
  const map = { nuevo: 'blue', recurrente: 'green', vip: 'purple', inactivo: 'orange' };
  return map[s] || 'blue';
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  render();
  if (state.token) loadDashboard();
});

// Keyboard: Enter on login
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('login-pass')) doLogin();
});
