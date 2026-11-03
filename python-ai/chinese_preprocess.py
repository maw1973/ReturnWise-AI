
# -*- coding: utf-8 -*-
"""
ReturnWise AI V2.3
中文退貨描述前處理模組

第一階段：
1. 辨識中文輸入
2. 處理常見退貨描述
3. 偵測語意模糊情況
4. 保留原始中文
5. 不修改既有 AI 模型
"""

import re


# 已知中文退貨描述與英文表達
# 這是規則式語意轉換，不是機器翻譯模型
PHRASE_MAP = {
    "尺寸太小": "The item is too small.",
    "衣服太小": "The clothing is too small.",
    "尺寸太大": "The item is too large.",
    "衣服太大": "The clothing is too large.",
    "鞋子太緊": "The shoes are too tight.",
    "尺寸不合": "The item does not fit.",
    "不合身": "The item does not fit.",
    "收到錯誤商品": "I received the wrong item.",
    "寄錯商品": "The seller sent the wrong item.",
    "商品損壞": "The item arrived damaged.",
    "商品破損": "The item arrived broken.",
    "商品故障": "The product is malfunctioning.",
    "無法使用": "The product does not work.",
    "品質不好": "The product quality is disappointing.",
    "品質不佳": "The product quality is disappointing.",
    "與描述不符": "The item is not as described.",
    "商品與描述不符": "The product is not as described.",
    "缺少配件": "Some accessories are missing.",
    "少了零件": "Parts are missing.",
    "收到仿冒品": "The product appears counterfeit.",
    "疑似仿冒": "The item appears counterfeit.",
}

# 單靠這些文字無法判斷具體問題
AMBIGUOUS = {
    "尺寸錯誤",
    "商品有問題",
    "東西不好",
    "不能用",
    "不符合",
    "有瑕疵",
}


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def preprocess_return_text(text: str) -> dict:
    original = text.strip()

    if not original:
        return {
            "success": False,
            "status": "empty",
            "original_text": original,
            "processed_text": None,
            "needs_clarification": True,
            "message": "請輸入退貨描述",
        }

    if len(original) > 2000:
        return {
            "success": False,
            "status": "too_long",
            "original_text": original,
            "processed_text": None,
            "needs_clarification": False,
            "message": "退貨描述不得超過 2000 字元",
        }

    if not contains_chinese(original):
        return {
            "success": True,
            "status": "english",
            "original_text": original,
            "processed_text": original,
            "needs_clarification": False,
            "message": "使用原始文字進行 AI 分類",
        }

    normalized = re.sub(r"\s+", "", original)
    normalized = normalized.strip("，。！？,.!? ")

    if normalized in AMBIGUOUS:
        return {
            "success": True,
            "status": "ambiguous",
            "original_text": original,
            "processed_text": None,
            "needs_clarification": True,
            "message": "退貨描述不夠明確，請補充具體問題",
        }

    # 僅處理已知完整短句
    if normalized in PHRASE_MAP:
        return {
            "success": True,
            "status": "mapped",
            "original_text": original,
            "processed_text": PHRASE_MAP[normalized],
            "needs_clarification": False,
            "message": "已轉換為英文退貨描述",
        }

    # 未辨識的中文不直接送進英文模型
    return {
        "success": True,
        "status": "unsupported",
        "original_text": original,
        "processed_text": None,
        "needs_clarification": True,
        "message": "目前無法可靠轉換這段中文，請補充描述或使用英文",
    }


if __name__ == "__main__":
    examples = [
        "尺寸錯誤",
        "尺寸太小",
        "鞋子太緊",
        "商品損壞",
        "收到錯誤商品",
        "與描述不符",
        "The shirt is too small.",
        "這件衣服穿起來不舒服",
    ]

    for example in examples:
        result = preprocess_return_text(example)

        print("=" * 50)
        print("原始輸入：", result["original_text"])
        print("處理狀態：", result["status"])
        print("英文描述：", result["processed_text"])
        print("需要補充：", result["needs_clarification"])
        print("系統說明：", result["message"])
