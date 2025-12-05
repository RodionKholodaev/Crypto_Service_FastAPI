"""
Pydantic схемы для валидации запросов/ответов аутентификации
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class UserRegister(BaseModel):
    """Схема для регистрации нового пользователя"""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")
    name: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Проверка минимальной сложности пароля"""
        if len(v) < 6:
            raise ValueError("Пароль должен содержать минимум 6 символов")
        if v.isspace():
            raise ValueError("Пароль не может состоять только из пробелов")
        return v
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Проверка что имя не пустое"""
        if not v.strip():
            raise ValueError("Имя не может быть пустым")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "password123",
                    "name": "Ivan Petrov"
                }
            ]
        }
    }


class UserLogin(BaseModel):
    """Схема для входа в систему"""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "password123"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: int
    email: str
    name: str
    
    model_config = {
        "from_attributes": True,  # Pydantic v2 синтаксис (было orm_mode=True)
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "user@example.com",
                    "name": "Ivan Petrov"
                }
            ]
        }
    }


class ApiResponse(BaseModel):
    """Универсальная схема ответа API"""
    success: bool = Field(..., description="Статус операции")
    data: Optional[dict] = Field(None, description="Данные ответа при успехе")
    error: Optional[str] = Field(None, description="Сообщение об ошибке при неудаче")
    
    @field_validator('data', 'error')
    @classmethod
    def check_data_or_error(cls, v, info):
        """Проверка: если success=True, то должен быть data, иначе error"""
        # Эта проверка будет выполняться на уровне создания объекта
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "data": {"user_id": 1, "email": "user@example.com"},
                    "error": None
                },
                {
                    "success": False,
                    "data": None,
                    "error": "Email уже зарегистрирован"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """Схема ответа с токеном (для будущей JWT интеграции)"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "user": {
                        "id": 1,
                        "email": "user@example.com",
                        "name": "Ivan Petrov"
                    }
                }
            ]
        }
    }
