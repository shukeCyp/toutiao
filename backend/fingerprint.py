"""
随机浏览器指纹生成器
为 Playwright 提供随机化的浏览器特征，降低被识别为自动化的风险
"""

import random

# Chrome 版本池
_CHROME_VERSIONS = [
    '120.0.0.0', '121.0.0.0', '122.0.0.0', '123.0.0.0',
    '124.0.0.0', '125.0.0.0', '126.0.0.0', '127.0.0.0',
    '128.0.0.0', '129.0.0.0', '130.0.0.0', '131.0.0.0',
    '132.0.0.0', '133.0.0.0',
]

# 操作系统 + UA 模板
_OS_UA_TEMPLATES = [
    # Windows
    ('Windows NT 10.0; Win64; x64', 'windows'),
    ('Windows NT 10.0; WOW64', 'windows'),
    ('Windows NT 11.0; Win64; x64', 'windows'),
    # macOS
    ('Macintosh; Intel Mac OS X 10_15_7', 'mac'),
    ('Macintosh; Intel Mac OS X 11_6_0', 'mac'),
    ('Macintosh; Intel Mac OS X 12_3_1', 'mac'),
    ('Macintosh; Intel Mac OS X 13_4_1', 'mac'),
    ('Macintosh; Intel Mac OS X 14_0', 'mac'),
]

# 常见屏幕分辨率
_VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1536, 'height': 864},
    {'width': 1440, 'height': 900},
    {'width': 1366, 'height': 768},
    {'width': 1280, 'height': 800},
    {'width': 1280, 'height': 720},
    {'width': 1600, 'height': 900},
    {'width': 1680, 'height': 1050},
]

# 中国城市时区（都是 Asia/Shanghai，但显示不同）
_TIMEZONES = ['Asia/Shanghai', 'Asia/Chongqing', 'Asia/Harbin', 'Asia/Urumqi']

# 语言
_LOCALES = ['zh-CN', 'zh-CN']  # 保持中文


def random_fingerprint():
    """
    生成一组随机浏览器指纹

    Returns:
        dict: {
            'user_agent': str,
            'viewport': {'width': int, 'height': int},
            'locale': str,
            'timezone_id': str,
            'color_scheme': str,
            'device_scale_factor': float,
            'extra_headers': dict,
        }
    """
    chrome_ver = random.choice(_CHROME_VERSIONS)
    os_str, os_type = random.choice(_OS_UA_TEMPLATES)
    viewport = random.choice(_VIEWPORTS)

    user_agent = (
        f'Mozilla/5.0 ({os_str}) '
        f'AppleWebKit/537.36 (KHTML, like Gecko) '
        f'Chrome/{chrome_ver} Safari/537.36'
    )

    # 随机缩放因子
    scale_factor = random.choice([1, 1, 1, 1.25, 1.5, 2])

    # 随机 Accept-Language 微调
    lang_q = round(random.uniform(0.7, 0.9), 1)
    accept_language = f'zh-CN,zh;q={lang_q},en;q=0.{random.randint(3, 5)}'

    return {
        'user_agent': user_agent,
        'viewport': viewport,
        'locale': random.choice(_LOCALES),
        'timezone_id': random.choice(_TIMEZONES),
        'color_scheme': random.choice(['light', 'dark', 'no-preference']),
        'device_scale_factor': scale_factor,
        'extra_http_headers': {
            'Accept-Language': accept_language,
        },
    }
