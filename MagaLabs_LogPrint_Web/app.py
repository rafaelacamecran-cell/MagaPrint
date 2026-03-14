from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# Force reload - MagaPrint Dashboard Fix
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Ticket, User, VirtualStock, StockLog, InfraDevice
from datetime import datetime
from functools import wraps
import os
from werkzeug.utils import secure_filename
from routes import main
from flask_mail import Mail, Message
from ai_service import suggest_solution
import logging
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
import requests
import json
from dotenv import load_dotenv

# Load environment variables
def find_and_load_env():
    # Try current directory
    if os.path.exists('.env'):
        load_dotenv('.env')
        return True
    # Try parent directory (if run from MagaLabs_LogPrint_Web)
    parent_env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(parent_env):
        load_dotenv(parent_env)
        return True
    return False

env_loaded = find_and_load_env()

app = Flask(__name__)

# --- CONFIGURAÇÕES DE LOGS (JSON) ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Limpa handlers existentes (padrão do Flask)
if logger.hasHandlers():
    logger.handlers.clear()

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

app.logger.info("Aplicação iniciada e logs configurados em JSON")

# --- CONFIGURAÇÕES DE MÉTRICAS (PROMETHEUS) ---
HOME_PAGE_ACCESSES = Counter('home_page_accesses_total', 'Total de acessos a pagina inicial (welcome/login)')
TOTAL_ASSETS = Gauge('total_assets', 'Total de ativos cadastrados no sistema (VirtualStock + Devices)')

# Registro de métrica dinâmica - evitando problemas de escopo e db
def collect_assets_total():
    """Coleta dinâmica do DB dentro de app_context sempre que for raspado o /metrics"""
    try:
        from models import Device, VirtualStock
        # Como metrics.wsgi e metrics.generate_latest correm nesse thread,
        # forçamos o contexto se necessário.
        with app.app_context():
            return Device.query.count() + VirtualStock.query.count()
    except Exception as e:
        app.logger.error(f"Erro coletando métrica de ativos: {e}")
        return 0

TOTAL_ASSETS.set_function(collect_assets_total)

# --- CONFIGURAÇÕES ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'magalabs_secret_key_123')
# Default to local postgres if not provided, but allow override via DATABASE_URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql+pg8000://postgres:PASSWORD@localhost:5432/MagaLabsLogPrint')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', 'SUA_CHAVE_API_AQUI')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Max
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- CONFIGURAÇÕES DE E-MAIL (SMTP) ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.google.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'seu-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'sua-senha-app')
app.config['MAIL_DEFAULT_SENDER'] = (
    os.environ.get('MAIL_SENDER_NAME', 'MagaLabs Alert'),
    os.environ.get('MAIL_USERNAME', 'seu-email@gmail.com')
)

mail = Mail(app)

# Inicialização do Banco de Dados
db.init_app(app)

# --- FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Nome da função de login
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- REGISTRO DE BLUEPRINTS ---
# Isso permite que url_for('main.alguma_coisa') funcione se as rotas estiverem no routes.py
app.register_blueprint(main)

# --- DECORATOR DE ACESSO ---
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            if current_user.role not in roles:
                # Silently redirect to welcome if no permission
                return redirect(url_for('welcome'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def send_gchat_alert(message):
    webhook_url = os.environ.get('GCHAT_SOLICITATION_WEBHOOK')
    
    if not webhook_url:
        app.logger.warning("GCHAT_SOLICITATION_WEBHOOK não configurada ou não carregada.")
        return
    
    app.logger.info(f"Enviando alerta para GChat (Webhook: {webhook_url[:40]}...)")
    
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 200:
            app.logger.info("Alerta enviado com sucesso para o Google Chat.")
        else:
            app.logger.error(f"Falha ao enviar alerta. Status: {response.status_code}, Resposta: {response.text}")
        response.raise_for_status()
    except Exception as e:
        app.logger.error(f"Erro ao enviar alerta para o Google Chat: {e}")

@app.route('/test-alert')
def test_alert_route():
    msg = "🔔 *Teste de Alerta Direto (MagaPrint)*\nSe você está vendo isso, as notificações de chamados estão configuradas corretamente!"
    send_gchat_alert(msg)
    return "Alerta enviado para GCHAT_SOLICITATION_WEBHOOK. Verifique o grupo MagaPrint."

# --- ROTAS ---

@app.route('/')
def welcome():
    HOME_PAGE_ACCESSES.inc()
    app.logger.info("Página inicial acessada (Welcome)")
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role in ['ti', 'superadmin']:
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('solicitar'))
    
    if request.method == 'POST':
        login_input = request.form.get('username', '').strip() # can be username or email
        password = request.form.get('password', '').strip()
        
        # Search by username OR email (case-insensitive for robust login)
        user = User.query.filter(
            (db.func.lower(User.username) == login_input.lower()) | 
            (db.func.lower(User.email) == login_input.lower())
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.now()
            db.session.commit()
            app.logger.info(f"Usuário {user.username} autenticado com sucesso")
            
            if user.first_login:
                flash('Este é o seu primeiro acesso. Por favor, altere sua senha.', 'info')
                return redirect(url_for('change_password'))
            
            if user.role in ['ti', 'superadmin']:
                return redirect(url_for('main.dashboard'))
            else:
                return redirect(url_for('solicitar'))
        else:
            app.logger.warning(f"Tentativa de login falhou para identificador: {login_input}")
            flash('Usuário ou senha inválidos.', 'danger')
    
    return render_template('login.html')

@app.route('/sso-login')
def sso_login():
    """Mock redirect to corporate email provider (Google Workspace)"""
    # For demonstration, we redirect to a mock page that simulates Google Login
    return render_template('sso_mock.html')

@app.route('/sso-callback', methods=['GET', 'POST'])
def sso_callback():
    """Handle return from corporate email provider with domain validation"""
    email = request.args.get('email', '').lower()
    if not email:
        flash('Falha na autenticação via E-mail Corporativo.', 'danger')
        return redirect(url_for('login'))
    
    # Restrict to corporate domains ONLY
    allowed_domains = ['magazineluiza.com.br', 'luizalabs.com']
    domain = email.split('@')[-1] if '@' in email else ''
    
    if domain not in allowed_domains:
        flash(f'Acesso negado. O e-mail {email} não pertence aos domínios corporativos permitidos.', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(email=email).first()
    if user:
        login_user(user, remember=True)
        flash(f'Bem-vindo de volta, {user.name}!', 'success')
        if user.role in ['ti', 'superadmin']:
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('solicitar'))
    else:
        # AUTO-REGISTER Corporate Email
        # We'll create a new user with placeholder details that they MUST update
        new_user = User(
            username=email.split('@')[0], # Initial username from email
            email=email,
            name=email.split('@')[0].replace('.', ' ').title(), # Attempt to format name
            employee_id='PENDENTE',
            role='user',
            sector='Logística', # Default sector for auto-identification
            first_login=True
        )
        # Random initial password (they'll likely use SSO anyway, but good for local login)
        import secrets
        new_password = secrets.token_urlsafe(12)
        new_user.set_password(new_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Enviar Alerta de E-mail para Rafaela
        try:
            msg = Message("ALERTA: Novo Acesso Corporativo MagaPrint",
                          recipients=["rafaela.camecran@luizalabs.com"])
            msg.body = f"""
            Olá Rafaela,

            Um novo colaborador foi reconhecido e autorizado automaticamente no sistema:

            Nome: {new_user.name}
            E-mail: {new_user.email}
            Login Sugerido: {new_user.username}
            Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

            O acesso foi liberado por se tratar de um domínio corporativo autorizado.
            Você pode gerenciar este usuário no painel administrativo.

            Atenciosamente,
            MagaBot Assistente
            """
            # mail.send(msg) # Descomente após configurar o SMTP real
            print(f"ALERTA ENVIADO PARA RAFAELA: Novo usuário {new_user.email}")
        except Exception as e:
            print(f"Erro ao enviar e-mail de alerta: {e}")

        # Log this auto-registration as an "Access Alert" for TI
        # We can flash a notification for the user
        flash(f'Sua conta corporativa foi reconhecida e autorizada automaticamente! Bem-vindo.', 'success')
        login_user(new_user, remember=True)
        return redirect(url_for('solicitar'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return redirect(url_for('change_password'))
        
        current_user.set_password(new_password)
        current_user.first_login = False
        db.session.commit()
        flash('Senha alterada com sucesso!', 'success')
        
        if current_user.role in ['ti', 'superadmin']:
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('solicitar'))
    
    return render_template('change_password.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if user:
            flash(f'Olá {user.name}, por favor procure seu líder imediato ou o time de T.I Logística para resetar sua senha.', 'info')
        else:
            flash('Usuário não encontrado em nossa base de dados.', 'danger')
        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/solicitar', methods=['GET', 'POST'])
@login_required
# Anyone logged in can solicit (Collaborators)
def solicitar():
    if request.method == 'POST':
        try:
            new_ticket = Ticket(
                zendesk_id=request.form['zendesk_id'],
                solicitor_id=request.form['solicitor_id'],
                solicitor_login=request.form['solicitor_login'],
                solicitor_name=request.form['solicitor_name'],
                solicitor_sector=request.form['solicitor_sector'],
                solicitor_cd=request.form['solicitor_cd'],
                problem_description=request.form['problem_description'],
                asset_type=request.form['asset_type'],
                asset_identifier=f"{request.form.get('printer_model', '')} | Host: {request.form.get('printer_hostname', 'N/A')} | IP: {request.form.get('printer_ip', 'N/A')}"
            )

            # Handle File Upload (Optional now)
            file = request.files.get('attachment')
            if file and file.filename != '':
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(os.path.join(app.root_path, filepath))
                new_ticket.attachment_path = filepath

            db.session.add(new_ticket)
            db.session.commit()

            # Enviar Alerta para o Google Chat
            try:
                msg = f"🆕 *Nova Solicitação MagaPrint*\n"
                msg += f"👤 *Solicitante:* {new_ticket.solicitor_name} ({new_ticket.solicitor_login})\n"
                msg += f"📍 *CD:* {new_ticket.solicitor_cd} | *Setor:* {new_ticket.solicitor_sector}\n"
                msg += f"🛠️ *Tipo:* {new_ticket.asset_type}\n"
                msg += f"📦 *Equipamento:* {new_ticket.asset_identifier}\n"
                msg += f"📝 *Problema:* {new_ticket.problem_description}\n"
                msg += f"🔗 *Zendesk:* {new_ticket.zendesk_id}"
                send_gchat_alert(msg)
            except Exception as e:
                app.logger.error(f"Erro no fluxo de notificação: {e}")

            flash('Solicitação registrada com sucesso!', 'success')
            return redirect(url_for('welcome'))
        except Exception as e:
            flash(f'Erro: {str(e)}', 'danger')
            return redirect(url_for('solicitar'))
    return render_template('solicitar.html')

@app.route('/resolver/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin')
def resolver(id):
    ticket = Ticket.query.get_or_404(id)
    # Fetch stock items for the form - grouped by category
    toners = VirtualStock.query.filter_by(category='Toner').order_by(VirtualStock.model).all()
    hardware = VirtualStock.query.filter(VirtualStock.category != 'Toner').order_by(VirtualStock.category, VirtualStock.model).all()
    
    if request.method == 'POST':
        ticket.resolver_name = request.form['resolver_name']
        ticket.resolver_login = request.form['resolver_login']
        ticket.resolver_id = request.form['resolver_id']
        ticket.toner_model = request.form.get('toner_model')
        ticket.counter_number = request.form.get('counter_number')
        ticket.resolution_note = request.form.get('resolution_note')
        ticket.resolved_at = datetime.now()
        ticket.status = 'Closed'

        # Automatic stock deduction
        replacements = request.form.getlist('stock_items')
        for stock_id in replacements:
            stock_item = VirtualStock.query.get(stock_id)
            if stock_item and stock_item.quantity > 0:
                stock_item.quantity -= 1
                # Log the movement
                log = StockLog(
                    stock_id=stock_item.id,
                    user_id=current_user.id,
                    user_name=current_user.name,
                    ticket_id=ticket.id,
                    action='remove',
                    quantity=1,
                    notes=f"Troca automática via Chamado #{ticket.id}"
                )
                db.session.add(log)
                flash(f'Item {stock_item.model} ({stock_item.category}) baixado do estoque.', 'info')
            elif stock_item:
                flash(f'ALERTA: Item {stock_item.model} não possui saldo no estoque!', 'warning')

        db.session.commit()
        flash(f'Chamado #{id} finalizado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('resolver.html', ticket=ticket, toners=toners, hardware=hardware)

@app.route('/ai_suggest_solution', methods=['POST'])
@login_required
def ai_suggest_solution():
    data = request.json
    problem = data.get('problem')
    asset = data.get('asset')
    
    api_key = app.config.get('GEMINI_API_KEY')
    suggestion = suggest_solution(api_key, problem, asset)
    
    return jsonify({'suggestion': suggestion})

@app.route('/metrics')
def metrics():
    app.logger.info("Endpoint /metrics coletado pelo Prometheus")
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    with app.app_context():
        # Sincronização básica do banco
        db.create_all()
        
        # Garantir que a coluna 'cd' existe na tabela 'user'
        from sqlalchemy import text
        try:
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS cd VARCHAR(50)'))
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS sector VARCHAR(100)'))
            # Monitoring enhancements - HP
            db.session.execute(text('ALTER TABLE "infra_device" ADD COLUMN IF NOT EXISTS toner_level INTEGER'))
            db.session.execute(text('ALTER TABLE "infra_device" ADD COLUMN IF NOT EXISTS last_toner_change TIMESTAMP'))
            # Monitoring enhancements - Zebra
            db.session.execute(text('ALTER TABLE "infra_device" ADD COLUMN IF NOT EXISTS label_level INTEGER'))
            db.session.execute(text('ALTER TABLE "infra_device" ADD COLUMN IF NOT EXISTS ribbon_level INTEGER'))
            db.session.execute(text('ALTER TABLE "infra_device" ADD COLUMN IF NOT EXISTS last_label_change TIMESTAMP'))
            db.session.execute(text('ALTER TABLE "infra_device" ADD COLUMN IF NOT EXISTS last_ribbon_change TIMESTAMP'))
            db.session.commit()
        except:
            db.session.rollback()

        # Fix: Garantir que ra_camecran é Super Admin e T.I
        u = User.query.filter_by(username='ra_camecran').first()
        if u:
            u.role = 'superadmin'
            db.session.commit()
            print(f"Status do Usuário {u.username} atualizado para Super Admin.")

    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=True)