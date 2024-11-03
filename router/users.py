from fastapi import APIRouter, Depends, HTTPException, status, Path, BackgroundTasks
from models import User, Cart, CartItems, Product, Order, Order
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from typing import Annotated
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import secrets



router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    
    finally:
        db.close()
        
db_dependency = Annotated[Session, Depends(get_db)]

class UsersReq(BaseModel):
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    address: str
    phone: str


class Loginreq(BaseModel):
    username: str
    password: str
    
class TokenData(BaseModel):
    username: str | None = None

    
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

     
SECRET_KEY = secrets.token_hex(32) 
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30

     
def create_access_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
     
     

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

async def get_current_user(db:db_dependency, token:str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username = payload.get("sub")
       
        if username is None:
           raise credentials_exception
        token_data = TokenData(username=username)
        
       
    except:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    return user
     
     
     
    
     
        
@router.get('/get-users')
async def get_user(db:db_dependency):
    users = db.query(User).all()
    
    return users


class Admin_Req(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: str
    address: str
    phone: str
    password: str
    





@router.post('/admin-signup')
async def admin_signup(db:db_dependency, user_req: Admin_Req):
    password = hash_password(user_req.password)
    
    NotUniqueUser = db.query(User).filter(User.username == user_req.username).first()
    NotUniqueEmail = db.query(User).filter(User.email == user_req.email).first()
    
    if NotUniqueUser:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= 'username already taken')
    
    if NotUniqueEmail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= 'email already taken')
    
    user_model = User(
        username = user_req.username,
        first_name = user_req.first_name,
        last_name = user_req.last_name,
        email = user_req.email,
        address = user_req.address,
        phone = user_req.phone,
        is_superuser = True,
        hashed_password = password
    )
    
    db.add(user_model)
    db.commit()
    
    return user_model
  



@router.post('/user-signup')
async def create_user(db:db_dependency, user_req: UsersReq):
    password = hash_password(user_req.password)
    
    NotUniqueUser = db.query(User).filter(User.username == user_req.username).first()
    NotUniqueEmail = db.query(User).filter(User.email == user_req.email).first()
    
    
    if NotUniqueUser:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= 'username already taken')
    
    if NotUniqueEmail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= 'email already taken')
    
    user_model = User(
        username = user_req.username,
        email = user_req.email,
        hashed_password = password,
        first_name = user_req.first_name,
        last_name = user_req.last_name,
        address = user_req.address,
        phone = user_req.phone
    )
    
    
    if user_model is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='complete all fields')
    
    db.add(user_model)
    db.commit()
    

    
    return user_model


@router.post('/user-login')
async def verify_user(db:db_dependency, login_req: Loginreq):
    user = db.query(User).filter(User.username == login_req.username).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    
    if not verify_password(login_req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Incorrect password')
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}







class addToCartReq(BaseModel):
    product_id: int



@router.post('/add-to-cart/{quantity}')
async def add_to_cart(db:db_dependency, quantity: int, addReq:addToCartReq, current_user: User = Depends(get_current_user)):
    
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication credentials')
    
    cart = db.query(Cart).filter(Cart.user_id == current_user.id ).first()
    
    if not cart:
        cart = Cart(user_id= current_user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        
    cart_item = db.query(CartItems).filter(CartItems.cart_id == cart.id, CartItems.product_id == addReq.product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    
    else:
        product = db.query(Product).filter(Product.id == addReq.product_id).first()
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='product not found')
        
        cart_item = CartItems(
            cart_id = cart.id,
            product_id = addReq.product_id,
            quantity = quantity,
            price = product.price
        )
        db.add(cart_item)
        
    db.commit()
    db.refresh(cart_item)
        
    return {"message": "Item added to cart", "cart_item": cart_item}




@router.get('/get-current-user')
async def get_user(db:db_dependency, current_user:User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='user not found')
    
    return current_user
    
    

@router.get('/get-user-cart')
async def get_user_cart(
    db: db_dependency,
    current_user: User = Depends(get_current_user)
):
    # Retrieve the user's cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Cart not found'
        )
    
    # Retrieve items in the user's cart
    cart_items = db.query(CartItems).filter(CartItems.cart_id == cart.id).all()
    
    # Prepare and return cart data
    cart_data = {
        "cart_id": cart.id,
        "user_id": cart.user_id,
        "items": [
            {
                "product_name": item.product.name,  # Access from Product model
                "cart_id": item.cart_id,
                "quantity": item.quantity,
                "product_id": item.product_id,
                "price": item.price,
                "total_price": item.quantity * item.price
            } for item in cart_items
        ],
        "total_cost": sum(item.quantity * item.price for item in cart_items)
    }
    
    return cart_data




@router.delete('/delete-cart')
async def delete_user_cart(db:db_dependency, current_user: User = Depends(get_current_user)):
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart not found")
    
    db.delete(cart)
    db.commit()
    
    
    
@router.get('/get-admin')
async def get_admin(db:db_dependency, user: User = Depends(get_current_user)):
    
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='user is not admin')
    
    admin = db.query(User).filter(User.is_superuser).all()
    
    return admin


@router.get('/get-orders')
async def get_orders(db:db_dependency):
    orders = db.query(Order).all()
    # After registering a user

    
    return orders