import stripe
import os
from datetime import datetime, timedelta

# Configura a API key do Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def create_customer(name, email):
    """Cria um cliente no Stripe"""
    try:
        customer = stripe.Customer.create(
            name=name,
            email=email,
            description="Cliente do AI Reader"
        )
        return customer.id
    except Exception as e:
        print(f"Erro ao criar cliente no Stripe: {e}")
        return None

def create_checkout_session(customer_id, price_id, success_url, cancel_url):
    """Cria uma sessão de checkout para assinatura"""
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return checkout_session
    except Exception as e:
        print(f"Erro ao criar sessão de checkout: {e}")
        return None

def get_subscription(subscription_id):
    """Obtém os detalhes de uma assinatura"""
    try:
        return stripe.Subscription.retrieve(subscription_id)
    except Exception as e:
        print(f"Erro ao obter assinatura: {e}")
        return None

def cancel_subscription(subscription_id):
    """Cancela uma assinatura"""
    try:
        print(f"[Stripe Service] Iniciando cancelamento da assinatura ID: {subscription_id}")
        subscription = stripe.Subscription.retrieve(subscription_id)
        print(f"[Stripe Service] Assinatura recuperada: {subscription.id} - Status atual: {subscription.status}")
        
        # Se a assinatura já estiver cancelada, apenas retorne-a
        if subscription.status == 'canceled':
            print(f"[Stripe Service] A assinatura já está cancelada")
            return subscription
        
        # Cancela a assinatura
        canceled_subscription = stripe.Subscription.delete(subscription_id)
        print(f"[Stripe Service] Assinatura cancelada com sucesso: {canceled_subscription.id} - Novo status: {canceled_subscription.status}")
        return canceled_subscription
    except stripe.error.StripeError as e:
        # Trata erros específicos do Stripe com mais detalhes
        print(f"[Stripe Service] Erro Stripe ao cancelar assinatura: {str(e)}")
        return None
    except Exception as e:
        print(f"[Stripe Service] Erro ao cancelar assinatura: {str(e)}")
        return None

def handle_subscription_event(subscription):
    """Processa os dados de uma assinatura e retorna as informações relevantes"""
    status = subscription.status
    current_period_end = datetime.fromtimestamp(subscription.current_period_end)
    
    return {
        'status': status,
        'current_period_end': current_period_end,
        'subscription_id': subscription.id
    } 