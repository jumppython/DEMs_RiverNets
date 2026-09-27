from __future__ import annotations

import re
import unicodedata


PREFECTURES = [
    (1, "北海道", "01", "北海道"),
    (2, "青森県", "02", "東北"),
    (3, "岩手県", "03", "東北"),
    (4, "宮城県", "04", "東北"),
    (5, "秋田県", "05", "東北"),
    (6, "山形県", "06", "東北"),
    (7, "福島県", "07", "東北"),
    (8, "茨城県", "08", "関東"),
    (9, "栃木県", "09", "関東"),
    (10, "群馬県", "10", "関東"),
    (11, "埼玉県", "11", "関東"),
    (12, "千葉県", "12", "関東"),
    (13, "東京都", "13", "関東"),
    (14, "神奈川県", "14", "関東"),
    (15, "新潟県", "15", "中部"),
    (16, "富山県", "16", "中部"),
    (17, "石川県", "17", "中部"),
    (18, "福井県", "18", "中部"),
    (19, "山梨県", "19", "中部"),
    (20, "長野県", "20", "中部"),
    (21, "岐阜県", "21", "中部"),
    (22, "静岡県", "22", "中部"),
    (23, "愛知県", "23", "中部"),
    (24, "三重県", "24", "近畿"),
    (25, "滋賀県", "25", "近畿"),
    (26, "京都府", "26", "近畿"),
    (27, "大阪府", "27", "近畿"),
    (28, "兵庫県", "28", "近畿"),
    (29, "奈良県", "29", "近畿"),
    (30, "和歌山県", "30", "近畿"),
    (31, "鳥取県", "31", "中国"),
    (32, "島根県", "32", "中国"),
    (33, "岡山県", "33", "中国"),
    (34, "広島県", "34", "中国"),
    (35, "山口県", "35", "中国"),
    (36, "徳島県", "36", "四国"),
    (37, "香川県", "37", "四国"),
    (38, "愛媛県", "38", "四国"),
    (39, "高知県", "39", "四国"),
    (40, "福岡県", "40", "九州"),
    (41, "佐賀県", "41", "九州"),
    (42, "長崎県", "42", "九州"),
    (43, "熊本県", "43", "九州"),
    (44, "大分県", "44", "九州"),
    (45, "宮崎県", "45", "九州"),
    (46, "鹿児島県", "46", "九州"),
    (47, "沖縄県", "47", "沖縄"),
]


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("ヶ", "ケ").replace("ヵ", "カ")
    text = re.sub(r"\s+", "", text)
    return text.strip()


def normalize_name(value: str | None) -> str:
    text = normalize_text(value)
    for suffix in ("ダム",):
        # Keep suffix by default; this hook exists for future synonym logic.
        pass
    return text


def normalize_prefecture(value: str | None) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    for _, pref, _, _ in PREFECTURES:
        if text == pref or text == pref.replace("県", "").replace("府", "").replace("都", ""):
            return pref
    return text
