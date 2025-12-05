"""
Модуль безопасности: хеширование паролей и шифрование API ключей
"""
from passlib.hash import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from .config import settings
import base64


# Инициализация Fernet шифровальщика
def _get_fernet() -> Fernet:
    """
    Создает Fernet шифровальщик из ENCRYPTION_KEY.
    ENCRYPTION_KEY должен быть base64-encoded 32-байтовый ключ.
    """
    try:
        # Проверяем что ключ валидный base64
        key_bytes = settings.ENCRYPTION_KEY.encode()
        return Fernet(key_bytes)
    except Exception as e:
        raise ValueError(f"Некорректный ENCRYPTION_KEY в .env файле: {str(e)}")


# ===== ХЕШИРОВАНИЕ ПАРОЛЕЙ =====

def hash_password(password: str) -> str:
    """
    Хеширует пароль через bcrypt (rounds=12 по умолчанию).
    
    Args:
        password: Пароль в открытом виде
        
    Returns:
        Bcrypt хеш в формате: $2b$12$salt22chars...hash31chars
        
    Example:
        >>> hash_password("password123")
        '$2b$12$KIXxKj.../VqZ8KYj...'
    """
    if not password:
        raise ValueError("Пароль не может быть пустым")
    
    return bcrypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие пароля хешу.
    
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Bcrypt хеш из БД
        
    Returns:
        True если пароль совпадает, False если нет
        
    Example:
        >>> verify_password("password123", "$2b$12$...")
        True
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        return bcrypt.verify(plain_password, hashed_password)
    except Exception:
        # Если хеш поврежден или некорректный формат
        return False


# ===== ШИФРОВАНИЕ API КЛЮЧЕЙ =====

def encrypt_api_key(plain_key: str) -> str:
    """
    Шифрует API ключ через Fernet (AES-128 в режиме CBC).
    
    Args:
        plain_key: API ключ в открытом виде
        
    Returns:
        Base64-encoded зашифрованная строка
        
    Raises:
        ValueError: Если ключ пустой
        
    Example:
        >>> encrypt_api_key("myApiKey12345")
        'gAAAAABl2X...'
    """
    if not plain_key:
        raise ValueError("API ключ не может быть пустым")
    
    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(plain_key.encode())
        return encrypted_bytes.decode()  # Возвращаем как строку
    except Exception as e:
        raise ValueError(f"Ошибка шифрования API ключа: {str(e)}")


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Расшифровывает API ключ.
    
    Args:
        encrypted_key: Зашифрованный ключ из БД
        
    Returns:
        Расшифрованный API ключ
        
    Raises:
        ValueError: Если ключ поврежден или ENCRYPTION_KEY изменился
        
    Example:
        >>> decrypt_api_key("gAAAAABl2X...")
        'myApiKey12345'
    """
    if not encrypted_key:
        raise ValueError("Зашифрованный ключ не может быть пустым")
    
    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted_key.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        raise ValueError(
            "Не удалось расшифровать API ключ. "
            "Ключ поврежден или ENCRYPTION_KEY изменился."
        )
    except Exception as e:
        raise ValueError(f"Ошибка расшифровки API ключа: {str(e)}")


# ===== ГЕНЕРАЦИЯ ENCRYPTION_KEY (для справки) =====

def generate_encryption_key() -> str:
    """
    Генерирует новый Fernet ключ для ENCRYPTION_KEY.
    
    ⚠️ НЕ используй в production - это только для генерации нового ключа!
    После генерации добавь в .env:
    ENCRYPTION_KEY=<результат_этой_функции>
    
    Returns:
        Base64-encoded 32-байтовый ключ
    """
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # Тестирование функций
    print("=== Тест хеширования паролей ===")
    pwd = "testpassword123"
    hashed = hash_password(pwd)
    print(f"Пароль: {pwd}")
    print(f"Хеш: {hashed}")
    print(f"Проверка (правильный): {verify_password(pwd, hashed)}")
    print(f"Проверка (неправильный): {verify_password('wrong', hashed)}")
    
    print("\n=== Тест шифрования API ключей ===")
    api_key = "mySecretApiKey123456"
    encrypted = encrypt_api_key(api_key)
    print(f"Исходный: {api_key}")
    print(f"Зашифрованный: {encrypted}")
    print(f"Расшифрованный: {decrypt_api_key(encrypted)}")
    
    print("\n=== Генерация нового ENCRYPTION_KEY ===")
    print(f"Новый ключ: {generate_encryption_key()}")
