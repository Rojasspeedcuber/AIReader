from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app.models.db import db
from app.models.user import User
from app.utils.stripe_service import create_checkout_session, get_subscription, handle_subscription_event, cancel_subscription
import os
import stripe
from datetime import datetime, timedelta

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
    # Atualiza o status de assinatura do usuário no retorno do pagamento bem-sucedido
    # Isso garante acesso mesmo se o webhook não for processado imediatamente
    current_user.subscription_status = 'active'
    current_user.subscription_end_date = datetime.utcnow() + timedelta(days=30)  # 30 dias de assinatura
    db.session.commit()
    
    flash('Obrigado por assinar o AI Reader! Agora você tem acesso completo ao serviço.', 'success')
    return redirect(url_for('pdf.dashboard'))

@payment_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription_route():
    try:
        print(f"[DEBUG] Iniciando cancelamento de assinatura para usuário {current_user.email}")
        
        # Verifica se o usuário tem uma assinatura
        if not current_user.stripe_subscription_id:
            print(f"[DEBUG] Usuário {current_user.email} não tem ID de assinatura: {current_user.stripe_subscription_id}")
            flash('Você não possui uma assinatura ativa.', 'warning')
            return redirect(url_for('payment.subscription'))
        
        subscription_id = current_user.stripe_subscription_id
        print(f"[DEBUG] Tentando cancelar a assinatura ID: {subscription_id}")
        
        # Cancela a assinatura no Stripe
        result = cancel_subscription(subscription_id)
        
        if result and result.status == 'canceled':
            # Atualiza o status no banco de dados
            print(f"[DEBUG] Assinatura cancelada com sucesso: {result.id} - Status: {result.status}")
            current_user.subscription_status = 'canceled'
            db.session.commit()
            
            flash('Sua assinatura foi cancelada com sucesso.', 'success')
        else:
            error_msg = "Resultado nulo" if not result else f"Status inválido: {result.status}"
            print(f"[DEBUG] Erro no cancelamento da assinatura: {error_msg}")
            flash('Erro ao cancelar assinatura. Por favor, tente novamente.', 'danger')
        
        return redirect(url_for('payment.subscription'))
    except Exception as e:
        # Registra o erro em logs
        print(f"[ERROR] Exceção ao cancelar assinatura: {str(e)}")
        
        # Faz rollback da sessão em caso de erro
        db.session.rollback()
        
        # Informa ao usuário
        flash('Ocorreu um erro ao processar sua solicitação. Nossa equipe foi notificada.', 'danger')
        return redirect(url_for('payment.subscription'))

@payment_bp.route('/cancel-subscription-simple')
@login_required
def cancel_subscription_simple():
    try:
        print(f"[DEBUG] Iniciando cancelamento de assinatura simples para usuário {current_user.email}")
        
        # Atualiza o status no banco de dados diretamente
        # Esta é uma solução temporária para testes - em produção deveria comunicar com o Stripe
        current_user.subscription_status = 'canceled'
        db.session.commit()
        
        flash('Sua assinatura foi cancelada com sucesso.', 'success')
        return redirect(url_for('payment.subscription'))
    except Exception as e:
        print(f"[ERROR] Exceção ao cancelar assinatura (simples): {str(e)}")
        db.session.rollback()
        flash('Ocorreu um erro ao processar sua solicitação. Nossa equipe foi notificada.', 'danger')
        return redirect(url_for('payment.subscription'))

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # Adiciona log para depuração
    print("[Webhook] Recebido evento do Stripe")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
        print(f"[Webhook] Evento construído com sucesso: {event['type']}")
    except ValueError as e:
        # Payload inválido
        print(f"[Webhook] Erro de payload inválido: {e}")
        return jsonify({'error': str(e)}), 400
    except stripe.error.SignatureVerificationError as e:
        # Assinatura inválida
        print(f"[Webhook] Erro de verificação de assinatura: {e}")
        return jsonify({'error': str(e)}), 400
    
    # Eventos de assinatura
    if event['type'] == 'customer.subscription.created' or \
       event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.customer
        
        print(f"[Webhook] Evento de assinatura: {event['type']} para cliente {customer_id}")
        
        # Encontra o usuário
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            # Atualiza as informações da assinatura
            subscription_data = handle_subscription_event(subscription)
            
            user.subscription_status = subscription_data['status']
            user.subscription_end_date = subscription_data['current_period_end']
            user.stripe_subscription_id = subscription_data['subscription_id']
            
            db.session.commit()
            print(f"[Webhook] Assinatura atualizada para usuário {user.email} - Status: {user.subscription_status}")
        else:
            print(f"[Webhook] Usuário não encontrado para customer_id: {customer_id}")
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.customer
        
        print(f"[Webhook] Evento de cancelamento para cliente {customer_id}")
        
        # Encontra o usuário
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            # Atualiza o status da assinatura
            user.subscription_status = 'canceled'
            db.session.commit()
            print(f"[Webhook] Assinatura cancelada para usuário {user.email}")
        else:
            print(f"[Webhook] Usuário não encontrado para customer_id: {customer_id}")
    
    return jsonify({'status': 'success'}) 