from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeProbe:
    has_paddle: bool
    cuda_compiled: bool
    gpu_count: int
    selected_device: str
    message: str


def detect_runtime(preferred: str = "auto") -> RuntimeProbe:
    preferred = (preferred or "auto").lower()
    try:
        import paddle
    except Exception as exc:
        return RuntimeProbe(
            has_paddle=False,
            cuda_compiled=False,
            gpu_count=0,
            selected_device="cpu",
            message=f"Chưa phát hiện PaddlePaddle, sẽ chạy CPU sau khi cài đủ thư viện. Chi tiết: {exc}",
        )

    cuda_compiled = False
    gpu_count = 0
    try:
        cuda_compiled = bool(paddle.device.is_compiled_with_cuda())
    except Exception:
        cuda_compiled = False
    if cuda_compiled:
        try:
            gpu_count = int(paddle.device.cuda.device_count())
        except Exception:
            gpu_count = 0

    gpu_ready = cuda_compiled and gpu_count > 0
    if preferred == "gpu":
        selected = "gpu" if gpu_ready else "cpu"
        message = (
            f"Đã phát hiện {gpu_count} GPU CUDA, sẽ dùng GPU."
            if gpu_ready
            else "Bạn chọn GPU nhưng PaddlePaddle hiện không có CUDA/GPU khả dụng, tự fallback CPU."
        )
    elif preferred == "cpu":
        selected = "cpu"
        message = "Đã chọn CPU thủ công."
    else:
        selected = "gpu" if gpu_ready else "cpu"
        message = (
            f"Tự động tối ưu: phát hiện {gpu_count} GPU CUDA, sẽ dùng GPU."
            if gpu_ready
            else "Tự động tối ưu: không phát hiện GPU CUDA khả dụng, sẽ dùng CPU."
        )

    return RuntimeProbe(
        has_paddle=True,
        cuda_compiled=cuda_compiled,
        gpu_count=gpu_count,
        selected_device=selected,
        message=message,
    )


def preferred_to_use_gpu(preferred: str = "auto") -> bool | None:
    preferred = (preferred or "auto").lower()
    if preferred == "gpu":
        return True
    if preferred == "cpu":
        return False
    return None
