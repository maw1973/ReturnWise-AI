
# -*- coding: utf-8 -*-
"""
ReturnWise AI V2.5
企業退貨改善建議規則引擎

說明：
- 依既有 AI 模型分類代碼，提供改善建議
- 不修改、不重新訓練分類模型
- 建議優先程度屬規則設定，不是風險機率
- 所有措施均需由企業人員確認
"""

CATEGORY_ZH = {
    "CHANGED_MIND": "改變購買意願",
    "COLOR_STYLE_MISMATCH": "顏色／款式不符",
    "DAMAGED_IN_TRANSIT": "運送途中損壞",
    "DEFECTIVE_MALFUNCTION": "商品故障",
    "FOUND_BETTER_PRICE": "找到更優惠價格",
    "GIFT_UNWANTED": "不需要的禮物",
    "LATE_DELIVERY": "配送延遲",
    "MISSING_PARTS": "缺少零件／配件",
    "NOT_AS_DESCRIBED": "商品與描述不符",
    "ORDERED_BY_MISTAKE": "誤下訂單",
    "OTHER_UNSPECIFIED": "其他／未明確分類",
    "QUALITY_DISAPPOINTING": "商品品質不如預期",
    "SIZE_FIT": "尺寸／合身問題",
    "SUSPECTED_COUNTERFEIT": "疑似仿冒商品",
    "WRONG_ITEM_SENT": "寄送錯誤商品"
}

# priority 是預先制定的處理規則，不是模型預測機率。
RECOMMENDATIONS = {
    "SIZE_FIT": {
        "priority": "中",
        "department": "商品管理／客服",
        "root_cause_to_check": "尺寸表是否準確、版型是否有偏差",
        "actions": [
            "重新核對商品尺寸表與實際測量數值",
            "在商品頁提供版型與尺寸選擇指引",
            "彙整常見尺寸不合的商品與規格",
            "改善客服購買前尺寸諮詢"
        ],
        "kpis": [
            "尺寸問題件數",
            "同款商品尺寸相關退貨占比"
        ]
    },

    "CHANGED_MIND": {
        "priority": "低",
        "department": "行銷／客服",
        "root_cause_to_check": "購買期待是否與需求相符",
        "actions": [
            "檢查商品介紹是否清楚呈現使用情境",
            "改善購買前比較資訊",
            "分析同類商品改變心意的常見原因"
        ],
        "kpis": [
            "改變心意件數",
            "重複發生的商品比例"
        ]
    },

    "DEFECTIVE_MALFUNCTION": {
        "priority": "高",
        "department": "品質管理／供應商管理",
        "root_cause_to_check": "製造瑕疵與出貨檢查是否充分",
        "actions": [
            "檢查故障商品批次與供應商",
            "加強出貨前功能測試",
            "建立商品故障原因紀錄",
            "針對集中發生的批次啟動品質調查"
        ],
        "kpis": [
            "商品故障件數",
            "同批次故障比例"
        ]
    },

    "COLOR_STYLE_MISMATCH": {
        "priority": "中",
        "department": "商品管理／設計",
        "root_cause_to_check": "商品圖片與實際顏色或款式是否一致",
        "actions": [
            "檢查商品照片與實品的色差",
            "提供多角度與自然光商品照片",
            "確認商品規格、顏色與款式標示"
        ],
        "kpis": [
            "顏色款式不符件數",
            "商品頁資訊修正件數"
        ]
    },

    "DAMAGED_IN_TRANSIT": {
        "priority": "高",
        "department": "倉儲／物流",
        "root_cause_to_check": "包裝保護及物流搬運是否適當",
        "actions": [
            "改善易損商品的防撞包裝",
            "檢查物流商及配送路線",
            "建立包裝破損照片與紀錄",
            "針對高損壞商品測試包裝強度"
        ],
        "kpis": [
            "運送損壞件數",
            "不同物流商損壞比例"
        ]
    },

    "FOUND_BETTER_PRICE": {
        "priority": "低",
        "department": "行銷／商品定價",
        "root_cause_to_check": "商品價格是否缺乏競爭力",
        "actions": [
            "定期檢查市場價格",
            "評估促銷及優惠活動設計",
            "清楚呈現商品價值與服務差異"
        ],
        "kpis": [
            "價格因素退貨件數",
            "主要競爭商品價差"
        ]
    },

    "GIFT_UNWANTED": {
        "priority": "低",
        "department": "客服／行銷",
        "root_cause_to_check": "禮物需求與實際收件者偏好是否不符",
        "actions": [
            "檢查禮物商品的選購資訊",
            "評估符合企業政策的換貨方式",
            "改善禮物分類與用途介紹"
        ],
        "kpis": [
            "禮物相關退貨件數",
            "禮物商品換貨件數"
        ]
    },

    "LATE_DELIVERY": {
        "priority": "中",
        "department": "物流／訂單管理",
        "root_cause_to_check": "配送承諾與實際時效是否一致",
        "actions": [
            "比較承諾與實際送達時間",
            "檢查延遲集中地區及物流商",
            "改善物流異常通知",
            "檢討出貨排程"
        ],
        "kpis": [
            "配送延遲件數",
            "準時送達比例"
        ]
    },

    "MISSING_PARTS": {
        "priority": "高",
        "department": "倉儲／品管",
        "root_cause_to_check": "揀貨、包裝及出貨核對是否遺漏",
        "actions": [
            "建立商品配件檢查清單",
            "加強包裝前的完整性確認",
            "核對缺少配件的商品與作業班次"
        ],
        "kpis": [
            "缺少配件件數",
            "包裝作業缺漏件數"
        ]
    },

    "NOT_AS_DESCRIBED": {
        "priority": "高",
        "department": "商品管理／行銷",
        "root_cause_to_check": "頁面內容與實際商品是否一致",
        "actions": [
            "核對商品規格與詳細描述",
            "修正錯誤照片或誇大文字",
            "建立商品上架內容覆核流程"
        ],
        "kpis": [
            "描述不符件數",
            "商品資訊修正完成率"
        ]
    },

    "ORDERED_BY_MISTAKE": {
        "priority": "低",
        "department": "網站營運／客服",
        "root_cause_to_check": "購物車及結帳流程是否容易誤操作",
        "actions": [
            "改善購買確認頁資訊",
            "檢查商品數量與規格選擇介面",
            "提供清楚的訂單確認提示"
        ],
        "kpis": [
            "誤下單件數",
            "訂單修改或取消件數"
        ]
    },

    "OTHER_UNSPECIFIED": {
        "priority": "中",
        "department": "客服／資料管理",
        "root_cause_to_check": "退貨原因文字是否不足或分類不明",
        "actions": [
            "請客服補充具體原因",
            "檢查是否需要新增退貨原因規則",
            "由人工確認後再進行正式分類"
        ],
        "kpis": [
            "未明確分類件數",
            "人工重新分類完成率"
        ]
    },

    "QUALITY_DISAPPOINTING": {
        "priority": "高",
        "department": "品質管理／採購",
        "root_cause_to_check": "品質表現是否低於商品頁所建立的期待",
        "actions": [
            "整理商品品質相關客訴",
            "比較不同批次及供應商",
            "檢討商品材質與檢驗標準"
        ],
        "kpis": [
            "品質不如預期件數",
            "同商品重複品質客訴件數"
        ]
    },

    "SUSPECTED_COUNTERFEIT": {
        "priority": "高",
        "department": "法遵／供應鏈管理",
        "root_cause_to_check": "供應來源與商品真偽是否可驗證",
        "actions": [
            "由授權人員核對商品來源及進貨憑證",
            "保存相關訂單與商品證據",
            "依企業政策評估是否暫停爭議商品銷售",
            "必要時交由法遵人員處理"
        ],
        "kpis": [
            "疑似仿冒案件數",
            "案件人工審核完成率"
        ]
    },

    "WRONG_ITEM_SENT": {
        "priority": "高",
        "department": "倉儲／訂單管理",
        "root_cause_to_check": "揀貨與商品條碼核對是否正確",
        "actions": [
            "檢查揀貨與包裝流程",
            "強化訂單與商品條碼核對",
            "分析寄錯商品的作業環節"
        ],
        "kpis": [
            "寄錯商品件數",
            "出貨核對正確率"
        ]
    }
}


def get_recommendation(category: str) -> dict | None:
    code = category.strip().upper()

    config = RECOMMENDATIONS.get(code)

    if config is None:
        return None

    return {
        "success": True,
        "category": code,
        "category_zh": CATEGORY_ZH[code],
        "recommendation_type": "rule_based",
        "priority": config["priority"],
        "department": config["department"],
        "root_cause_to_check": config["root_cause_to_check"],
        "actions": config["actions"],
        "kpis": config["kpis"],
        "human_review_required": True,
        "notice": (
            "本建議依退貨原因分類及預設管理規則產生。"
            "優先程度不是模型預測機率，"
            "根本原因尚待實際資料或人工調查確認。"
        )
    }


if __name__ == "__main__":
    for code in CATEGORY_ZH:
        result = get_recommendation(code)
        print(code, "=>", result["category_zh"],
              "|", result["priority"])
