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

【改写要求】
- 标题保持原意，换个说法，别改太多
- 正文逐段改写，原创度 70% 以上，意思不能跑偏
- 段落数量和顺序必须跟原文一模一样，一段对一段，不准增删合并
- 每一段都必须改写，不允许任何一段和原文一样

【写得像人话】
- 像真人写的公众号文章，不能有任何AI痕迹
- 句子长短参差不齐，别整齐划一
- 每段开头别都一个套路，有时直接说事，有时来个转折、感叹、疑问
- 适当带点情绪——惊讶、吐槽、感慨、调侃都行
- 保留口语、俚语、网络梗，甚至换个更接地气的说法

【绝对禁止的AI套话】
- 禁止：值得注意的是、不可否认、总而言之、综上所述、毋庸置疑、显而易见
- 禁止：首先/其次/再次/最后、一方面/另一方面
- 禁止：不仅...更...、既...又...
- 禁止：每段结尾总结升华、连续多段相同句式、排比对仗、文绉绉的书面语

【内容清理】
- 原文中如果出现 #话题标签（如 #娱乐圈 #热搜 等），改写时必须去掉这些话题标签，不要保留
- 原文中如果出现"参考资料"、"参考文献"、"资料来源"等标记及其后面的引用内容（如《xxx》某某网 日期、媒体名称等），改写时必须整段去掉，不要保留任何参考资料内容
- 原文中如果某段只包含来源引用（如书名号包裹的文章标题+媒体名+日期、单独的媒体名称），改写时该段输出为空行即可
- 原文开头如果是作者自我介绍或打招呼的套话（如"各位老铁好久不见，我是XX，今天咱聊聊"、"大家好我是XX"、"关注我的朋友都知道"等），改写时必须去掉这类开场白，直接从正文内容开始

【返回格式——必须严格遵守，违反则视为失败】
只返回改写结果，禁止返回任何解释、说明、前言、备注、总结。
格式如下，第一行是标题（以#开头），后面每段用 -------- 隔开：

# 标题
--------
第1段
--------
第2段
--------
第3段

除了上面这个格式之外，不要输出任何其他内容。"""

# 遇到这些状态码时自动重试
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_MAX_REWRITE_ATTEMPTS = 3


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

        # 构造用户消息：标题 + -------- 分隔的段落
        user_parts = [f'# {title}']
        for p in paragraphs:
            user_parts.append(p)
        user_message = '\n--------\n'.join(user_parts)

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
            content = data['choices'][0]['message']['content'].strip()

            # 解析 Markdown 返回
            try:
                new_title, new_paragraphs = self._parse_markdown(content)
            except ValueError as e:
                log.warning(f'解析失败 (attempt {rewrite_attempt + 1}/{_MAX_REWRITE_ATTEMPTS}): {e}')
                if rewrite_attempt < _MAX_REWRITE_ATTEMPTS - 1:
                    log.info('重新请求 LLM...')
                    continue
                raise

            # 校验段落数量
            if len(new_paragraphs) != len(paragraphs):
                log.warning(f'段落数不匹配: 返回 {len(new_paragraphs)}, 期望 {len(paragraphs)} (attempt {rewrite_attempt + 1})')
                if len(new_paragraphs) > len(paragraphs):
                    new_paragraphs = new_paragraphs[:len(paragraphs)]
                elif rewrite_attempt < _MAX_REWRITE_ATTEMPTS - 1:
                    log.info('段落数不足，重新请求 LLM...')
                    continue
                else:
                    raise ValueError(f'段落数不匹配: 返回 {len(new_paragraphs)}, 期望 {len(paragraphs)}')

            log.info(f'改写完成: new_title={new_title[:30]}, 段落数={len(new_paragraphs)}')
            return new_title, new_paragraphs

        raise ValueError('改写多次重试后仍然失败')

    def _request_with_retry(self, url, headers, payload):
        """带重试的 HTTP 请求"""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
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

        # 按 -------- 分割（至少 4 个连续短横线）
        parts = re.split(r'\n\s*-{4,}\s*\n', content)

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

        # 剩余部分是段落
        paragraphs = []
        for p in parts[1:]:
            text = p.strip()
            if text:
                # 清理控制字符
                text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
                if text:
                    paragraphs.append(text)

        if not paragraphs:
            raise ValueError('未解析到任何段落内容')

        return title, paragraphs
