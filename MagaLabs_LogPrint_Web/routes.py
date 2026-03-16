from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from models import db, Device, UsageLog, SupportTicket, User, Ticket, VirtualStock, StockLog, InfraDevice
from datetime import datetime
from functools import wraps
from flask import current_app
from ai_service import generate_ai_insights, technical_chat, suggest_solution
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import logging
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import requests
import json
from dotenv import load_dotenv
import concurrent.futures
import platform
import subprocess

main = Blueprint('main', __name__)

# Custom decorator for role-based access control
def role_required(*roles):
    """Decorator to require specific roles for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            if current_user.role not in roles:
                return redirect(url_for('welcome'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@main.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - renders different templates based on user role"""
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '', type=str)
    per_page = 10
    
    # Query devices based on search
    query = Device.query
    if search_term:
        query = query.filter(
            db.or_(
                Device.name.ilike(f'%{search_term}%'),
                Device.device_type.ilike(f'%{search_term}%'),
                Device.assigned_to_name.ilike(f'%{search_term}%')
            )
        )
    
    # Role-based filtering and template selection
    if current_user.role in ['ti', 'superadmin']:
        # TI and Superadmin see all devices
        devices_query = query
        template = 'dashboard_ti.html'
    elif current_user.role == 'lider':
        # Leadership sees devices in their CD or available
        devices_query = query.outerjoin(User, Device.assigned_to_user_id == User.id)\
                             .filter(db.or_(User.cd == current_user.cd, Device.status == 'available'))
        template = 'dashboard_ti.html'
    else:
        # Collaborators see only devices they have
        devices_query = query.filter_by(assigned_to_user_id=current_user.id)
        template = 'dashboard_colaborador.html'
    
    # Paginate results
    pagination = devices_query.order_by(Device.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Check for pending toner forms (TI/Superadmin/Lider)
    # Even if only TI/Superadmin can resolve, Lider should see the count to know status
    pending_toner_count = 0
    if current_user.role in ['ti', 'superadmin', 'lider']:
        from models import InfraDevice
        try:
            pending_toner_count = InfraDevice.query.filter_by(pending_toner_form=True).count()
        except Exception as e:
            print(f"Erro ao contar pendencias de toner: {e}")
            pending_toner_count = 0

    return render_template(
        template,
        devices=pagination.items,
        pagination_data=pagination,
        search_term=search_term,
        pending_toner_count=pending_toner_count
    )

# ============================================================================
# DEVICE MANAGEMENT ROUTES (TI/Superadmin only)
# ============================================================================

@main.route('/devices')
@login_required
@role_required('ti', 'superadmin')
def manage_devices_page():
    """List all devices with search and pagination"""
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '', type=str)
    per_page = 20
    
    query = Device.query
    if search_term:
        query = query.filter(
            db.or_(
                Device.name.ilike(f'%{search_term}%'),
                Device.device_type.ilike(f'%{search_term}%'),
                Device.serial_number.ilike(f'%{search_term}%')
            )
        )
    
    pagination = query.order_by(Device.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template(
        'manage_devices_list.html',
        devices=pagination.items,
        pagination=pagination,
        search_term=search_term
    )

@main.route('/devices/create', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin')
def create_device():
    """Create a new device"""
    if request.method == 'POST':
        try:
            device = Device(
                name=request.form['name'],
                device_type=request.form['device_type'],
                serial_number=request.form.get('serial_number'),
                status='available'
            )
            db.session.add(device)
            db.session.commit()
            flash('Dispositivo criado com sucesso!', 'success')
            return redirect(url_for('main.manage_devices_page'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar dispositivo: {str(e)}', 'danger')
    
    return render_template('manage_device_form.html', device=None)

@main.route('/devices/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin')
def edit_device(id):
    """Edit an existing device"""
    device = Device.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            device.name = request.form['name']
            device.device_type = request.form['device_type']
            device.serial_number = request.form.get('serial_number')
            device.updated_at = datetime.now()
            db.session.commit()
            flash('Dispositivo atualizado com sucesso!', 'success')
            return redirect(url_for('main.manage_devices_page'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar dispositivo: {str(e)}', 'danger')
    
    return render_template('manage_device_form.html', device=device)

@main.route('/devices/<int:id>/delete', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def delete_device(id):
    """Delete a device"""
    device = Device.query.get_or_404(id)
    try:
        db.session.delete(device)
        db.session.commit()
        flash('Dispositivo excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir dispositivo: {str(e)}', 'danger')
    
    return redirect(url_for('main.manage_devices_page'))

# ============================================================================
# DEVICE OPERATIONS ROUTES
# ============================================================================

@main.route('/devices/<int:device_id>/pickup', methods=['POST'])
@login_required
def device_pickup(device_id):
    """Mark device as picked up by current user"""
    device = Device.query.get_or_404(device_id)
    
    if device.status != 'available':
        flash('Este dispositivo não está disponível.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Update device status
        device.status = 'in_use'
        device.assigned_to_user_id = current_user.id
        device.assigned_to_name = current_user.name
        device.assigned_at = datetime.now()
        
        # Create usage log
        log = UsageLog(
            device_id=device.id,
            user_id=current_user.id,
            user_name=current_user.name,
            action='pickup'
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Dispositivo {device.name} retirado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao retirar dispositivo: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))

@main.route('/devices/<int:device_id>/return', methods=['POST'])
@login_required
def device_return(device_id):
    """Return device to available pool"""
    device = Device.query.get_or_404(device_id)
    
    if device.assigned_to_user_id != current_user.id and current_user.role not in ['ti', 'superadmin']:
        flash('Você não tem permissão para devolver este dispositivo.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Update device status
        device.status = 'available'
        device.assigned_to_user_id = None
        device.assigned_to_name = None
        device.assigned_at = None
        
        # Create usage log
        log = UsageLog(
            device_id=device.id,
            user_id=current_user.id,
            user_name=current_user.name,
            action='return'
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Dispositivo {device.name} devolvido com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao devolver dispositivo: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))

@main.route('/devices/<int:device_id>/report', methods=['POST'])
@login_required
def device_report(device_id):
    """Report a device issue"""
    device = Device.query.get_or_404(device_id)
    
    description = request.form.get('description', '')
    if not description:
        return jsonify({'success': False, 'message': 'Descrição é obrigatória'}), 400
    
    try:
        # Create support ticket
        ticket = SupportTicket(
            device_id=device.id,
            reported_by_user_id=current_user.id,
            reported_by_name=current_user.name,
            description=description
        )
        db.session.add(ticket)
        
        # Update device status
        device.status = 'support'
        device.support_description = description
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Problema reportado com sucesso!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@main.route('/devices/<int:device_id>/resolve-support', methods=['POST'])
@login_required
@role_required('ti', 'superadmin', 'lider')
def device_resolve_support(device_id):
    """Resolve device support ticket"""
    device = Device.query.get_or_404(device_id)
    
    resolution_notes = request.form.get('resolution_notes', '')
    
    try:
        # Find open ticket for this device
        ticket = SupportTicket.query.filter_by(
            device_id=device.id,
            status='open'
        ).first()
        
        if ticket:
            ticket.status = 'resolved'
            ticket.resolved_at = datetime.now()
            ticket.resolved_by_user_id = current_user.id
            ticket.resolved_by_name = current_user.name
            ticket.resolution_notes = resolution_notes
        
        # Update device status
        device.status = 'available'
        device.support_description = None
        
        db.session.commit()
        
        flash('Suporte resolvido com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao resolver suporte: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))

@main.route('/devices/<int:device_id>/history')
@login_required
@role_required('ti', 'superadmin', 'lider')
def device_history(device_id):
    """View device usage history"""
    device = Device.query.get_or_404(device_id)
    
    usage_logs = UsageLog.query.filter_by(device_id=device.id).order_by(
        UsageLog.timestamp.desc()
    ).all()
    
    support_tickets = SupportTicket.query.filter_by(device_id=device.id).order_by(
        SupportTicket.created_at.desc()
    ).all()
    
    return render_template(
        'device_history.html',
        device=device,
        usage_logs=usage_logs,
        support_tickets=support_tickets
    )

@main.route('/devices/<int:device_id>/zendesk', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def update_zendesk_link(device_id):
    """Update Zendesk ticket link for device"""
    device = Device.query.get_or_404(device_id)
    
    zendesk_url = request.form.get('zendesk_url', '')
    
    try:
        device.zendesk_url = zendesk_url
        
        # Also update the open support ticket if exists
        ticket = SupportTicket.query.filter_by(
            device_id=device.id,
            status='open'
        ).first()
        
        if ticket:
            ticket.zendesk_url = zendesk_url
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Link Zendesk atualizado!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Legacy user routes removed

# ============================================================================
# ANALYTICS AND HISTORY ROUTES
# ============================================================================

@main.route('/history')
@login_required
@role_required('ti', 'superadmin', 'lider')
def global_history():
    """View global usage, support tickets and zendesk requests"""
    try:
        page_usage = request.args.get('page_usage', 1, type=int)
        page_support = request.args.get('page_support', 1, type=int)
        page_zendesk = request.args.get('page_zendesk', 1, type=int)
        page_access = request.args.get('page_access', 1, type=int)
        page_toner = request.args.get('page_toner', 1, type=int)
        per_page = 20
        
        # Paginate usage logs
        usage_logs = UsageLog.query.order_by(
            UsageLog.timestamp.desc()
        ).paginate(page=page_usage, per_page=per_page, error_out=False)
        
        # Paginate support tickets (Internal inventory)
        support_tickets = SupportTicket.query.order_by(
            SupportTicket.created_at.desc()
        ).paginate(page=page_support, per_page=per_page, error_out=False)
        
        # Paginate zendesk requests (Ticket model)
        zendesk_tickets = Ticket.query.order_by(
            Ticket.created_at.desc()
        ).paginate(page=page_zendesk, per_page=per_page, error_out=False)

        # Paginate Recent Corporate Auto-Registrations (Users with PENDENTE or first login)
        recent_access = User.query.filter(User.employee_id == 'PENDENTE').order_by(
            User.created_at.desc()
        ).paginate(page=page_access, per_page=per_page, error_out=False)
        
        # Paginate toner replacement forms
        from models import TonerChange
        toner_changes = TonerChange.query.order_by(
            TonerChange.timestamp.desc()
        ).paginate(page=page_toner, per_page=per_page, error_out=False)
        
        return render_template(
            'global_history.html',
            logs=usage_logs,
            tickets=support_tickets,
            zendesk_tickets=zendesk_tickets,
            recent_access=recent_access,
            toner_changes=toner_changes
        )
    except Exception as e:
        print(f"ERRO NO HISTORICO GLOBAL: {str(e)}")
        # If it fails, maybe due to schema mismatch, return a simple error message
        flash(f'Erro ao carregar histórico: {str(e)}', 'danger')
        return redirect(url_for('welcome'))

@main.route('/analytics')
@login_required
@role_required('ti', 'superadmin', 'lider')
def ai_analise_page():
    """AI analysis page with real Gemini integration"""
    total_devices = Device.query.count()
    available_devices = Device.query.filter_by(status='available').count()
    in_use_devices = Device.query.filter_by(status='in_use').count()
    support_devices = Device.query.filter_by(status='support').count()
    open_tickets = SupportTicket.query.filter_by(status='open').count()
    
    # Pegar logs recentes para contexto da IA
    recent_logs = UsageLog.query.order_by(UsageLog.timestamp.desc()).limit(15).all()
    logs_text = "\n".join([f"{l.timestamp}: {l.user_name} fez {l.action} no dispositivo {l.device_id}" for l in recent_logs])

    stats = {
        'total': total_devices,
        'available': available_devices,
        'in_use': in_use_devices,
        'support': support_devices,
        'open_tickets': open_tickets
    }

    # Chamar o serviço de IA
    api_key = current_app.config.get('GEMINI_API_KEY')
    ai_result = generate_ai_insights(api_key, stats, logs_text, open_tickets)

    return render_template(
        'ai_analise.html',
        total_devices=total_devices,
        available_devices=available_devices,
        in_use_devices=in_use_devices,
        support_devices=support_devices,
        open_tickets=open_tickets,
        ai_pattern_alert=ai_result.get('pattern_alert'),
        ai_recommendation=ai_result.get('recommendation')
    )
@main.route('/ai-chat', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin', 'lider')
def ai_chat():
    """Technical Chat with Gemini"""
    if request.method == 'POST':
        user_message = request.json.get('message')
        
        # Preparar contexto para o chat
        devices = Device.query.all()
        tickets = SupportTicket.query.filter_by(status='open').all()
        
        context = f"Dispositivos: {[d.name for d in devices]}\nChamados Abertos: {[t.description for t in tickets]}"
        
        api_key = current_app.config.get('GEMINI_API_KEY')
        response = technical_chat(api_key, user_message, context)
        
        return jsonify({'response': response})

    return render_template('ai_chat.html')
@main.route('/stock', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin', 'lider')
def inventory():
    """Manage virtual hardware stock (Toners, Printers, Peripherals)"""
    if request.method == 'POST':
        category = request.form.get('category')
        model = request.form.get('model')
        quantity = request.form.get('quantity', 0, type=int)
        min_qty = request.form.get('min_quantity', 5, type=int)
        
        existing = VirtualStock.query.filter_by(model=model).first()
        if existing:
            existing.quantity += quantity
            action_note = f"Entrada manual de {quantity} unidades"
        else:
            existing = VirtualStock(category=category, model=model, quantity=quantity, min_quantity=min_qty)
            db.session.add(existing)
            db.session.flush() # To get the id
            action_note = "Cadastro inicial no estoque"
            flash(f'Novo modelo {model} ({category}) adicionado ao estoque!', 'success')
        
        # Log the movement
        log = StockLog(
            stock_id=existing.id,
            user_id=current_user.id,
            user_name=current_user.name,
            action='add',
            quantity=quantity,
            notes=action_note
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Estoque de {model} atualizado!', 'success')
        return redirect(url_for('main.inventory'))
    
    # Grouped inventory for the view
    toners = VirtualStock.query.filter_by(category='Toner').order_by(VirtualStock.model).all()
    printers = VirtualStock.query.filter_by(category='Printer').order_by(VirtualStock.model).all()
    peripherals = VirtualStock.query.filter_by(category='Peripheral').order_by(VirtualStock.model).all()
    
    return render_template('inventory.html', toners=toners, printers=printers, peripherals=peripherals)

@main.route('/stock/update/<int:id>', methods=['POST'])
@login_required
@role_required('ti', 'superadmin', 'lider')
def update_stock(id):
    item = VirtualStock.query.get_or_404(id)
    new_qty = request.form.get('quantity', type=int)
    
    if new_qty is not None:
        diff = new_qty - item.quantity
        item.quantity = new_qty
        
        # Log the movement
        log = StockLog(
            stock_id=item.id,
            user_id=current_user.id,
            user_name=current_user.name,
            action='add' if diff > 0 else 'remove',
            quantity=abs(diff),
            notes=f"Atualização manual: para {new_qty}"
        )
        db.session.add(log)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Determinar novo status/badge para resposta AJAX
            status_html = ""
            if item.quantity <= 0: status_html = '<span class="badge-pill badge-danger-light">Esgotado</span>'
            elif (item.category == 'Toner' and item.quantity < 5) or (item.quantity <= item.min_quantity):
                status_html = '<span class="badge-pill badge-danger-light">ALERTA < 5</span>' if item.category == 'Toner' and item.quantity < 5 else '<span class="badge-pill badge-warning-light">Baixo</span>'
            else: status_html = '<span class="badge-pill badge-success-light">OK</span>'
            
            return jsonify({
                'success': True, 
                'new_qty': f"{item.quantity} unidades",
                'status_html': status_html
            })

        flash(f'Quantidade de {item.model} alterada para {new_qty}.', 'success')
    return redirect(url_for('main.inventory'))

@main.route('/stock/delete/<int:id>', methods=['POST'])
@login_required
@role_required('ti', 'superadmin', 'lider')
def delete_stock(id):
    item = VirtualStock.query.get_or_404(id)
    
    # Log the deletion as a complete removal before actually deleting
    log = StockLog(
        stock_id=None, # Cannot reference deleted item ID
        user_id=current_user.id,
        user_name=current_user.name,
        action='remove',
        quantity=item.quantity,
        notes=f"Item Excluído do Sistema: {item.category} - {item.model}"
    )
    db.session.add(log)
    
    # Actually delete from db
    db.session.delete(item)
    db.session.commit()
    
    flash(f'{item.category} "{item.model}" foi excluído permanentemente.', 'success')
    return redirect(url_for('main.inventory'))

@main.route('/export/<string:report_type>')
@login_required
@role_required('ti', 'superadmin', 'lider')
def export_report(report_type):
    """Export status files (Excel/CSV) for Stock and Movements"""
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    
    if report_type == 'inventory':
        items = VirtualStock.query.all()
        data = [{
            'Categoria': i.category,
            'Modelo': i.model,
            'Quantidade': i.quantity,
            'Mínimo': i.min_quantity,
            'Última Atualização': i.last_updated.strftime('%d/%m/%Y %H:%M')
        } for i in items]
        filename = f"estoque_virtual_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df = pd.DataFrame(data)
    elif report_type == 'movements':
        logs = StockLog.query.order_by(StockLog.timestamp.desc()).all()
        data = [{
            'Data': l.timestamp.strftime('%d/%m/%Y %H:%M'),
            'Item': l.item.model if l.item else 'N/A',
            'Categoria': l.item.category if l.item else 'N/A',
            'Usuário': l.user_name,
            'Ação': 'Entrada' if l.action == 'add' else 'Saída',
            'Quantidade': l.quantity,
            'Chamado': f"#{l.ticket_id}" if l.ticket_id else '-',
            'Notas': l.notes
        } for l in logs]
        filename = f"movimentacao_estoque_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df = pd.DataFrame(data)
    else:
        flash('Tipo de relatório inválido', 'danger')
        return redirect(url_for('main.dashboard'))

    # Generate Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# ============================================================================
# USER MANAGEMENT (TI ONLY)
# ============================================================================

@main.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin')
def manage_users():
    """TI Management of users and passwords"""
    if request.method == 'POST':
        # Create new user with temp password
        username = request.form.get('username')
        email = request.form.get('email')
        name = request.form.get('name')
        emp_id = request.form.get('employee_id')
        role = request.form.get('role', 'user') # 'user', 'lider', 'ti', 'superadmin'
        cd = request.form.get('cd')
        sector = request.form.get('sector', 'Logística')
        temp_pwd = request.form.get('password', '').strip()

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Usuário ou E-mail já existe!', 'danger')
        else:
            new_user = User(
                username=username,
                email=email,
                name=name,
                employee_id=emp_id,
                role=role,
                cd=cd,
                sector=sector,
                first_login=True
            )
            new_user.set_password(temp_pwd)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Usuário {name} criado com sucesso! Senha provisória definida.', 'success')
        
    users = User.query.order_by(User.name).all()
    return render_template('manage_users.html', users=users)

@main.route('/users/reset-password/<int:id>', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def reset_password(id):
    user = User.query.get_or_404(id)
    temp_pwd = request.form.get('new_password', '').strip()
    user.set_password(temp_pwd)
    user.first_login = True
    db.session.commit()
    flash(f'Senha de {user.name} resetada! Troca obrigatória no próximo acesso.', 'success')
    return redirect(url_for('main.manage_users'))

@main.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def delete_user(id):
    if current_user.id == id:
        flash('Você não pode excluir a si mesmo!', 'danger')
    else:
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        flash('Usuário excluído.', 'success')
    return redirect(url_for('main.manage_users'))

@main.route('/users/edit/<int:id>', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def edit_user(id):
    user = User.query.get_or_404(id)
    
    user.name = request.form.get('name')
    user.username = request.form.get('username')
    user.email = request.form.get('email')
    user.employee_id = request.form.get('employee_id')
    user.role = request.form.get('role')
    user.cd = request.form.get('cd')
    user.sector = request.form.get('sector')
    
    try:
        db.session.commit()
        flash(f'Dados de {user.name} atualizados com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar usuário: {str(e)}', 'danger')
        
    return redirect(url_for('main.manage_users'))

# ============================================================================
# INFRA MONITORING ROUTES (TI/Superadmin only)
# ============================================================================

@main.route('/infra')
@login_required
@role_required('ti', 'superadmin', 'lider')
def infra_status():
    """Infra Status Dashboard"""
    from models import InfraDevice
    devices = InfraDevice.query.filter_by(is_active=True).order_by(InfraDevice.name).all()
    return render_template('infra_status.html', devices=devices)

@main.route('/infra/manage', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin')
def manage_infra():
    """Manage IPs/Devices for Infra Bot"""
    from models import InfraDevice
    if request.method == 'POST':
        ip = request.form.get('ip')
        name = request.form.get('name')
        device_type = request.form.get('device_type')
        
        existing = InfraDevice.query.filter_by(ip=ip).first()
        if existing:
            existing.name = name
            existing.device_type = device_type
            existing.is_active = True
            flash(f'Dispositivo {ip} atualizado!', 'info')
        else:
            new_dev = InfraDevice(ip=ip, name=name, device_type=device_type)
            db.session.add(new_dev)
            flash(f'Dispositivo {name} adicionado com sucesso!', 'success')
        
        db.session.commit()
        return redirect(url_for('main.manage_infra'))

    devices = InfraDevice.query.order_by(InfraDevice.name).all()
    return render_template('manage_infra.html', devices=devices)

@main.route('/infra/toggle/<int:id>', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def toggle_infra(id):
    from models import InfraDevice
    device = InfraDevice.query.get_or_404(id)
    device.is_active = not device.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': device.is_active})

@main.route('/infra/check-now', methods=['POST'])
@login_required
@role_required('ti', 'superadmin')
def infra_check_now():
    """Trigger an immediate check (Manual trigger) using multithreading for performance"""
    from models import InfraDevice
    
    devices = InfraDevice.query.filter_by(is_active=True).all()
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    
    def check_device(dev_id):
        # We need to re-query or use a scoped session inside the thread if not careful,
        # but since we are just updating and committing at the end, and this is a simple check:
        with current_app.app_context():
            dev = InfraDevice.query.get(dev_id)
            command = ['ping', param, '1', '-w', '1000', dev.ip]
            try:
                subprocess.check_call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                dev.status = 'OK'
                dev.details = 'Manual check success'
            except:
                dev.status = 'DOWN'
                dev.details = 'Manual check failed'
            dev.last_check = datetime.now()
            db.session.add(dev)
            db.session.commit()

    # Use ThreadPoolExecutor to run pings in parallel
    device_ids = [d.id for d in devices]
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(check_device, device_ids)
    
    flash('Check manual concluído para todos os dispositivos em paralelo!', 'success')
    return redirect(url_for('main.infra_status'))

# ============================================================================
# TONER MANAGEMENT ROUTES (TI/Superadmin only)
# ============================================================================

@main.route('/toner/register', methods=['GET', 'POST'])
@login_required
@role_required('ti', 'superadmin')
def toner_register():
    from models import TonerChange, InfraDevice, VirtualStock, StockLog
    if request.method == 'POST':
        printer_ip = request.form.get('printer_ip')
        printer_model = request.form.get('printer_model')
        toner_model = request.form.get('toner_model')
        counter = request.form.get('counter')
        
        if not printer_ip or not counter:
            flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('main.toner_register'))

        device = InfraDevice.query.filter_by(ip=printer_ip).first()
        
        new_change = TonerChange(
            ti_name=current_user.name,
            ti_login=current_user.username,
            ti_employee_id=current_user.employee_id,
            printer_ip=printer_ip,
            printer_name=device.name if device else "Desconhecida",
            printer_model=printer_model or "N/A",
            toner_model=toner_model or "N/A",
            counter_number=int(counter),
            user_id=current_user.id
        )
        
        # Mark pending as resolved if it exists
        if device:
            device.pending_toner_form = False
            device.last_toner_change = datetime.now()
            
        # Optional: Deduct from VirtualStock if possible
        stock_item = VirtualStock.query.filter_by(model=toner_model).first()
        if stock_item:
            if stock_item.quantity > 0:
                stock_item.quantity -= 1
                log = StockLog(
                    stock_id=stock_item.id,
                    user_id=current_user.id,
                    user_name=current_user.name,
                    action='remove',
                    quantity=1,
                    notes=f'Troca de toner na impressora {printer_ip}'
                )
                db.session.add(log)
            else:
                flash(f'Atenção: Estoque de {toner_model} está zerado, mas a troca foi registrada.', 'warning')
            
        db.session.add(new_change)
        db.session.commit()
        flash('Troca de toner registrada com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
        
    printers = InfraDevice.query.filter(InfraDevice.device_type.like('Printer%')).all()
    # If a specific printer IP is passed via query string
    selected_ip = request.args.get('ip', '')
    return render_template('toner_form.html', printers=printers, selected_ip=selected_ip)

@main.route('/toner/pending')
@login_required
@role_required('ti', 'superadmin')
def toner_pending_list():
    from models import InfraDevice
    pending = InfraDevice.query.filter_by(pending_toner_form=True).all()
    return render_template('toner_pending.html', pending=pending)
