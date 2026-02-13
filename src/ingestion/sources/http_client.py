"""HTTP 客户端，处理 API 速率限制和重试"""
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class RateLimitedClient:
    """带速率限制处理的 HTTP 客户端"""
    
    def __init__(self, base_url: str, max_retries: int = 3):
        """
        初始化客户端
        
        Args:
            base_url: API 基础 URL
            max_retries: 最大重试次数
        """
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=30.0)
    
    def get(self, path: str, **kwargs) -> httpx.Response:
        """
        发送 GET 请求，自动处理速率限制
        
        Args:
            path: API 路径
            **kwargs: 传递给 httpx 的其他参数
            
        Returns:
            httpx.Response 对象
            
        Raises:
            httpx.HTTPStatusError: 重试失败后仍返回错误
        """
        url = f"{self.base_url}{path}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url, **kwargs)
                
                # 处理速率限制（429）
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # 指数退避：2^attempt 秒
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"API 速率限制，等待 {wait_time} 秒后重试 "
                            f"(尝试 {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"API 速率限制，已达到最大重试次数 {self.max_retries}")
                        response.raise_for_status()
                
                # 其他错误直接抛出
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"HTTP 错误 {e.response.status_code}，等待 {wait_time} 秒后重试 "
                        f"(尝试 {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP 请求失败，已达到最大重试次数: {e}")
                    raise
        
        # 理论上不会到达这里
        raise httpx.HTTPStatusError("请求失败", request=None, response=None)
    
    def close(self):
        """关闭客户端"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
