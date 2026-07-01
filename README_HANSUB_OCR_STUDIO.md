# HanSub OCR Studio

Ứng dụng desktop Python + PyQt6 dùng PaddleOCR để trích xuất phụ đề tiếng Trung từ video. Dự án được hiện thực theo tài liệu thiết kế `VIDEO_CHINESE_SUBTITLE_OCR_DESIGN.md`.

## Tính năng đã có

- Mở video và đọc metadata bằng OpenCV.
- Xem trước khung hình video kèm thanh timeline.
- Chọn vùng phụ đề ROI trực tiếp trên preview, hỗ trợ kéo, resize, hover cursor và hiển thị tọa độ.
- Nút nhanh `Chọn 25% phía dưới`, `Đặt lại vùng`, `Xem vùng cắt`.
- Cấu hình định dạng xuất `SRT`, `VTT`, `ASS`, `TXT`.
- Chọn ngôn ngữ OCR: `Tiếng Trung giản thể`, `Tiếng Trung phồn thể`, `Tiếng Trung + tiếng Anh`.
- Cấu hình bước quét khung hình, ngưỡng tin cậy, khử nhiễu, phóng to 2x, ảnh xám, tăng tương phản CLAHE, ngưỡng thích nghi và thiết bị xử lý.
- Chạy OCR nền bằng `QThread` để giao diện không bị treo.
- PaddleOCR engine với `use_angle_cls=True` khi phiên bản PaddleOCR hỗ trợ.
- Tự fallback tham số khởi tạo PaddleOCR để tương thích cả phiên bản cũ và mới.
- Gộp phụ đề lặp lại bằng fuzzy matching.
- Bảng xem trước phụ đề có sửa text bằng double-click, màu theo độ tin cậy, tìm kiếm và click dòng để nhảy tới timestamp.
- Xuất phụ đề ra file.
- Lưu/mở cấu hình dự án dạng JSON.
- Dừng và chạy tiếp tác vụ OCR.
- Tự chọn ROI bằng heuristic 25% phía dưới video.
- Giao diện sáng, tiếng Việt có dấu, có icon cho các nút chính.`r`n- Tự nhận máy có GPU CUDA/Paddle khả dụng hay không để chọn GPU hoặc fallback CPU tối ưu.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu dùng GPU, hãy cài bản `paddlepaddle-gpu` phù hợp với CUDA trên máy của bạn theo hướng dẫn PaddlePaddle.

## Chạy ứng dụng

```powershell
python -m app.main
```

## Lưu ý sử dụng

- Lần đầu chạy PaddleOCR có thể mất thời gian tải hoặc khởi tạo model.
- Nếu phụ đề nhỏ hoặc nền video phức tạp, hãy bật `Phóng to 2x`, `Tăng tương phản CLAHE` và chọn ROI sát vùng phụ đề.
- `Tự chọn vùng phụ đề` hiện dùng heuristic 25% phía dưới video; sau đó vẫn nên căn chỉnh thủ công để OCR chính xác hơn.
- Chế độ `Tự động tối ưu` sẽ dùng GPU khi PaddlePaddle phát hiện CUDA khả dụng; nếu không có GPU, ứng dụng tự chạy CPU an toàn.

## Kho mã nguồn

Dự án này được cấu hình để đẩy lên GitHub:

https://github.com/nqthaivl/PaddleOCR

