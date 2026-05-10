from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import sqlite3, json, os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gonzalo_valles_agentes_2026')

# ══════════════════════════════════════════════════════════════
#  CREDENCIALES ADMIN — solo Gonzalo
# ══════════════════════════════════════════════════════════════
ADMIN_USER  = os.environ.get('ADMIN_USER', 'gonzalo')
ADMIN_PASS  = os.environ.get('ADMIN_PASS', 'GV2026admin')
GONZALO_WSP = os.environ.get('GONZALO_PHONE', '+51908763241')
DB_PATH     = 'gonzalo_agents.db'

# ══════════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript('''
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, type TEXT NOT NULL,
        description TEXT, color TEXT DEFAULT '#6366f1',
        icon TEXT DEFAULT 'robot', active INTEGER DEFAULT 1,
        install_price TEXT, monthly_price TEXT,
        features TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, business TEXT, phone TEXT, email TEXT, address TEXT,
        agent_id INTEGER, agent_name TEXT, status TEXT DEFAULT 'active',
        monthly_fee REAL DEFAULT 0, install_date TEXT, notes TEXT,
        FOREIGN KEY(agent_id) REFERENCES agents(id)
    );
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_number TEXT UNIQUE,
        client_name TEXT, business TEXT, agent_id INTEGER, agent_name TEXT,
        subject TEXT, message TEXT, category TEXT DEFAULT 'consulta',
        priority TEXT DEFAULT 'normal', status TEXT DEFAULT 'open',
        sla_hours INTEGER DEFAULT 24, created_at TEXT,
        updated_at TEXT, resolved_at TEXT, resolution TEXT,
        assigned_to TEXT DEFAULT 'Gonzalo Valles'
    );
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, content TEXT, category TEXT,
        agent_id INTEGER, views INTEGER DEFAULT 0, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE, client_id INTEGER, client_name TEXT,
        amount REAL, status TEXT DEFAULT 'pending',
        period TEXT, due_date TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS contact_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, business TEXT, phone TEXT, email TEXT,
        agent_interest TEXT, message TEXT, status TEXT DEFAULT 'new',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS agent_monitor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id INTEGER, status TEXT DEFAULT 'online',
        last_check TEXT, uptime_percent REAL DEFAULT 99.9,
        tickets_today INTEGER DEFAULT 0, response_avg_hours REAL DEFAULT 2.0
    );
    ''')

    # Insertar agentes si no existen
    if db.execute('SELECT COUNT(*) FROM agents').fetchone()[0] == 0:
        agents = [
            (1,'Marketing completo','marketing','Chatbot WhatsApp, redes sociales, campañas y métricas automáticas','#8b5cf6','bullhorn',1,'S/250–500','S/120–200','["Chatbot 24/7","AutoPost IA","Email marketing","Métricas","Campañas","Base de clientes"]'),
            (2,'Inventario inteligente','inventory','Control de stock, alertas de mínimos y reportes automáticos','#06b6d4','boxes-stacked',1,'S/200–400','S/100–150','["Control de stock","Alertas de mínimos","Entradas y salidas","Reportes PDF","Gestión de proveedores","Códigos QR"]'),
            (3,'Ciberseguridad 24/7','security','Escaneo automático de vulnerabilidades, alertas y reportes PDF profesionales','#ef4444','shield-halved',1,'S/400–800','S/200–350','["Escaneo 24/7","Lista de dominios/IPs","Reporte PDF con soluciones","Alertas WhatsApp","Mapeo de red","Monitor continuo"]'),
            (4,'Atención al cliente CRM','crm','Tickets, soporte 24/7, historial completo e indicadores de satisfacción','#f59e0b','headset',1,'S/200–350','S/100–150','["Sistema de tickets","Soporte 24/7","Historial de clientes","Encuestas satisfacción","Métricas CRM","Escalamiento"]'),
            (5,'Reservas y agenda','reservations','Citas automáticas para spas, salones, restaurantes y clínicas','#10b981','calendar-check',1,'S/150–300','S/80–130','["Reservas por WhatsApp","Recordatorios automáticos","Gestión de turnos","Perfil del cliente","Dashboard de ocupación","Cancelaciones"]'),
            (6,'Finanzas y caja','finance','Control de ingresos, egresos, reportes diarios y proyecciones financieras','#3b82f6','chart-pie',1,'S/150–300','S/80–130','["Control de caja","Ingresos y egresos","Reporte diario","Proyección de ventas","Alertas de saldo","Métodos de pago"]'),
        ]
        for a in agents:
            db.execute('INSERT INTO agents (id,name,type,description,color,icon,active,install_price,monthly_price,features,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                      (*a, datetime.now().isoformat()))

        # Clientes demo
        demo_clients = [
            ('Rosa Mamani','Tienda Moda Gamarra','+51987111222','rosita@gmail.com','Gamarra, La Victoria',1,'Marketing completo','active',150,'2026-01-15','Clienta satisfecha'),
            ('Carlos Quispe','Bodega Don Carlos','+51987333444','carlos@gmail.com','Surco',2,'Inventario inteligente','active',120,'2026-02-01','Maneja 200+ productos'),
            ('TechPeru SAC','Empresa de tecnología','+51987555666','tech@techperu.pe','San Isidro',3,'Ciberseguridad 24/7','active',300,'2026-03-01','Red de 50 equipos'),
            ('Salon Luna','Salón de belleza','+51987777888','luna@salon.pe','Miraflores',5,'Reservas y agenda','active',100,'2026-02-15','Quiere agregar manicure'),
        ]
        for cl in demo_clients:
            db.execute('INSERT INTO clients (name,business,phone,email,address,agent_id,agent_name,status,monthly_fee,install_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)', cl)

        # Tickets demo
        now = datetime.now().isoformat()
        demo_tickets = [
            ('TKT-001','Rosa Mamani','Tienda Moda Gamarra',1,'Marketing completo','Agregar producto nuevo al chatbot','Necesito agregar polos talla XS y XXS al catálogo','configuracion','normal','open',24,now,now,None,None),
            ('TKT-002','TechPeru SAC','Empresa de tecnología',3,'Ciberseguridad 24/7','Vulnerabilidad crítica detectada','Puerto 23 (Telnet) abierto en 192.168.1.1 — riesgo crítico','incidencia','high','open',4,now,now,None,None),
            ('TKT-003','Carlos Quispe','Bodega Don Carlos',2,'Inventario inteligente','Agregar categoría Bebidas','Necesito agregar nueva categoría de bebidas al inventario','mejora','normal','resolved',24,now,now,now,'Categoría creada y configurada exitosamente'),
        ]
        for t in demo_tickets:
            db.execute('INSERT INTO tickets (ticket_number,client_name,business,agent_id,agent_name,subject,message,category,priority,status,sla_hours,created_at,updated_at,resolved_at,resolution) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', t)

        # Knowledge base
        kb_items = [
            ('Cómo agregar un producto al inventario','Accede al agente de inventario → pestaña Herramientas → Agregar producto → llena nombre, SKU, categoría y stock mínimo → Guardar.','inventario',2),
            ('El chatbot no responde bien','Verifica que el mensaje de bienvenida esté configurado. Accede al agente → Config → Chatbot → actualiza el mensaje. Si persiste, crea un ticket.','marketing',1),
            ('Cómo generar reporte de seguridad','Agente Ciberseguridad → Herramientas → ingresa IP o dominio → Iniciar escaneo → espera el resultado → Descargar PDF.','seguridad',3),
        ]
        for kb in kb_items:
            db.execute('INSERT INTO knowledge_base (title,content,category,agent_id,created_at) VALUES (?,?,?,?,?)', (*kb, now))

        # Monitor inicial
        for i in range(1,7):
            db.execute('INSERT INTO agent_monitor (agent_id,status,last_check,uptime_percent) VALUES (?,?,?,?)',
                      (i,'online',now,99.9))

    db.commit(); db.close()

# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def send_whatsapp_notification(subject, body):
    """Reemplazar con Twilio para producción real"""
    msg = f"\n📱 [WSP → Gonzalo]\n{subject}\n{body}\n{'─'*40}"
    print(msg)

def get_ticket_number():
    db = get_db()
    count = db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    db.close()
    return f'TKT-{str(count+1).zfill(4)}'

def check_sla(ticket):
    if ticket['status'] == 'resolved':
        return 'resolved'
    created = datetime.fromisoformat(ticket['created_at'])
    sla_deadline = created + timedelta(hours=ticket['sla_hours'])
    if datetime.now() > sla_deadline:
        return 'breached'
    elif datetime.now() > sla_deadline - timedelta(hours=2):
        return 'warning'
    return 'ok'

# ══════════════════════════════════════════════════════════════
#  SITIO PÚBLICO
# ══════════════════════════════════════════════════════════════
@app.route('/')
def home():
    db = get_db()
    agents = db.execute('SELECT * FROM agents WHERE active=1 ORDER BY id').fetchall()
    db.close()
    return render_template('public/home.html', agents=agents)

@app.route('/contacto', methods=['POST'])
def contact():
    db = get_db()
    db.execute('INSERT INTO contact_leads (name,business,phone,email,agent_interest,message,created_at) VALUES (?,?,?,?,?,?,?)', (
        request.form.get('name'), request.form.get('business'),
        request.form.get('phone'), request.form.get('email'),
        request.form.get('agent_interest'), request.form.get('message'),
        datetime.now().isoformat()
    ))
    db.commit(); db.close()
    send_whatsapp_notification(
        f"🌟 Nuevo lead: {request.form.get('name')} — {request.form.get('business')}",
        f"Tel: {request.form.get('phone')}\nInterés: {request.form.get('agent_interest')}\n{request.form.get('message','')}"
    )
    return jsonify({'ok': True, 'message': '¡Mensaje enviado! Gonzalo te contactará pronto.'})

# ══════════════════════════════════════════════════════════════
#  AUTH ADMIN
# ══════════════════════════════════════════════════════════════
@app.route('/admin/login', methods=['GET','POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        if request.form.get('username')==ADMIN_USER and request.form.get('password')==ADMIN_PASS:
            session['logged_in'] = True
            session['user'] = ADMIN_USER
            return redirect(url_for('admin_dashboard'))
        flash('Credenciales incorrectas','error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ══════════════════════════════════════════════════════════════
#  ADMIN — DASHBOARD
# ══════════════════════════════════════════════════════════════
@app.route('/admin')
@login_required
def admin_dashboard():
    db = get_db()
    agents   = db.execute('SELECT * FROM agents ORDER BY id').fetchall()
    clients  = db.execute('SELECT * FROM clients WHERE status="active"').fetchall()
    tickets  = db.execute('SELECT * FROM tickets ORDER BY CASE priority WHEN "high" THEN 1 ELSE 2 END, created_at DESC LIMIT 20').fetchall()
    open_t   = db.execute("SELECT COUNT(*) as n FROM tickets WHERE status='open'").fetchone()['n']
    high_t   = db.execute("SELECT COUNT(*) as n FROM tickets WHERE status='open' AND priority='high'").fetchone()['n']
    revenue  = db.execute("SELECT COALESCE(SUM(monthly_fee),0) as t FROM clients WHERE status='active'").fetchone()['t']
    leads    = db.execute("SELECT COUNT(*) as n FROM contact_leads WHERE status='new'").fetchone()['n']
    monitors = db.execute('SELECT * FROM agent_monitor').fetchall()
    agents_stats = []
    for ag in agents:
        cnt = db.execute('SELECT COUNT(*) as n FROM clients WHERE agent_id=? AND status="active"',(ag['id'],)).fetchone()['n']
        rev = db.execute('SELECT COALESCE(SUM(monthly_fee),0) as t FROM clients WHERE agent_id=? AND status="active"',(ag['id'],)).fetchone()['t']
        tix = db.execute("SELECT COUNT(*) as n FROM tickets WHERE agent_id=? AND status='open'",(ag['id'],)).fetchone()['n']
        agents_stats.append({'agent':ag,'clients':cnt,'revenue':rev,'tickets':tix})
    tickets_with_sla = [{'ticket':t,'sla':check_sla(t)} for t in tickets]
    db.close()
    return render_template('admin/dashboard.html',
        agents=agents, clients=clients, tickets=tickets_with_sla,
        open_tickets=open_t, high_tickets=high_t, revenue=revenue,
        new_leads=leads, agents_stats=agents_stats, monitors=monitors)

# ══════════════════════════════════════════════════════════════
#  ADMIN — TICKETS (GLPI)
# ══════════════════════════════════════════════════════════════
@app.route('/admin/tickets')
@login_required
def admin_tickets():
    db = get_db()
    status_f   = request.args.get('status','all')
    priority_f = request.args.get('priority','all')
    agent_f    = request.args.get('agent','all')
    query = 'SELECT * FROM tickets WHERE 1=1'
    params = []
    if status_f != 'all':
        query += ' AND status=?'; params.append(status_f)
    if priority_f != 'all':
        query += ' AND priority=?'; params.append(priority_f)
    if agent_f != 'all':
        query += ' AND agent_id=?'; params.append(int(agent_f))
    query += ' ORDER BY CASE priority WHEN "high" THEN 1 ELSE 2 END, created_at DESC'
    tickets  = db.execute(query, params).fetchall()
    agents   = db.execute('SELECT id,name FROM agents').fetchall()
    kb_items = db.execute('SELECT * FROM knowledge_base ORDER BY views DESC LIMIT 5').fetchall()
    stats = {
        'total': db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0],
        'open':  db.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0],
        'high':  db.execute("SELECT COUNT(*) FROM tickets WHERE priority='high' AND status='open'").fetchone()[0],
        'resolved_today': db.execute("SELECT COUNT(*) FROM tickets WHERE status='resolved' AND date(resolved_at)=date('now')").fetchone()[0],
    }
    db.close()
    tickets_with_sla = [{'ticket':t,'sla':check_sla(t)} for t in tickets]
    return render_template('admin/tickets.html', tickets=tickets_with_sla,
        agents=agents, kb_items=kb_items, stats=stats,
        status_f=status_f, priority_f=priority_f, agent_f=agent_f)

@app.route('/admin/tickets/<int:tid>/resolve', methods=['POST'])
@login_required
def resolve_ticket(tid):
    db = get_db()
    res = request.form.get('resolution','')
    db.execute("UPDATE tickets SET status='resolved',resolved_at=?,resolution=?,updated_at=? WHERE id=?",
               (datetime.now().isoformat(), res, datetime.now().isoformat(), tid))
    db.commit(); db.close()
    flash('Ticket resuelto exitosamente','success')
    return redirect(url_for('admin_tickets'))

@app.route('/admin/tickets/<int:tid>/update_priority', methods=['POST'])
@login_required
def update_priority(tid):
    db = get_db()
    db.execute('UPDATE tickets SET priority=?,updated_at=? WHERE id=?',
               (request.form['priority'], datetime.now().isoformat(), tid))
    db.commit(); db.close()
    return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════
#  ADMIN — CLIENTES
# ══════════════════════════════════════════════════════════════
@app.route('/admin/clients')
@login_required
def admin_clients():
    db = get_db()
    clients = db.execute('''SELECT c.*,a.color as agent_color FROM clients c
                           LEFT JOIN agents a ON c.agent_id=a.id
                           ORDER BY c.name''').fetchall()
    agents  = db.execute('SELECT * FROM agents WHERE active=1').fetchall()
    total_r = sum(c['monthly_fee'] or 0 for c in clients if c['status']=='active')
    invoices= db.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 10").fetchall()
    db.close()
    return render_template('admin/clients.html', clients=clients, agents=agents,
                          total_revenue=total_r, invoices=invoices)

@app.route('/admin/clients/add', methods=['POST'])
@login_required
def add_client():
    db = get_db()
    ag = db.execute('SELECT name FROM agents WHERE id=?',(request.form['agent_id'],)).fetchone()
    db.execute('INSERT INTO clients (name,business,phone,email,address,agent_id,agent_name,monthly_fee,install_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?)', (
        request.form['name'], request.form['business'],
        request.form.get('phone',''), request.form.get('email',''),
        request.form.get('address',''), request.form['agent_id'],
        ag['name'] if ag else '', float(request.form.get('monthly_fee',0)),
        datetime.now().strftime('%Y-%m-%d'), request.form.get('notes','')
    ))
    db.commit(); db.close()
    send_whatsapp_notification(f"✅ Nuevo cliente: {request.form['name']}",
        f"Negocio: {request.form['business']}\nAgente: {ag['name'] if ag else ''}\nFee: S/{request.form.get('monthly_fee',0)}/mes")
    flash('Cliente agregado exitosamente','success')
    return redirect(url_for('admin_clients'))

@app.route('/admin/clients/<int:cid>/deactivate', methods=['POST'])
@login_required
def deactivate_client(cid):
    db = get_db()
    db.execute("UPDATE clients SET status='inactive' WHERE id=?", (cid,))
    db.commit(); db.close()
    flash('Cliente desactivado','info')
    return redirect(url_for('admin_clients'))

# ══════════════════════════════════════════════════════════════
#  ADMIN — AGENTES
# ══════════════════════════════════════════════════════════════
@app.route('/admin/agents')
@login_required
def admin_agents():
    db = get_db()
    agents = db.execute('SELECT * FROM agents ORDER BY id').fetchall()
    agents_data = []
    for ag in agents:
        clients = db.execute('SELECT COUNT(*) as n FROM clients WHERE agent_id=? AND status="active"',(ag['id'],)).fetchone()['n']
        revenue = db.execute('SELECT COALESCE(SUM(monthly_fee),0) as t FROM clients WHERE agent_id=? AND status="active"',(ag['id'],)).fetchone()['t']
        tickets = db.execute("SELECT COUNT(*) as n FROM tickets WHERE agent_id=? AND status='open'",(ag['id'],)).fetchone()['n']
        monitor = db.execute('SELECT * FROM agent_monitor WHERE agent_id=?',(ag['id'],)).fetchone()
        agents_data.append({'agent':ag,'clients':clients,'revenue':revenue,'tickets':tickets,'monitor':monitor})
    db.close()
    return render_template('admin/agents.html', agents_data=agents_data)

@app.route('/admin/agents/<int:aid>/toggle', methods=['POST'])
@login_required
def toggle_agent(aid):
    db = get_db()
    current = db.execute('SELECT active FROM agents WHERE id=?',(aid,)).fetchone()['active']
    db.execute('UPDATE agents SET active=? WHERE id=?',(0 if current else 1, aid))
    db.commit(); db.close()
    return jsonify({'ok':True,'active': not current})

@app.route('/admin/agents/<int:aid>/update', methods=['POST'])
@login_required
def update_agent(aid):
    db = get_db()
    db.execute('UPDATE agents SET name=?,description=?,install_price=?,monthly_price=? WHERE id=?', (
        request.form['name'], request.form['description'],
        request.form['install_price'], request.form['monthly_price'], aid
    ))
    db.commit(); db.close()
    flash('Agente actualizado','success')
    return redirect(url_for('admin_agents'))

# ══════════════════════════════════════════════════════════════
#  ADMIN — BASE DE CONOCIMIENTO
# ══════════════════════════════════════════════════════════════
@app.route('/admin/knowledge')
@login_required
def admin_knowledge():
    db = get_db()
    items  = db.execute('SELECT k.*,a.name as agent_name FROM knowledge_base k LEFT JOIN agents a ON k.agent_id=a.id ORDER BY k.views DESC').fetchall()
    agents = db.execute('SELECT id,name FROM agents').fetchall()
    db.close()
    return render_template('admin/knowledge.html', items=items, agents=agents)

@app.route('/admin/knowledge/add', methods=['POST'])
@login_required
def add_knowledge():
    db = get_db()
    db.execute('INSERT INTO knowledge_base (title,content,category,agent_id,created_at) VALUES (?,?,?,?,?)', (
        request.form['title'], request.form['content'],
        request.form.get('category','general'), request.form.get('agent_id') or None,
        datetime.now().isoformat()
    ))
    db.commit(); db.close()
    flash('Artículo agregado','success')
    return redirect(url_for('admin_knowledge'))

# ══════════════════════════════════════════════════════════════
#  ADMIN — FINANZAS / FACTURACIÓN
# ══════════════════════════════════════════════════════════════
@app.route('/admin/finance')
@login_required
def admin_finance():
    db = get_db()
    clients  = db.execute("SELECT * FROM clients WHERE status='active' ORDER BY name").fetchall()
    invoices = db.execute('SELECT * FROM invoices ORDER BY created_at DESC').fetchall()
    revenue  = db.execute("SELECT COALESCE(SUM(monthly_fee),0) as t FROM clients WHERE status='active'").fetchone()['t']
    pending  = db.execute("SELECT COALESCE(SUM(amount),0) as t FROM invoices WHERE status='pending'").fetchone()['t']
    agents_rev = []
    for ag in db.execute('SELECT * FROM agents WHERE active=1').fetchall():
        r = db.execute('SELECT COALESCE(SUM(monthly_fee),0) as t FROM clients WHERE agent_id=? AND status="active"',(ag['id'],)).fetchone()['t']
        agents_rev.append({'name':ag['name'],'color':ag['color'],'revenue':r})
    db.close()
    return render_template('admin/finance.html', clients=clients, invoices=invoices,
                          monthly_revenue=revenue, pending_amount=pending,
                          agents_rev=agents_rev, year_revenue=revenue*12)

@app.route('/admin/finance/invoice/generate', methods=['POST'])
@login_required
def generate_invoice():
    db = get_db()
    client_id = request.form['client_id']
    client = db.execute('SELECT * FROM clients WHERE id=?',(client_id,)).fetchone()
    if client:
        inv_num = f"FAC-{datetime.now().strftime('%Y%m')}-{client_id.zfill(3)}"
        period  = datetime.now().strftime('%B %Y')
        due     = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        db.execute('INSERT OR IGNORE INTO invoices (invoice_number,client_id,client_name,amount,period,due_date,created_at) VALUES (?,?,?,?,?,?,?)',
                  (inv_num, client_id, client['name'], client['monthly_fee'], period, due, datetime.now().isoformat()))
        db.commit()
    db.close()
    return jsonify({'ok':True,'invoice':inv_num if client else None})

# ══════════════════════════════════════════════════════════════
#  ADMIN — LEADS (contactos del sitio público)
# ══════════════════════════════════════════════════════════════
@app.route('/admin/leads')
@login_required
def admin_leads():
    db = get_db()
    leads = db.execute('SELECT * FROM contact_leads ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin/leads.html', leads=leads)

@app.route('/admin/leads/<int:lid>/convert', methods=['POST'])
@login_required
def convert_lead(lid):
    db = get_db()
    db.execute("UPDATE contact_leads SET status='converted' WHERE id=?", (lid,))
    db.commit(); db.close()
    flash('Lead marcado como convertido','success')
    return redirect(url_for('admin_leads'))

# ══════════════════════════════════════════════════════════════
#  API PÚBLICA — los agentes envían tickets
# ══════════════════════════════════════════════════════════════
@app.route('/api/ticket', methods=['POST'])
def api_ticket():
    data = request.json or {}
    db = get_db()
    tkt_num = get_ticket_number()
    db.execute('''INSERT INTO tickets
        (ticket_number,client_name,business,agent_id,agent_name,subject,message,category,priority,status,sla_hours,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        tkt_num, data.get('client_name','Desconocido'), data.get('business',''),
        data.get('agent_id',0), data.get('agent_name','Agente'),
        data.get('subject','Sin asunto'), data.get('message',''),
        data.get('category','consulta'), data.get('priority','normal'),
        'open', 4 if data.get('priority')=='high' else 24,
        datetime.now().isoformat(), datetime.now().isoformat()
    ))
    db.commit(); db.close()
    priority = data.get('priority','normal')
    send_whatsapp_notification(
        f"{'🚨' if priority=='high' else '🎫'} {tkt_num}: {data.get('subject')}",
        f"Cliente: {data.get('client_name')}\nAgente: {data.get('agent_name')}\nPrioridad: {priority.upper()}\n\n{data.get('message','')}"
    )
    return jsonify({'ok':True,'ticket_number':tkt_num,'message':'Ticket creado correctamente'})

@app.route('/api/agents')
def api_agents():
    db = get_db()
    agents = db.execute('SELECT id,name,type,description,color,active FROM agents WHERE active=1').fetchall()
    db.close()
    return jsonify([dict(a) for a in agents])

@app.route('/api/stats')
def api_stats():
    db = get_db()
    data = {
        'clients': db.execute("SELECT COUNT(*) FROM clients WHERE status='active'").fetchone()[0],
        'agents':  db.execute("SELECT COUNT(*) FROM agents WHERE active=1").fetchone()[0],
        'tickets_open': db.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0],
    }
    db.close()
    return jsonify(data)

if __name__ == '__main__':
    init_db()
    print("\n" + "="*52)
    print("  🚀  GONZALO AGENTES IA — INICIANDO")
    print("="*52)
    print(f"  Sitio público: http://localhost:5000")
    print(f"  Panel admin:   http://localhost:5000/admin")
    print(f"  Usuario:       {ADMIN_USER}")
    print(f"  Contraseña:    {ADMIN_PASS}")
    print("="*52 + "\n")
    app.run(debug=True, port=5000)

# Filtro Jinja2 para parsear JSON en templates
import json as _json
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return _json.loads(value) if value else []
    except:
        return []
