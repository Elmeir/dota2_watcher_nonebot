"""将纯文本渲染为图片，返回 'base64://...' 字符串（供 CQ 图片消息使用）。"""

import base64
import io

from PIL import Image, ImageDraw, ImageFont

from .config import FONTS_DIR

FONT_PATH = FONTS_DIR / "SourceHanSansCN-Medium.otf"

LINE_CHAR_COUNT = 60  # 每行宽度：60 个半角字符（=30 个中文全角）
CHAR_SIZE = 32
CHAR_SIZE_H = 47
PADDING = 42
BORDER = 16


def _line_break(line: str) -> tuple[str, int]:
    """按中/英文宽度折行，返回 (折行后文本, 最大行宽)。"""
    ret = ""
    width = 0
    max_width = 0
    for c in line:
        if len(c.encode("utf8")) == 3:  # 中文全角
            if LINE_CHAR_COUNT == width + 1:  # 剩余位置不足一个汉字
                width = 2
                ret += "\n" + c
            else:
                width += 2
                ret += c
        else:
            if c == "\t":
                space = 4 - width % 4
                ret += " " * space
                width += space
            elif c == "\n":
                width = 0
                ret += c
                continue
            else:
                width += 1
                ret += c
        if width >= LINE_CHAR_COUNT:
            ret += "\n"
            width = 0
        max_width = max(max_width, width)
    if not ret.endswith("\n"):
        ret += "\n"
    return ret, max_width


def image_draw(msg: str) -> str:
    """将文本渲染为带边框的米色背景图片，返回 base64 字符串。"""
    output_str, max_width = _line_break(msg)
    font = ImageFont.truetype(str(FONT_PATH), CHAR_SIZE)
    lines = output_str.count("\n")

    img_w = max_width * CHAR_SIZE // 2 + 84
    img_h = CHAR_SIZE_H * lines + 84
    image = Image.new("RGB", (img_w, img_h), (255, 252, 245))
    draw = ImageDraw.Draw(image)
    draw.text(
        (PADDING, PADDING), output_str, fill=(125, 101, 89), font=font, spacing=CHAR_SIZE // 2
    )
    draw.rectangle(
        (BORDER, BORDER, max_width * CHAR_SIZE // 2 + 69, CHAR_SIZE_H * lines + 69),
        fill=None,
        outline=(220, 211, 196),
        width=2,
    )

    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return "base64://" + base64.b64encode(buf.getvalue()).decode()
