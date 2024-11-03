from database import Base
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy import DateTime




class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)
    stock = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    
    category = relationship("Category", back_populates= 'products')
    
    
class Category(Base):
    __tablename__ = 'category'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    
    products = relationship('Product', back_populates='category')
    
    
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    address = Column(String)
    phone = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(Integer, default=datetime.now(timezone.utc))
    

class Cart(Base):
    __tablename__ = 'cart'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    items = relationship('CartItems', back_populates='cart', cascade='all, delete-orphan')
    
    
class CartItems(Base):
    __tablename__ = 'cart_items'
    
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('cart.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=1)
    price = Column(Float)
    
    cart = relationship('Cart', back_populates='items')
    product = relationship('Product')
    


class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    total_price = Column(Float)
    status = Column(String, default='pending')  # e.g., pending, completed, failed
    created_at = Column(DateTime,default=datetime.now(timezone.utc))
    
    user = relationship('User')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')



class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    product_name = Column(String)  # New field to store product name at the time of order
    quantity = Column(Integer, default=1)
    price = Column(Float)
    
    order = relationship('Order', back_populates='items')
    product = relationship('Product')

    
    
    
    
    
    

#uvicorn main:app --reload --port 4000





