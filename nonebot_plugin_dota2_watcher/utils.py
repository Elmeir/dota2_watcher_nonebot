"""网络请求与通用工具。"""

import os
import ssl
import sys
import time
import urllib.request

import httpx

if __package__:
    from .config import config
else:
    from config import config


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


# 部分公开素材 CDN（如 cdn.cloudflare.steamstatic.com）的证书缺少 Authority Key Identifier，
# 在较新的 OpenSSL / Python 上会触发 CERTIFICATE_VERIFY_FAILED。这里为素材下载统一
# 使用不校验证书的上下文，下载内容为公开图片/数据，风险可控。
_UNVERIFIED_SSL_CONTEXT = ssl.create_default_context()
_UNVERIFIED_SSL_CONTEXT.check_hostname = False
_UNVERIFIED_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

_DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def download_bytes(url, timeout=None, headers=None, retries=1):
    """下载 url 内容为字节（不校验 SSL，用于公开素材）。最后一次失败抛出异常。"""
    req = urllib.request.Request(url, headers=headers or _DEFAULT_HEADERS)
    last_exc = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(
                req, timeout=timeout, context=_UNVERIFIED_SSL_CONTEXT
            ) as resp:
                return resp.read()
        except Exception as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(1.0)
    raise last_exc


def download_file(url, filepath, timeout=None, headers=None, quiet=False, retries=1):
    """下载 url 内容到本地文件（不校验 SSL，用于公开素材）。成功返回 True，失败返回 False。"""
    try:
        body = download_bytes(url, timeout=timeout, headers=headers, retries=retries)
    except Exception as e:
        if not quiet:
            print(f"警告: 下载 {os.path.basename(filepath)} 失败: {e}", file=sys.stderr)
        return False
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(body)
    return True
