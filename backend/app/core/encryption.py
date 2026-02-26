from cryptography.fernet import Fernet
from app.core.config import settings
from typing import Optional
import base64
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

# 获取或生成一个用于加密的 Key
# 在生产环境中，这应该是一个独立的 Secret，从环境变量读取 ENCRYPTION_KEY
def get_cipher_suite():
    """
    生成 Fernet 加密套件
    优先使用 ENCRYPTION_KEY 环境变量，如果没有则使用 SECRET_KEY 派生
    """
    # 优先使用专用的加密密钥
    encryption_key = os.getenv("ENCRYPTION_KEY")
    
    if encryption_key:
        key_source = encryption_key.encode()
    else:
        # 使用 SHA-256 派生 32 字节密钥（避免直接截取）
        key_source = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    
    # Fernet key 必须是 32 字节的 URL-safe base64 编码
    # base64 编码 32 字节 = 44 字符（包含结尾的 =）
    fernet_key = base64.urlsafe_b64encode(key_source[:32])
    
    return Fernet(fernet_key)

def encrypt_string(text: str) -> Optional[str]:
    """加密字符串，如果输入为空则返回 None"""
    if not text:
        return None
    cipher = get_cipher_suite()
    return cipher.encrypt(text.encode()).decode()

def decrypt_string(text: str) -> Optional[str]:
    """解密字符串，如果输入为空或解密失败则返回 None"""
    if not text:
        return None
    try:
        cipher = get_cipher_suite()
        return cipher.decrypt(text.encode()).decode()
    except Exception as e:
        # 解密失败（密钥不匹配或数据损坏），返回 None
        logger.warning(f"Decryption failed: {e}")
        return None
