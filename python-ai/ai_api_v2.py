
# -*- coding: utf-8 -*-

"""
============================================================
ReturnWise AI V2.5
智慧退貨原因分類與企業改善建議 API
============================================================

技術：
- FastAPI
- Python
- scikit-learn 已訓練模型
- V2 Linear SVM
- V2-C2 Calibrated
- 繁體中文規則式前處理
- 企業改善建議規則引擎

API：
GET  /
GET  /api/health
GET  /api/categories
POST /api/preprocess
POST /api/predict
GET  /api/recommendations/{category}

注意：
1. 保留原有雙模型，不重新訓練。
2. Decision Score 不是預測機率。
3. Decision Gap 不是預測機率。
4. 改善建議是規則式產生，不是生成式 AI。
5. AI 分類與改善措施皆需人工確認。
============================================================
"""

from pathlib import Path
from contextlib import asynccontextmanager
import logging

import joblib
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chinese_preprocess import preprocess_return_text
from return_recommendations import get_recommendation


# ============================================================
# 01. 系統設定
# ============================================================

APP_NAME = "ReturnWise AI"
APP_VERSION = "2.5.0"

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

V2_MODEL_PATH = (
    MODEL_DIR / "return_reason_model_v2.joblib"
)

C2_MODEL_PATH = (
    MODEL_DIR / "return_reason_model_v2_c2.joblib"
)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger("ReturnWiseAI")

models = {}


# ============================================================
# 02. 正式 15 種退貨原因
# ============================================================

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


def category_to_zh(category: str) -> str:
    code = str(category)
    return CATEGORY_ZH.get(code, code)


# ============================================================
# 03. 模型生命週期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info(
        "正在啟動 %s V%s",
        APP_NAME,
        APP_VERSION
    )

    if not V2_MODEL_PATH.is_file():
        raise RuntimeError(
            f"主要模型不存在：{V2_MODEL_PATH}"
        )

    if not C2_MODEL_PATH.is_file():
        raise RuntimeError(
            f"輔助模型不存在：{C2_MODEL_PATH}"
        )

    # 只讀取本機已建立且可信任的模型檔案。
    # joblib 不適合載入未知來源的檔案。

    v2 = joblib.load(V2_MODEL_PATH)
    c2 = joblib.load(C2_MODEL_PATH)

    for name, model in [
        ("V2", v2),
        ("V2-C2", c2)
    ]:

        if not hasattr(model, "predict"):
            raise RuntimeError(
                f"{name} 模型缺少 predict"
            )

        if not hasattr(model, "classes_"):
            raise RuntimeError(
                f"{name} 模型缺少 classes_"
            )

    if not hasattr(v2, "decision_function"):
        raise RuntimeError(
            "V2 模型缺少 decision_function"
        )

    v2_classes = set(
        map(str, v2.classes_)
    )

    c2_classes = set(
        map(str, c2.classes_)
    )

    if v2_classes != c2_classes:
        raise RuntimeError(
            "兩個模型的分類集合不一致"
        )

    if len(v2_classes) != 15:
        raise RuntimeError(
            "模型分類數量不是預期的 15 類"
        )

    missing = v2_classes - set(CATEGORY_ZH)

    if missing:
        raise RuntimeError(
            f"缺少中文分類：{sorted(missing)}"
        )

    models["v2"] = v2
    models["c2"] = c2

    logger.info(
        "AI 雙模型載入成功，分類數量：%d",
        len(v2_classes)
    )

    try:
        yield

    finally:
        models.clear()
        logger.info("AI 模型已釋放")


# ============================================================
# 04. FastAPI
# ============================================================

app = FastAPI(
    title=APP_NAME,
    description=(
        "退貨原因雙模型分類、中文前處理"
        "與企業改善建議 API"
    ),
    version=APP_VERSION,
    lifespan=lifespan
)


# ============================================================
# 05. CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=[
        "Content-Type",
        "Accept"
    ]
)


# ============================================================
# 06. 請求資料模型
# ============================================================

class PredictRequest(BaseModel):

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="顧客退貨原因描述"
    )


# ============================================================
# 07. 模型取得
# ============================================================

def get_models():

    v2 = models.get("v2")
    c2 = models.get("c2")

    if v2 is None or c2 is None:
        raise HTTPException(
            status_code=503,
            detail="AI 模型尚未完成載入"
        )

    return v2, c2


# ============================================================
# 08. 首頁
# ============================================================

@app.get("/")
def root():

    loaded = (
        "v2" in models and
        "c2" in models
    )

    return {
        "success": True,
        "system": APP_NAME,
        "version": APP_VERSION,
        "model_loaded": loaded,
        "primary_model": "V2 Linear SVM",
        "auxiliary_model": "V2-C2 Calibrated",
        "chinese_preprocessing": True,
        "recommendations_enabled": True,
        "database_required": False
    }


# ============================================================
# 09. 健康檢查
# ============================================================

@app.get("/api/health")
def health():

    loaded = (
        "v2" in models and
        "c2" in models
    )

    category_count = (
        len(models["v2"].classes_)
        if loaded
        else 0
    )

    return {
        "status": (
            "ok"
            if loaded
            else "not_ready"
        ),
        "model_loaded": loaded,
        "database_required": False,
        "version": APP_VERSION,
        "chinese_preprocessing": True,
        "recommendations_enabled": True,
        "category_count": category_count
    }


# ============================================================
# 10. 正式分類 API
# ============================================================

@app.get("/api/categories")
def get_categories():

    v2, _ = get_models()

    categories = sorted(
        map(str, v2.classes_)
    )

    return {
        "success": True,
        "total": len(categories),
        "data": [
            {
                "code": code,
                "name_zh": category_to_zh(code)
            }
            for code in categories
        ]
    }


# ============================================================
# 11. 中文前處理 API
# ============================================================

@app.post("/api/preprocess")
def preprocess_api(request: PredictRequest):

    result = preprocess_return_text(
        request.text.strip()
    )

    return {
        "success": result["success"],
        "preprocessing": result
    }


# ============================================================
# 12. AI 預測 API
# ============================================================

@app.post("/api/predict")
def predict_api(request: PredictRequest):

    original_text = request.text.strip()

    if not original_text:
        raise HTTPException(
            status_code=422,
            detail="請輸入退貨原因描述"
        )

    # --------------------------------------------------------
    # A. 中文前處理
    # --------------------------------------------------------

    preprocessing = preprocess_return_text(
        original_text
    )

    if not preprocessing["success"]:
        raise HTTPException(
            status_code=422,
            detail=preprocessing["message"]
        )

    # --------------------------------------------------------
    # B. 中文描述不足時不執行模型
    # --------------------------------------------------------

    if preprocessing["needs_clarification"]:

        return {
            "success": True,
            "prediction_available": False,

            "input_text": original_text,
            "model_input_text": None,

            "preprocessing": preprocessing,

            "primary_model": None,
            "auxiliary_model": None,
            "analysis": None,

            "review": {
                "required": True,
                "status": "需要補充描述",
                "reasons": [
                    preprocessing["message"]
                ]
            },

            "notice": (
                "退貨描述尚不明確，"
                "未執行 AI 分類，"
                "請補充更具體的原因。"
            )
        }

    # --------------------------------------------------------
    # C. 模型輸入
    # --------------------------------------------------------

    model_text = preprocessing["processed_text"]

    if (
        not isinstance(model_text, str)
        or not model_text.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="模型輸入文字無效"
        )

    v2, c2 = get_models()

    try:

        # ----------------------------------------------------
        # D. 雙模型預測
        # ----------------------------------------------------

        primary_category = str(
            v2.predict([model_text])[0]
        )

        auxiliary_category = str(
            c2.predict([model_text])[0]
        )

        # ----------------------------------------------------
        # E. Linear SVM 決策分數
        # ----------------------------------------------------

        scores = np.asarray(
            v2.decision_function([model_text])
        ).reshape(-1)

        classes = np.asarray(
            v2.classes_
        )

        if len(scores) != len(classes):
            raise RuntimeError(
                "決策分數與分類數量不一致"
            )

        if len(scores) < 2:
            raise RuntimeError(
                "分類數量不足"
            )

        if not np.all(np.isfinite(scores)):
            raise RuntimeError(
                "決策分數包含無效值"
            )

        sorted_indices = np.argsort(
            scores
        )[::-1]

        first_score = float(
            scores[sorted_indices[0]]
        )

        second_score = float(
            scores[sorted_indices[1]]
        )

        decision_gap = round(
            first_score - second_score,
            6
        )

        # ----------------------------------------------------
        # F. Top 3 候選分類
        # ----------------------------------------------------

        top3 = []

        for index in sorted_indices[:3]:

            category = str(classes[index])

            top3.append({
                "category": category,
                "category_zh": category_to_zh(
                    category
                ),
                "decision_score": round(
                    float(scores[index]),
                    6
                )
            })

        # ----------------------------------------------------
        # G. 雙模型一致性
        # ----------------------------------------------------

        models_agree = (
            primary_category ==
            auxiliary_category
        )

        # ----------------------------------------------------
        # H. 人工覆核
        # ----------------------------------------------------

        review_reasons = []

        if not models_agree:
            review_reasons.append(
                "主要模型與輔助模型的分類不一致"
            )

        if (
            primary_category == "SUSPECTED_COUNTERFEIT"
            or
            auxiliary_category == "SUSPECTED_COUNTERFEIT"
        ):
            review_reasons.append(
                "涉及疑似仿冒商品，建議人工確認"
            )

        # 不使用尚未經驗證的 Decision Gap 門檻
        review_required = (
            len(review_reasons) > 0
        )

        review_status = (
            "建議人工複核"
            if review_required
            else "一般處理"
        )

        # ----------------------------------------------------
        # I. 正式 AI 預測回傳
        # ----------------------------------------------------

        return {
            "success": True,
            "prediction_available": True,

            "input_text": original_text,
            "model_input_text": model_text,

            "preprocessing": preprocessing,

            "primary_model": {
                "version": "V2",
                "algorithm": "Linear SVM",
                "category": primary_category,
                "category_zh": category_to_zh(
                    primary_category
                )
            },

            "auxiliary_model": {
                "version": "V2-C2",
                "category": auxiliary_category,
                "category_zh": category_to_zh(
                    auxiliary_category
                )
            },

            "analysis": {
                "models_agree": bool(
                    models_agree
                ),
                "decision_gap": decision_gap,
                "decision_gap_is_probability": False,
                "top3_decision_scores": top3
            },

            "review": {
                "required": review_required,
                "status": review_status,
                "reasons": review_reasons
            },

            "notice": (
                "本結果為 AI 輔助分類。"
                "Decision Score 與 Decision Gap "
                "皆不是預測機率。"
                "企業應依實際退貨政策進行人工確認。"
            )
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "AI 模型預測發生錯誤"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "AI 預測失敗，"
                "請查看後端服務日誌"
            )
        ) from exc


# ============================================================
# 13. V2.5 企業改善建議 API
# ============================================================

@app.get("/api/recommendations/{category}")
def recommendations_api(category: str):

    code = category.strip().upper()

    if code not in CATEGORY_ZH:
        raise HTTPException(
            status_code=404,
            detail="找不到對應的退貨原因分類"
        )

    result = get_recommendation(code)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="尚未建立此分類的改善建議"
        )

    return result
