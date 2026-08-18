"""网络请求与通用工具。"""

import httpx

from .config import config


class DOTA2HTTPError(Exception):
    """DOTA2 相关请求/解析失败时抛出的异常。"""


_client: httpx.AsyncClient | None = None


def prompt_error(response: httpx.Response, url: str) -> None:
    """根据 HTTP 状态码抛出友好的错误信息。"""
    if response.status_code >= 400:
        if response.status_code == 401:
            raise DOTA2HTTPError("未经授权的请求 401。请验证 API 密钥。")
        if response.status_code == 503:
            raise DOTA2HTTPError("服务器繁忙或您超出了限制。请等待 30 秒后重试。")
        raise DOTA2HTTPError(f"无法获取数据：{response.status_code}。URL：{url}")


def _proxies_kwargs() -> dict:
    """将配置中的代理转为 httpx 支持的关键字参数。

    httpx >= 0.28 已移除 Client(proxies=...)，这里针对不同版本做兼容：
    - 仅一个 http/https 代理时使用 proxy=...
    - 多个不同代理时使用 mounts=...
    """
    proxies: dict[str, str] = {}
    for key, value in (config.d2w_proxies or {}).items():
        if value:
            proxies[key if "://" in key else f"{key}://"] = value
    if not proxies:
        return {}
    if "http://" in proxies and "https://" in proxies and proxies["http://"] == proxies["https://"]:
        return {"proxy": proxies["https://"]}
    return {"mounts": {k: httpx.AsyncHTTPTransport(proxy=v) for k, v in proxies.items()}}


async def get_http_client() -> httpx.AsyncClient:
    """获取（或创建）全局复用的异步 HTTP 客户端。"""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=config.d2w_timeout,
            **_proxies_kwargs(),
        )
    return _client
