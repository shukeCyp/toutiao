"""
RewriteClient - 文章改写客户端
调用 OpenAI 兼容 API 改写文章标题和正文
使用 Markdown 格式交互，避免 JSON 解析问题
"""

import re
import time
import requests
from logger import get_logger

log = get_logger('rewriter')

SYSTEM_PROMPT = """你是一个有十年经验的自媒体老手，写文章就跟聊天似的，特别自然。现在需要你改写一篇文章。

【核心规则——段落数必须完全一致】
原文有 N 段，你必须返回 N 段。一段对一段，不准增加、不准删除、不准合并、不准拆分。
这是最高优先级的硬性要求，违反则视为失败。

【改写要求】
- 标题换个说法，保持原意，别改太多
- 正文逐段改写，原创度 70% 以上，意思不能跑偏
- 每一段都必须改写，不允许任何一段和原文完全一样
- 如果原文某段是非正文内容（如作品声明、作者署名、参考资料、图片说明、互动引导等），直接用一句自然的过渡句或概括句替代，不要留空、不要原样保留、不要添加任何注释说明

【风格要求】
- 像真人写的公众号文章，不能有任何AI痕迹
- 句子长短参差不齐，别整齐划一
- 每段开头别都一个套路，有时直接说事，有时来个转折、感叹、疑问
- 适当带点情绪——惊讶、吐槽、感慨、调侃都行
- 保留口语、俚语、网络梗，甚至换个更接地气的说法
- 原文中的 #话题标签 去掉标签符号，只保留文字

【绝对禁止】
- 禁止：值得注意的是、不可否认、总而言之、综上所述、毋庸置疑、显而易见
- 禁止：首先/其次/再次/最后、一方面/另一方面
- 禁止：不仅...更...、既...又...
- 禁止：每段结尾总结升华、连续多段相同句式、排比对仗、文绉绉的书面语
- 禁止：输出任何解释、说明、前言、备注、注释、总结

【返回格式】
第一行是标题（以 # 开头），后面每段用 -------- 隔开：

# 标题
--------
第1段
--------
第2段
--------
第3段

分隔符数量必须和原文一致。除此格式外不要输出任何其他内容。"""

# 遇到这些状态码时自动重试
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_MAX_REWRITE_ATTEMPTS = 3

# 敏感词等需删文的错误，不重试，由 api 层删文
SENSITIVE_PHRASE = 'Content contains sensitive words'


class SensitiveContentError(Exception):
    """LLM 返回内容包含敏感词等需删文的错误"""
    pass


class RewriteClient:
    """调用大模型 API 改写文章"""

    def __init__(self, api_base, api_key, model, timeout=120):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def rewrite(self, title, paragraphs):
        """
        改写文章标题和正文段落

        Args:
            title: 原始标题
            paragraphs: 原始正文段落列表

        Returns:
            (new_title, new_paragraphs) 元组

        Raises:
            ValueError: 改写失败（格式错误、与原文相同等）
        """
        if not paragraphs:
            raise ValueError('没有可改写的文字内容')

        # 构造用户消息：标题 + -------- 分隔的段落，并标注段落数
        user_parts = [f'# {title}']
        for p in paragraphs:
            user_parts.append(p)
        user_message = '\n--------\n'.join(user_parts)
        user_message += f'\n\n（以上共 {len(paragraphs)} 个段落，改写后必须保持 {len(paragraphs)} 个段落）'

        log.info(f'调用 LLM 改写: model={self.model}, title={title}, paragraphs={len(paragraphs)}, timeout={self.timeout}s')

        url = f'{self.api_base}/chat/completions'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_message},
            ],
            'temperature': 0.95,
        }

        for rewrite_attempt in range(_MAX_REWRITE_ATTEMPTS):
            # 带重试的 HTTP 请求
            resp = self._request_with_retry(url, headers, payload)

            data = resp.json()
            # 先检查 API 返回的 error 字段（部分厂商 200 也带 error）
            if 'error' in data:
                err = data['error']
                err_msg = err.get('message', err) if isinstance(err, dict) else str(err)
                if SENSITIVE_PHRASE in err_msg or 'sensitive' in err_msg.lower():
                    raise SensitiveContentError(err_msg)
            try:
                content = (data['choices'][0]['message']['content'] or '').strip()
            except (KeyError, TypeError):
                if 'error' in data:
                    err = data['error']
                    err_msg = err.get('message', err) if isinstance(err, dict) else str(data)
                    if SENSITIVE_PHRASE in err_msg or 'sensitive' in err_msg.lower():
                        raise SensitiveContentError(err_msg)
                raise
            # 若返回内容就是敏感词提示（整段或开头），视为需删文
            if content and (content == SENSITIVE_PHRASE or content.startswith(SENSITIVE_PHRASE)):
                raise SensitiveContentError(content)

            # 解析 Markdown 返回
            try:
                new_title, new_paragraphs = self._parse_markdown(content)
            except ValueError as e:
                log.warning(f'解析失败 (attempt {rewrite_attempt + 1}/{_MAX_REWRITE_ATTEMPTS}): {e}')
                if rewrite_attempt < _MAX_REWRITE_ATTEMPTS - 1:
                    log.info('重新请求 LLM...')
                    continue
                raise

            # 校验段落数量（误差 3 个以内可接受）
            diff = len(new_paragraphs) - len(paragraphs)
            if diff != 0:
                log.warning(f'段落数不匹配: 返回 {len(new_paragraphs)}, 期望 {len(paragraphs)}, 差值 {diff} (attempt {rewrite_attempt + 1})')
                if abs(diff) <= 3:
                    # 误差可接受：多了截断，少了保留
                    if diff > 0:
                        new_paragraphs = new_paragraphs[:len(paragraphs)]
                    log.info(f'段落数误差 {abs(diff)} 在容许范围内，继续')
                elif diff > 0:
                    new_paragraphs = new_paragraphs[:len(paragraphs)]
                elif rewrite_attempt < _MAX_REWRITE_ATTEMPTS - 1:
                    log.info('段落数差距过大，重新请求 LLM...')
                    continue
                else:
                    raise ValueError(f'段落数不匹配: 返回 {len(new_paragraphs)}, 期望 {len(paragraphs)}, 差值 {diff}')

            log.info(f'改写完成: new_title={new_title[:30]}, 段落数={len(new_paragraphs)}')
            return new_title, new_paragraphs

        raise ValueError('改写多次重试后仍然失败')

    def _request_with_retry(self, url, headers, payload):
        """带重试的 HTTP 请求"""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if not resp.ok:
                    body = (resp.text or '')[:500]
                    if SENSITIVE_PHRASE in body or ('sensitive' in body.lower() and 'word' in body.lower()):
                        raise SensitiveContentError(body or f'HTTP {resp.status_code}')
                if resp.status_code in _RETRY_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                    wait = (attempt + 1) * 5
                    log.warning(f'LLM 请求失败 (HTTP {resp.status_code})，{wait}s 后重试 ({attempt + 1}/{_MAX_RETRIES})')
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except requests.exceptions.Timeout:
                if attempt < _MAX_RETRIES - 1:
                    wait = (attempt + 1) * 5
                    log.warning(f'LLM 请求超时，{wait}s 后重试 ({attempt + 1}/{_MAX_RETRIES})')
                    time.sleep(wait)
                    continue
                raise TimeoutError(f'LLM 请求超时 ({self.timeout}s)')
            except requests.exceptions.ConnectionError:
                if attempt < _MAX_RETRIES - 1:
                    wait = (attempt + 1) * 5
                    log.warning(f'LLM 连接失败，{wait}s 后重试 ({attempt + 1}/{_MAX_RETRIES})')
                    time.sleep(wait)
                    continue
                raise

    @staticmethod
    def _parse_markdown(content):
        """
        解析改写结果，用 -------- 分隔段落

        期望格式：
            # 改写后的标题
            --------
            改写后的段落1
            --------
            改写后的段落2

        Returns:
            (title, paragraphs) 元组
        """
        # 去掉代码块包裹（以防万一）
        if '```' in content:
            content = re.sub(r'```(?:markdown)?\s*', '', content)
            content = content.strip()

        # 按 -------- 分割（逐行检测，至少 4 个连续短横线独占一行）
        # 比正则切分更可靠：不受连续分隔符、末尾无换行等边界条件影响
        _sep_re = re.compile(r'^[^\S\n]*-{4,}[^\S\n]*$')
        parts = []
        current_lines = []
        for line in content.split('\n'):
            if _sep_re.match(line):
                parts.append('\n'.join(current_lines))
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            parts.append('\n'.join(current_lines))

        if len(parts) < 2:
            raise ValueError(f'未找到 -------- 分隔符，无法解析（共 {len(parts)} 段）')

        # 第一部分包含标题
        first_part = parts[0].strip()
        title = None
        for line in first_part.split('\n'):
            stripped = line.strip()
            if stripped.startswith('# '):
                title = stripped[2:].strip()
                break
        if not title:
            # 没有 # 前缀，把第一部分整体当标题
            title = first_part.strip().lstrip('#').strip()

        if not title:
            raise ValueError('未找到标题')

        # 剩余部分是段落（保留空段落以维持段落数一致）
        paragraphs = []
        for p in parts[1:]:
            text = p.strip()
            # 清理控制字符
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            paragraphs.append(text)  # 空段落也保留，维持计数

        if not any(p for p in paragraphs):
            raise ValueError('未解析到任何段落内容')

        return title, paragraphs
