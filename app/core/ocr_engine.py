from __future__ import annotations

import os
import sys
import types
from typing import Iterable

import numpy as np

from app.core.runtime import detect_runtime


LANG_MAP = {
    "Chinese Simplified": "ch",
    "Chinese Traditional": "chinese_cht",
    "Chinese + English": "ch",
    "Tiếng Trung giản thể": "ch",
    "Tiếng Trung phồn thể": "chinese_cht",
    "Tiếng Trung + tiếng Anh": "ch",
}

PADDLE_RUNTIME_HINT = (
    "Lỗi runtime PaddleOCR/PaddlePaddle. Nếu bạn chạy CPU, hãy chọn chế độ CPU "
    "hoặc Tự động tối ưu. Có thể cài lại bản CPU ổn định bằng: "
    "pip uninstall -y paddlepaddle paddlepaddle-gpu paddleocr && "
    "pip install paddlepaddle paddleocr"
)


def _prepare_paddle_runtime(use_gpu: bool | None) -> None:
    # Các flag này cần được set trước khi import paddleocr/paddle để tránh lỗi
    # oneDNN/PIR trên một số bản PaddlePaddle CPU.
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")
    if use_gpu is False:
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


def _install_modelscope_stub() -> None:
    modelscope = types.ModuleType("modelscope")
    hub = types.ModuleType("modelscope.hub")
    errors = types.ModuleType("modelscope.hub.errors")

    class ModelScopeDisabledError(RuntimeError):
        pass

    class NotExistError(ModelScopeDisabledError):
        pass

    class HTTPError(ModelScopeDisabledError):
        pass

    def snapshot_download(*args, **kwargs):
        raise ModelScopeDisabledError(
            "ModelScope bị tắt trong ứng dụng vì dependency torch/modelscope trên máy đang lỗi."
        )

    errors.NotExistError = NotExistError
    errors.HTTPError = HTTPError
    modelscope.snapshot_download = snapshot_download
    modelscope.hub = hub
    hub.errors = errors
    sys.modules["modelscope"] = modelscope
    sys.modules["modelscope.hub"] = hub
    sys.modules["modelscope.hub.errors"] = errors


class OcrEngine:
    def __init__(self, language: str = "Tiếng Trung giản thể", use_gpu: bool | None = None):
        preferred = "auto" if use_gpu is None else "gpu" if use_gpu else "cpu"
        _prepare_paddle_runtime(use_gpu)
        probe = detect_runtime(preferred)
        resolved_use_gpu = probe.selected_device == "gpu"
        self.runtime_probe = probe
        self.selected_device = probe.selected_device

        _prepare_paddle_runtime(resolved_use_gpu)
        PaddleOCR = _import_paddleocr()

        lang = LANG_MAP.get(language, "ch")
        candidates = _build_init_candidates(lang, resolved_use_gpu)

        last_error: Exception | None = None
        for kwargs in candidates:
            try:
                self.ocr = PaddleOCR(**kwargs)
                self.init_kwargs = kwargs
                return
            except (TypeError, ValueError, NotImplementedError) as exc:
                last_error = exc
                continue

        raise RuntimeError(f"Không thể khởi tạo PaddleOCR: {last_error}\n{PADDLE_RUNTIME_HINT}")

    def recognize(self, image: np.ndarray) -> list[tuple[str, float]]:
        try:
            result = self.ocr.ocr(image, cls=True)
            return list(_flatten_paddle_result(result))
        except (TypeError, ValueError):
            result = self.ocr.ocr(image)
            return list(_flatten_paddle_result(result))
        except NotImplementedError as exc:
            try:
                result = self.ocr.predict(image)
                return list(_flatten_paddle_result(result))
            except Exception as predict_exc:
                raise RuntimeError(
                    "PaddleOCR gặp lỗi oneDNN/PIR khi nhận diện trên CPU. "
                    "Ứng dụng đã tắt MKLDNN/PIR trong code và đã thử API predict(), "
                    "nhưng môi trường Paddle hiện tại vẫn lỗi.\n"
                    f"{PADDLE_RUNTIME_HINT}\n"
                    f"Chi tiết ocr(): {exc}\nChi tiết predict(): {predict_exc}"
                ) from predict_exc


def _import_paddleocr():
    # Tránh PaddleOCR 3.x kéo ModelScope -> torch trên các máy có torch DLL lỗi.
    _purge_modules("modelscope")
    _install_modelscope_stub()
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except Exception as exc:
        raise RuntimeError(
            "Không import được PaddleOCR hoặc dependency của PaddleOCR. "
            "Hãy kiểm tra lại PaddleOCR/PaddlePaddle bằng: pip install -r requirements.txt"
        ) from exc

def _purge_modules(prefix: str) -> None:
    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            sys.modules.pop(name, None)


def _build_init_candidates(lang: str, use_gpu: bool) -> list[dict]:
    device = "gpu" if use_gpu else "cpu"
    candidates: list[dict] = []

    candidates.append(
        {
            "lang": lang,
            "device": device,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": True,
            "enable_mkldnn": False,
            "ocr_version": "PP-OCRv3",
        }
    )
    candidates.append(
        {
            "lang": lang,
            "use_angle_cls": True,
            "show_log": False,
            "use_gpu": use_gpu,
            "enable_mkldnn": False,
            "cpu_threads": 4,
            "ocr_version": "PP-OCRv3",
        }
    )
    candidates.append({"lang": lang, "use_angle_cls": True, "use_gpu": use_gpu, "enable_mkldnn": False, "ocr_version": "PP-OCRv3"})
    candidates.append({"lang": lang, "use_angle_cls": True, "enable_mkldnn": False, "ocr_version": "PP-OCRv3"})
    candidates.append({"lang": lang, "use_angle_cls": True, "ocr_version": "PP-OCRv3"})
    candidates.append({"lang": lang, "ocr_version": "PP-OCRv3"})
    return candidates


def _flatten_paddle_result(result) -> Iterable[tuple[str, float]]:
    result = _result_to_plain_data(result)
    if isinstance(result, dict):
        yield from _flatten_dict_result(result)
        return
    for block in result or []:
        block = _result_to_plain_data(block)
        if not block:
            continue
        if isinstance(block, dict):
            yield from _flatten_dict_result(block)
            continue
        if _looks_like_line(block):
            text, score = block[1]
            yield str(text), float(score)
            continue
        for item in block:
            item = _result_to_plain_data(item)
            if isinstance(item, dict):
                yield from _flatten_dict_result(item)
            elif _looks_like_line(item):
                text, score = item[1]
                yield str(text), float(score)


def _flatten_dict_result(data: dict) -> Iterable[tuple[str, float]]:
    texts = data.get("rec_texts") or data.get("texts") or data.get("text")
    scores = data.get("rec_scores") or data.get("scores") or data.get("score")
    if isinstance(texts, str):
        yield texts, float(scores if isinstance(scores, (int, float)) else 1.0)
        return
    if isinstance(texts, list):
        score_list = scores if isinstance(scores, list) else []
        for index, text in enumerate(texts):
            score = score_list[index] if index < len(score_list) else 1.0
            yield str(text), float(score)


def _result_to_plain_data(value):
    if isinstance(value, dict):
        return value
    for method_name in ("to_dict", "json"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return method()
            except TypeError:
                continue
    return value


def _looks_like_line(item) -> bool:
    return (
        isinstance(item, (list, tuple))
        and len(item) >= 2
        and isinstance(item[1], (list, tuple))
        and len(item[1]) >= 2
        and isinstance(item[1][0], (str, bytes))
    )

