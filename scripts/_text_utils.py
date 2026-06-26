"""Shared text preprocessing for ko.javascript.info translation checks."""

import re


def strip_non_korean_content(content: str, inline_replacement: str = ' ') -> str:
    """Remove markdown/code regions that should not be inspected as prose.

    inline_replacement controls what inline-level spans (inline code, URL,
    image, HTML tag) are replaced with. Default ' ' preserves line structure
    for callers that report line numbers (e.g. check_glossary). Spell checking
    passes '\\n' so that a token boundary separates the surrounding Korean
    fragments, avoiding hanspell josa-spacing false positives.
    """
    # Fenced code blocks (백틱 3개 이상, 여는/닫는 펜스 길이 일치)
    content = re.sub(
        r'^(`{3,})[^\n]*\n[\s\S]*?^\1[ \t]*$', '\n', content, flags=re.MULTILINE
    )
    # Inline code
    content = re.sub(r'`[^`\n]+`', inline_replacement, content)
    # URLs
    content = re.sub(r'https?://\S+', inline_replacement, content)
    # Markdown images
    content = re.sub(r'!\[[^\]]*\]\([^\)]+\)', inline_replacement, content)
    # Markdown links → keep link text only
    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    # HTML tags
    content = re.sub(r'<[^>]+>', inline_replacement, content)
    # Heading markers
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
    # Bold/italic markers
    content = re.sub(r'\*{1,3}', '', content)
    content = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'\1', content)
    # YAML frontmatter
    content = re.sub(r'^---[\s\S]*?---\n', '', content)
    # Smart quotes
    content = content.replace('“', '"').replace('”', '"')
    return content
