from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.db import db
from app.models.user import User
from app.utils.forms import RegisterForm, LoginForm
from app.utils.stripe_service import create_customer
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pdf.dashboard'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            # Para depuração e facilitar o acesso, ativamos a assinatura temporariamente
            print(f"[Login] Ativando assinatura temporária para usuário {user.email}")
            user.subscription_status = 'active'
            user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
            
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('pdf.dashboard'))
        else:
            flash('Email ou senha incorretos. Por favor, tente novamente.', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('pdf.dashboard'))
        
    form = RegisterForm()
    
    if form.validate_on_submit():
        # Verifica se o email já está em uso
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Este email já está em uso. Por favor, use outro email.', 'danger')
            return render_template('register.html', form=form)
        
        # Cria o usuário
        user = User(
            name=form.name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        # Cria o cliente no Stripe
        stripe_customer_id = create_customer(user.name, user.email)
        if stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
        
        # Salva no banco de dados
        db.session.add(user)
        db.session.commit()
        
        flash('Conta criada com sucesso! Agora você pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 