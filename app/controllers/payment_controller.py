from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app.models.db import db
from app.models.user import User
from app.utils.stripe_service import create_checkout_session, get_subscription, handle_subscription_event, cancel_subscription
import os
import stripe

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/subscription')
@login_required
def subscription():
    # Se o usuário já está inscrito, mostre a página de gerenciamento
    if current_user.is_subscribed():
        return render_template('subscription_management.html')
    
    # Caso contrário, mostre a página para se inscrever
    return render_template('subscription.html')

@payment_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout():
    if not current_user.stripe_customer_id:
        flash('Erro ao criar sessão de pagamento. Por favor, entre em contato com o suporte.', 'danger')
        return redirect(url_for('payment.subscription'))
    
    # URLs de sucesso e cancelamento
    success_url = url_for('payment.subscription_success', _external=True)
    cancel_url = url_for('payment.subscription', _external=True)
    
    # ID do preço no Stripe
    price_id = os.environ.get('STRIPE_PRICE_ID')
    
    # Cria a sessão de checkout
    checkout_session = create_checkout_session(
        current_user.stripe_customer_id,
        price_id,
        success_url,
        cancel_url
    )
    
    if not checkout_session:
        flash('Erro ao criar sessão de pagamento. Por favor, tente novamente.', 'danger')
        return redirect(url_for('payment.subscription'))
    
    # Redireciona para a página de checkout do Stripe
    return redirect(checkout_session.url)

@payment_bp.route('/subscription-success')
@login_required
def subscription_success():
    flash('Obrigado por assinar o AI Reader! Agora você tem acesso completo ao serviço.', 'success')
    return redirect(url_for('pdf.dashboard'))

@payment_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription_route():
    if not current_user.stripe_subscription_id:
        flash('Você não possui uma assinatura ativa.', 'warning')
        return redirect(url_for('payment.subscription'))
    
    # Cancela a assinatura no Stripe
    result = cancel_subscription(current_user.stripe_subscription_id)
    
    if result and result.status == 'canceled':
        # Atualiza o status no banco de dados
        current_user.subscription_status = 'canceled'
        db.session.commit()
        
        flash('Sua assinatura foi cancelada com sucesso.', 'success')
    else:
        flash('Erro ao cancelar assinatura. Por favor, tente novamente.', 'danger')
    
    return redirect(url_for('payment.subscription'))

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        # Payload inválido
        return jsonify({'error': str(e)}), 400
    except stripe.error.SignatureVerificationError as e:
        # Assinatura inválida
        return jsonify({'error': str(e)}), 400
    
    # Eventos de assinatura
    if event['type'] == 'customer.subscription.created' or \
       event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.customer
        
        # Encontra o usuário
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            # Atualiza as informações da assinatura
            subscription_data = handle_subscription_event(subscription)
            
            user.subscription_status = subscription_data['status']
            user.subscription_end_date = subscription_data['current_period_end']
            user.stripe_subscription_id = subscription_data['subscription_id']
            
            db.session.commit()
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.customer
        
        # Encontra o usuário
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            # Atualiza o status da assinatura
            user.subscription_status = 'canceled'
            db.session.commit()
    
    return jsonify({'status': 'success'}) 