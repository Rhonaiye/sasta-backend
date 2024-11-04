from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile, Form
import shutil
import os
from fastapi.responses import JSONResponse 
from pydantic import BaseModel, Field
from models import Product, User
from typing import Annotated
from database import SessionLocal
from sqlalchemy.orm import Session
from models import Product, Category
from .users import get_current_user

from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
        
    finally:
        db.close
        
db_dependency = Annotated[Session, Depends(get_db)]


    
    
class CategoryReq(BaseModel):
    name: str
    description: str




@router.get('/get-all-products')
async def get_all_products(db:db_dependency):
    products = db.query(Product).all()

    if not products:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No products found")

    base_url = 'https://sasta-backend-1.onrender.com'  # Ensure this matches your actual backend URL

    for product in products:
        product.image_url = f"{base_url}/{product.image_url}"  # Prepend the base URL

    return products




    

@router.post('/create-product')
async def create_products(db: db_dependency,current_user : User = Depends(get_current_user) ,
                          name: str = Form(...),
                          description: str = Form(...),
                          price: float = Form(...),
                          stock: int = Form(...),
                          category_id: int = Form(...),
                          image: UploadFile = File(...)):
    
    
    if not current_user.is_active:  # Assuming 'is_admin' attribute to verify permissions
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    
    os.makedirs('images', exist_ok=True)
    
    
    image_path = f'images/{image.filename}'
    with open(image_path, 'wb') as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    product_model = Product(
        name = name,
        description  = description,
        price = price,
        stock = stock,
        category_id = category_id,
        image_url = f"images/{image.filename}"

    )
    
    if not product_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    
    db.add(product_model)
    db.commit()
    
    return JSONResponse({"message": "product created succesfully"}, status_code=status.HTTP_201_CREATED)



@router.delete('/delete-product/{id}')
async def delete_product(db:db_dependency, id: int):
    product = db.query(Product).filter(Product.id == id).first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


    db.delete(product)
    db.commit()

    return {"message": "Product deleted successfully"}






@router.get('/get-product-by-category/{id}')
async def get_product_by_category(db:db_dependency,id: int):
    product = db.query(Product).filter(Product.category_id == id).all()
    
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    
    return product
    




@router.post('/create-category')
async def create_category(db: db_dependency, category_req: CategoryReq, current_user = Depends(get_current_user)):
    category_model = Category(**category_req.model_dump())
    
    if not category_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    
    db.add(category_model)
    db.commit()
    
    return JSONResponse({"message": category_model.id}, status_code=status.HTTP_201_CREATED)


@router.get('/get-category')
async def get_all_categories(db: db_dependency):
    categories = db.query(Category).all()
    return categories
    
    