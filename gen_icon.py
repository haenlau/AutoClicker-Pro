# -*- coding: utf-8 -*-
"""生成 Apple 风格应用图标：浅银玻璃圆角方块 + 石墨色鼠标 + 绿色点击波纹"""
from PIL import Image, ImageDraw, ImageFilter

S = 1024


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded_gradient(size, radius_ratio, top, bottom):
    grad = Image.new("RGB", (size, size))
    px = grad.load()
    for y in range(size):
        c = lerp(top, bottom, y / (size - 1))
        for x in range(size):
            px[x, y] = c
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    return img


def main():
    # 浅银玻璃底：上亮下微灰，顶部一层柔和白色高光
    img = rounded_gradient(S, 0.224, (250, 251, 253), (222, 226, 233))

    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.rounded_rectangle([int(S*0.05), int(S*0.03), int(S*0.95), int(S*0.5)],
                         radius=int(S*0.17), fill=(255, 255, 255, 90))
    img = Image.alpha_composite(img, hl)

    graphite = (58, 58, 62, 255)      # #3A3A3E
    green = (52, 199, 89, 255)        # iOS green

    d = ImageDraw.Draw(img)
    lw = int(S * 0.032)

    # 鼠标主体：石墨色描边胶囊
    mx0, my0 = int(S*0.36), int(S*0.30)
    mx1, my1 = int(S*0.64), int(S*0.82)
    d.rounded_rectangle([mx0, my0, mx1, my1], radius=(mx1-mx0)//2,
                        outline=graphite, width=lw)
    mid_y = (my0 + my1) // 2
    d.line([(S//2, my0 + lw), (S//2, mid_y)], fill=graphite, width=lw)
    d.line([(mx0 + lw, mid_y), (mx1 - lw, mid_y)], fill=graphite, width=lw)
    wheel_h = int(S*0.07)
    d.rounded_rectangle([S//2 - lw//2, my0 + int(S*0.07),
                         S//2 + lw//2, my0 + int(S*0.07) + wheel_h],
                        radius=lw//2, fill=graphite)

    # 点击波纹：绿色，右上方
    cx, cy = int(S*0.70), int(S*0.22)
    for rr, a in ((int(S*0.085), 255), (int(S*0.135), 130)):
        wave = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        wd = ImageDraw.Draw(wave)
        wd.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=300, end=30,
               fill=(52, 199, 89, a), width=lw)
        img = Image.alpha_composite(img, wave)
    d = ImageDraw.Draw(img)
    dot_r = int(S*0.028)
    d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=green)

    img = img.filter(ImageFilter.SMOOTH_MORE)
    out = img.resize((256, 256), Image.LANCZOS)
    out.save("icon.png")
    out.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48),
                                (32, 32), (24, 24), (16, 16)])
    print("icon.ico / icon.png 已生成 (苹果风格)")


if __name__ == "__main__":
    main()
