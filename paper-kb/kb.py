# -*- coding: utf-8 -*-
"""paper-kb 的命令列 MCP client：不用 Claude Desktop，直接透過 MCP 呼叫 server 的工具

  python kb.py tools                                   列出工具
  python kb.py search query="mouse grimace scale" k=5
  python kb.py get_document doc_id=2203.11991 pages=[5,6]
  python kb.py get_citations query=SiamFC
  python kb.py list_documents mine=true

參數格式 key=value；value 會先當 JSON 解析（數字、true、[1,2]），失敗就當字串。
"""
import os
import sys
import json
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.abspath(__file__))


NUMERIC = {'k', 'window', 'max_chars', 'limit', 'offset'}


def parse_args(items):
    """key=value。清單、true/false 和 NUMERIC 裡的參數照 JSON 解析；其他一律當字串
    （避免 doc_id=731068813e84、2203.11991 被當成數字）"""
    out = {}
    for it in items:
        k, _, v = it.partition('=')
        try:
            j = json.loads(v)
        except ValueError:
            j = v
        if isinstance(j, (int, float)) and not isinstance(j, bool) and k not in NUMERIC:
            j = v
        out[k] = j
    return out


async def main(argv):
    p = StdioServerParameters(command=sys.executable, args=['-m', 'paper_kb.server'],
                              env={**os.environ, 'PYTHONPATH': os.path.join(ROOT, 'src'), 'PAPER_KB_ROOT': ROOT})
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            if not argv or argv[0] == 'tools':
                for t in (await s.list_tools()).tools:
                    schema = getattr(t, 'input_schema', None) or getattr(t, 'inputSchema', None) or {}
                    props = schema.get('properties', {})
                    sig = ', '.join(f'{k}={v["default"]!r}' if 'default' in v else k for k, v in props.items())
                    print(f'## {t.name}({sig})\n{(t.description or "").strip()}\n')
                return 0
            res = await s.call_tool(argv[0], parse_args(argv[1:]))
            for c in res.content:
                print(getattr(c, 'text', c))
            return 1 if res.is_error else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(asyncio.run(main(sys.argv[1:])))
    except BaseException as e:   # 輸出接到 head 之類被提早關掉：安靜結束
        if 'BrokenPipe' in repr(e):
            sys.exit(0)
        raise
