from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True) # Corporate email
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user', 'ti', 'lider', 'superadmin'
    cd = db.Column(db.String(50), nullable=True)     # Filial
    sector = db.Column(db.String(100), nullable=True) # Setor
    first_login = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Hash and store password using bcrypt"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Verify password against stored hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Solicitor Details
    zendesk_id = db.Column(db.String(255), nullable=False)
    solicitor_id = db.Column(db.String(50), nullable=False)
    solicitor_login = db.Column(db.String(50), nullable=False)
    solicitor_name = db.Column(db.String(100), nullable=False)
    solicitor_sector = db.Column(db.String(100), nullable=False)
    solicitor_cd = db.Column(db.String(50), nullable=False)
    
    # Problem Details
    problem_description = db.Column(db.Text, nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)  # 'Printer' or 'Computer'
    asset_identifier = db.Column(db.String(100), nullable=False) # Model+IP OR Hostname
    attachment_path = db.Column(db.String(255), nullable=True) # Comprovante do Zendesk (Opcional)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='Open') # 'Open', 'Closed'
    
    # Resolution Details (Filled by IT)
    resolver_name = db.Column(db.String(100), nullable=True)
    resolver_id = db.Column(db.String(50), nullable=True)
    resolver_login = db.Column(db.String(50), nullable=True)
    toner_model = db.Column(db.String(100), nullable=True)
    counter_number = db.Column(db.Integer, nullable=True)
    resolution_note = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Ticket {self.id} - Zendesk: {self.zendesk_id}>'

class Device(db.Model):
    """Device model for tracking equipment (tablets, phones, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)  # 'Tablet', 'Phone', etc.
    serial_number = db.Column(db.String(100), unique=True, nullable=True)
    status = db.Column(db.String(20), default='available')  # 'available', 'in_use', 'support'
    
    # Current assignment
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_to_name = db.Column(db.String(100), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    
    # Support tracking
    zendesk_url = db.Column(db.String(255), nullable=True)
    support_description = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    usage_logs = db.relationship('UsageLog', backref='device', lazy=True, cascade='all, delete-orphan')
    support_tickets = db.relationship('SupportTicket', backref='device', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Device {self.name} - {self.status}>'

class UsageLog(db.Model):
    """Log of device pickups and returns"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    
    action = db.Column(db.String(20), nullable=False)  # 'pickup', 'return'
    timestamp = db.Column(db.DateTime, default=datetime.now)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<UsageLog {self.action} - Device {self.device_id} by {self.user_name}>'

class SupportTicket(db.Model):
    """Support tickets for device issues"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    
    reported_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_by_name = db.Column(db.String(100), nullable=False)
    
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # 'open', 'resolved'
    
    zendesk_url = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolved_by_name = db.Column(db.String(100), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<SupportTicket {self.id} - Device {self.device_id} - {self.status}>'

class VirtualStock(db.Model):
    """Inventory control for hardware (toners, printers, peripherals)"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # 'Toner', 'Printer', 'Peripheral'
    model = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    min_quantity = db.Column(db.Integer, default=5) 
    last_updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<VirtualStock {self.category} - {self.model}: {self.quantity}>'

class StockLog(db.Model):
    """Logs all stock movements for auditing"""
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('virtual_stock.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=True)
    action = db.Column(db.String(20), nullable=False) # 'add', 'remove'
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    notes = db.Column(db.Text, nullable=True)

    # Relationship
    item = db.relationship('VirtualStock', backref=db.backref('logs', lazy=True))

    def __repr__(self):
        return f'<StockLog {self.action} - {self.quantity} of {self.stock_id} by {self.user_name}>'

class InfraDevice(db.Model):
    """Network devices monitored by the CDS Infra Bot"""
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False) # 'Link', 'PC', 'Printer_HP', 'Printer_Zebra'
    category = db.Column(db.String(100), nullable=True, default='General')
    status = db.Column(db.String(20), default='UNKNOWN')   # 'OK', 'DOWN', 'OSCILLATING', 'UNKNOWN'
    details = db.Column(db.Text, nullable=True)
    toner_level = db.Column(db.Integer, nullable=True)     # 0-100% (HP Laser)
    last_toner_change = db.Column(db.DateTime, nullable=True)
    label_level = db.Column(db.Integer, nullable=True)     # 0-100% (Zebra)
    ribbon_level = db.Column(db.Integer, nullable=True)    # 0-100% (Zebra)
    last_label_change = db.Column(db.DateTime, nullable=True)
    last_ribbon_change = db.Column(db.DateTime, nullable=True)
    last_check = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    pending_toner_form = db.Column(db.Boolean, default=False) # Flag for missing register

    def __repr__(self):
        return f'<InfraDevice {self.name} ({self.ip}) - {self.status}>'

class TonerChange(db.Model):
    """Manual registry for toner replacements as requested by TI"""
    id = db.Column(db.Integer, primary_key=True)
    ti_name = db.Column(db.String(100), nullable=False)
    ti_login = db.Column(db.String(50), nullable=False)
    ti_employee_id = db.Column(db.String(50), nullable=False)
    
    printer_ip = db.Column(db.String(50), nullable=False)
    printer_name = db.Column(db.String(100), nullable=False)
    printer_model = db.Column(db.String(100), nullable=False)
    toner_model = db.Column(db.String(100), nullable=False)
    counter_number = db.Column(db.Integer, nullable=False)
    
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f'<TonerChange {self.printer_name} ({self.timestamp}) by {self.ti_name}>'
