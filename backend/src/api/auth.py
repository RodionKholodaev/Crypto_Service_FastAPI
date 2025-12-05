"""
FastAPI роутер для аутентификации (регистрация, вход)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..core.security import hash_password, verify_password
from ..models.user import User
from ..schemas.auth import (
    UserRegister, 
    UserLogin, 
    UserResponse, 
    ApiResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister, 
    db: Session = Depends(get_db)
):
    """
    Регистрация нового пользователя.
    
    **Процесс:**
    1. Проверка уникальности email
    2. Хеширование пароля через bcrypt
    3. Создание записи в таблице users
    4. Возврат user_id и email
    
    **Ошибки:**
    - 409 Conflict: Email уже зарегистрирован
    - 500 Internal Server Error: Ошибка БД
    """
    try:
        # 1. Проверяем что email не занят
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            return ApiResponse(
                success=False,
                error="Email уже зарегистрирован"
            )
        
        # 2. Хешируем пароль
        hashed_password = hash_password(user_data.password)
        
        # 3. Создаем пользователя
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            name=user_data.name
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 4. Возвращаем успешный ответ
        return ApiResponse(
            success=True,
            data={
                "user_id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "message": "Регистрация успешна"
            }
        )
    
    except IntegrityError as e:
        db.rollback()
        # Обработка race condition (если между проверкой и INSERT кто-то успел создать)
        return ApiResponse(
            success=False,
            error="Email уже зарегистрирован"
        )
    
    except ValueError as e:
        # Ошибка хеширования пароля
        return ApiResponse(
            success=False,
            error=f"Ошибка обработки пароля: {str(e)}"
        )
    
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            error=f"Ошибка сервера: {str(e)}"
        )


@router.post("/login", response_model=ApiResponse)
async def login(
    credentials: UserLogin, 
    db: Session = Depends(get_db)
):
    """
    Вход в систему.
    
    **Процесс:**
    1. Поиск пользователя по email
    2. Проверка пароля через bcrypt
    3. Возврат user_id, email, name
    
    **Ошибки:**
    - 401 Unauthorized: Неверный email или пароль
    - 500 Internal Server Error: Ошибка БД
    
    **Безопасность:**
    - Одинаковое сообщение об ошибке для "пользователь не найден" и "неверный пароль"
    - Защита от username enumeration атак
    """
    try:
        # 1. Ищем пользователя по email
        user = db.query(User).filter(User.email == credentials.email).first()
        
        # 2. Проверяем существование и пароль
        if not user:
            # НЕ раскрываем что пользователь не найден
            return ApiResponse(
                success=False,
                error="Неверный email или пароль"
            )
        
        # 3. Проверяем пароль
        if not verify_password(credentials.password, user.password_hash):
            return ApiResponse(
                success=False,
                error="Неверный email или пароль"
            )
        
        # 4. Успешный вход
        return ApiResponse(
            success=True,
            data={
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "message": "Вход выполнен успешно"
            }
        )
    
    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"Ошибка сервера: {str(e)}"
        )


@router.get("/me", response_model=ApiResponse)
async def get_current_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение информации о текущем пользователе.
    
    **Примечание:** В будущем user_id будет извлекаться из JWT токена.
    Сейчас передается в Headers как X-User-ID.
    
    **Использование:**
    ```
    curl -H "X-User-ID: 1" http://localhost:8000/auth/me?user_id=1
    ```
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return ApiResponse(
                success=False,
                error="Пользователь не найден"
            )
        
        return ApiResponse(
            success=True,
            data={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat()
            }
        )
    
    except Exception as e:
        return ApiResponse(
            success=False,
            error=f"Ошибка сервера: {str(e)}"
        )
