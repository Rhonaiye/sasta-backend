from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import Order, OrderItem, User, Cart, CartItems, Product
from database import SessionLocal
from typing import Annotated
from .users import get_current_user
import requests
from datetime import datetime, timezone
import json



router = APIRouter()


def get_db():
    db = SessionLocal()
    
    try:
        yield db
    
    finally:
         db.close()

db_dependency = Annotated[Session, Depends(get_db)]



PAYSTACK_SECRET_KEY = "sk_test_72aec27cbf426e858f1ff61b9a4611a9ed0c2797"  # Store this in environment variables
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"

# Payment status enum
class PaymentStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    

@router.post('/checkout')
async def checkout(db: db_dependency,current_user: User = Depends(get_current_user)):
    # Get user's cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='Cart not found')
    
    cart_items = db.query(CartItems).filter(CartItems.cart_id == cart.id).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cart is empty')
    
    try:
        total_price = sum(item.quantity * item.price for item in cart_items)
        
        # Create order
        order = Order(
            user_id=current_user.id,
            total_price=total_price,
            status=PaymentStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        db.add(order)
        db.flush()  # To get the order ID
        
        # Create order items
        for cart_item in cart_items:
            # Get product details
            product = db.query(Product).filter(Product.id == cart_item.product_id).first()
            if not product:
                raise HTTPException(
                     status_code=status.HTTP_404_NOT_FOUND,
                     detail=f'Product with id {cart_item.product_id} not found')
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                product_name=product.name,  # Store current product name
                quantity=cart_item.quantity,
                price=cart_item.price
            )
            db.add(order_item)
        
        # Generate a unique reference
        reference = f"order_{order.id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Initialize Paystack transaction
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}","Content-Type": "application/json"}
        
        payload = {
            "email": current_user.email,
            "amount": int(total_price * 100),  # Convert to kobo/cents
            "reference": reference,
            "callback_url": "http://localhost:3000/",  # Add your frontend callback URL
            "metadata": {
                "order_id": order.id,
                "user_id": current_user.id
            }
        }
        
        response = requests.post(PAYSTACK_INITIALIZE_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        payment_data = response.json()
        
        # Clear the cart after successful payment initialization
        db.query(CartItems).filter(CartItems.cart_id == cart.id).delete()
        db.commit()
        
        return {
            "order_id": order.id,
            "payment_url": payment_data['data']['authorization_url'],
            "reference": payment_data['data']['reference']
        }
        
    except requests.exceptions.RequestException as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        

@router.get('/verify-payment/{reference}')
async def verify_payment(
    reference: str,
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    try:
        # Extract order ID from reference
        order_id = int(reference.split('_')[1])
        
        # Get order
        order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Order not found'
            )
        
        # Verify payment with Paystack
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
        }
        
        response = requests.get(
            f"{PAYSTACK_VERIFY_URL}{reference}",
            headers=headers
        )
        response.raise_for_status()
        payment_data = response.json()
        
        if payment_data['data']['status'] == 'success':
            order.status = PaymentStatus.COMPLETED
            db.commit()
            
            return {
                "message": "Payment verified successfully",
                "order_id": order.id,
                "status": order.status
            }
        else:
            order.status = PaymentStatus.FAILED
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Payment verification failed'
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )
        
        
        

@router.get('/order/')
async def get_order( db: db_dependency):
    # Get order with all related items
    order = db.query(Order).filter(Order.user_id == 2).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Order not found'
        )
    
    return {
        "order_id": order.id,
        "total_price": order.total_price,
        "status": order.status,
        "created_at": order.created_at,
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "price": item.price,
                "total_price": item.quantity * item.price
            } for item in order.items  # Using relationship
        ]
    }




@router.get('/all-orders/')
async def get_all_user_orders(db: db_dependency, current_user: User = Depends(get_current_user)):
    # Query all orders for the given user
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()
    
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No orders found for this user'
        )
    
    return [
        {
            "order_id": order.id,
            'user_id': current_user.id,
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "total_price": item.quantity * item.price
                } for item in order.items  # Assuming a relationship exists between Order and Item models
            ]
        } for order in orders
    ]
