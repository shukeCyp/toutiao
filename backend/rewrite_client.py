"""
RewriteClient - 文章改写客户端
调用 OpenAI 兼容 API 改写文章标题和正文
"""

import json
import requests
from logger import get_logger

log = get_logger('rewriter')

SYSTEM_PROMPT = """你是一个有十年经验的自媒体老手，写文章就跟聊天似的，特别自然。现在需要你改写一篇文章，注意以下要求：

【标题】
- 保持原意，换个说法就行，别改太多

【正文改写】
- 逐段改写，原创度 70% 以上，意思不能跑偏
- 段落数量和顺序必须跟原文一模一样，一段对一段，不准增删合并

【最重要 —— 写得像人话】
- 你写出来的东西要像真人写的博客、公众号文章，不能有任何AI痕迹
- 句子长短要参差不齐，有的句子就几个字，有的可以长一些，别整齐划一
- 每段的开头别都一个套路，有时候直接说事，有时候可以先来个转折、感叹、疑问
- 适当带点情绪——惊讶、吐槽、感慨、调侃都行，别一直平铺直叙
- 原文如果有口语、俚语、网络梗，该保留就保留，甚至可以换个更接地气的说法
- 偶尔可以用一两个不那么正式的表达，比如"说白了""搁谁谁不急""这谁顶得住"之类的

【绝对禁止的AI套话和模式】
- 禁止：值得注意的是、不可否认、总而言之、综上所述、毋庸置疑、显而易见
- 禁止：首先/其次/再次/最后、一方面/另一方面 这种机械连接
- 禁止：不仅...更...、既...又... 这种工整的关联词堆叠
- 禁止：每段结尾都来一句总结性的升华
- 禁止：连续多段用相同的句式结构（比如每段都是"XXX，这XXX"的模式）
- 禁止：过度使用排比、对仗
- 禁止：把原文生动的表达改成文绉绉的书面语

请严格按照以下 JSON 格式返回，不要包含任何其他文字：
{"title": "改写后的标题", "paragraphs": ["改写段落1", "改写段落2", ...]}"""


class RewriteClient:
    """调用大模型 API 改写文章"""

    def __init__(self, api_base, api_key, model):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.model = model

    def rewrite(self, title, paragraphs):
        """
        改写文章标题和正文段落

        Args:
            title: 原始标题
            paragraphs: 原始正文段落列表

        Returns:
            (new_title, new_paragraphs) 元组
        """
        if not paragraphs:
            raise ValueError('没有可改写的文字内容')

        user_message = json.dumps({
            'title': title,
            'paragraphs': paragraphs,
        }, ensure_ascii=False)

        log.info(f'调用 LLM 改写: model={self.model}, title={title[:30]}, paragraphs={len(paragraphs)}')

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

        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()

        data = resp.json()
        content = data['choices'][0]['message']['content'].strip()

        # 尝试解析 JSON（有时 LLM 会用 ```json 包裹）
        if content.startswith('```'):
            # 去掉 markdown 代码块
            lines = content.split('\n')
            # 去掉第一行 ```json 和最后一行 ```
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines).strip()

        result = json.loads(content)
        new_title = result.get('title', title)
        new_paragraphs = result.get('paragraphs', paragraphs)

        # 校验段落数量
        if len(new_paragraphs) != len(paragraphs):
            log.warning(f'LLM 返回段落数 {len(new_paragraphs)} != 原始 {len(paragraphs)}，尝试截取/填充')
            if len(new_paragraphs) > len(paragraphs):
                new_paragraphs = new_paragraphs[:len(paragraphs)]
            else:
                # 用原文填充缺失的段落
                while len(new_paragraphs) < len(paragraphs):
                    new_paragraphs.append(paragraphs[len(new_paragraphs)])

        log.info(f'改写完成: new_title={new_title[:30]}')
        return new_title, new_paragraphs
