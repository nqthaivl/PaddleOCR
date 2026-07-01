# Thiết kế ứng dụng trích xuất phụ đề tiếng Trung bằng PaddleOCR

## 1. Mục tiêu sản phẩm

Ứng dụng desktop Python + PyQt6 giúp trích xuất phụ đề tiếng Trung Quốc từ video bằng PaddleOCR. Người dùng có thể:

- Mở video từ máy tính.
- Xem trước video và chọn vùng phụ đề trực tiếp trên khung hình.
- Cấu hình ngôn ngữ OCR, tốc độ quét khung hình, ngưỡng tin cậy và các bước tiền xử lý ảnh.
- Xuất phụ đề ra `SRT`, `VTT`, `ASS` hoặc `TXT`.
- Chọn vị trí lưu file phụ đề.
- Theo dõi tiến trình, xem nhật ký, xem trước phụ đề và sửa lại nội dung trước khi xuất.

PaddleOCR phù hợp cho bài toán này vì hỗ trợ Scene OCR đa ngôn ngữ, có các model PP-OCR cho Chinese/English/Japanese và nhiều ngôn ngữ khác, đồng thời có thể chạy trên CPU hoặc GPU. Theo README PaddleOCR trên GitHub, dự án nhấn mạnh khả năng nhận diện văn bản trong cảnh thực tế, hỗ trợ nhiều ngôn ngữ và các dòng PP-OCR mới tập trung vào tốc độ cùng độ chính xác.

Nguồn tham khảo:

- https://github.com/nqthaivl/PaddleOCR
- https://github.com/nqthaivl/PaddleOCR/blob/main/README.md

## 2. Tên gợi ý

**HanSub OCR Studio**

Tên này thể hiện ứng dụng tập trung vào phụ đề tiếng Trung, nhưng vẫn đủ linh hoạt để mở rộng sang tiếng Anh, Nhật, Hàn, Việt hoặc video có nhiều ngôn ngữ.

## 3. Công nghệ cốt lõi

### 3.1. Desktop UI

- `PyQt6`: xây dựng giao diện desktop hiện đại.
- `QLabel` custom hoặc `QGraphicsView`: hiển thị frame video và cho phép kéo thả/chỉnh kích thước vùng ROI phụ đề.
- `QSlider`: timeline để nhảy tới thời điểm trong video.
- `QThread`: xử lý OCR nền, tránh treo giao diện khi video dài.
- Stylesheet `.qss`: tạo theme sáng, đồng bộ và dễ tùy biến.
- `QStyle.StandardPixmap`: thêm icon chuẩn của Qt cho các nút thao tác chính.

### 3.2. Xử lý video

- `opencv-python`: mở video, đọc metadata, lấy frame theo timestamp và crop vùng phụ đề.
- `ffmpeg` hoặc `ffmpeg-python`: có thể dùng thêm để đọc metadata/codec hoặc xử lý video dài ổn định hơn.
- `numpy`: xử lý ảnh.
- `Pillow`: hỗ trợ convert hoặc lưu ảnh debug khi cần.

### 3.3. OCR

- `paddleocr`: engine OCR chính.
- `paddlepaddle` hoặc `paddlepaddle-gpu`: runtime Paddle.
- Model gợi ý:
  - Chinese scene OCR pipeline của PaddleOCR.
  - Bật `use_angle_cls=True` nếu phiên bản PaddleOCR hỗ trợ.
  - Ưu tiên GPU nếu có CUDA, fallback CPU khi không có GPU hoặc phiên bản PaddleOCR không nhận tham số GPU.

### 3.4. Hậu xử lý phụ đề

- Gộp các kết quả OCR liên tiếp thành một subtitle segment.
- Loại nội dung trùng lặp qua nhiều frame.
- Sửa lỗi nhỏ bằng rule:
  - Chuẩn hóa khoảng trắng.
  - Loại ký tự rác do watermark hoặc noise.
  - Gộp phụ đề 2 dòng.
  - Bỏ segment có confidence thấp.
- Xuất:
  - `SRT`: phổ biến nhất.
  - `VTT`: dùng tốt cho web player.
  - `ASS`: giữ style, font và vị trí phụ đề.
  - `TXT`: đọc nhanh hoặc đưa qua công cụ dịch.

## 4. Luồng xử lý chính

1. Người dùng bấm **Mở video**.
2. Ứng dụng đọc metadata: duration, FPS, resolution, video codec.
3. Hiển thị frame đầu tiên hoặc frame tại timeline hiện tại.
4. Người dùng kéo chọn vùng phụ đề trên preview.
5. Người dùng chọn:
   - Ngôn ngữ OCR: tiếng Trung giản thể mặc định.
   - Định dạng xuất: `SRT`, `VTT`, `ASS`, `TXT`.
   - Đường dẫn lưu file.
   - Bước quét khung hình: ví dụ `0.3s`, `0.5s`, `1.0s`.
   - Ngưỡng tin cậy: ví dụ `0.65`.
6. Bấm **Bắt đầu OCR**.
7. Worker thread đọc frame theo timestamp, crop ROI, tiền xử lý ảnh và chạy PaddleOCR.
8. Kết quả OCR được đẩy về UI:
   - Thanh tiến trình.
   - Nhật ký nhận diện.
   - Bảng phụ đề tạm thời.
9. Hậu xử lý và gộp segment.
10. Người dùng xem trước, sửa tay nếu cần.
11. Bấm **Xuất phụ đề** để ghi file.

## 5. Kiến trúc module đề xuất

```text
app/
  main.py
  ui/
    main_window.py
    video_preview.py
    roi_selector.py
    subtitle_table.py
    styles.qss
  core/
    video_reader.py
    frame_sampler.py
    ocr_engine.py
    subtitle_builder.py
    subtitle_exporter.py
    preprocess.py
  workers/
    ocr_worker.py
  models/
    settings.py
    subtitle.py
  assets/
    icons/
```

### Vai trò từng module

- `video_reader.py`: mở video, đọc frame tại timestamp, trả về metadata.
- `roi_selector.py`: vùng chọn phụ đề bằng thao tác kéo, resize và hiển thị tọa độ.
- `preprocess.py`: crop ROI, grayscale, sharpen, threshold, upscale khi phụ đề nhỏ.
- `ocr_engine.py`: khởi tạo PaddleOCR một lần, nhận frame crop và trả về text + confidence.
- `subtitle_builder.py`: gộp text lặp lại thành segment có `start_time` và `end_time`.
- `subtitle_exporter.py`: ghi `SRT`, `VTT`, `ASS`, `TXT`.
- `ocr_worker.py`: xử lý nền, phát signal tiến trình và kết quả về UI.
- `styles.qss`: định nghĩa giao diện sáng, màu sắc, nút, bảng, dropdown và progress bar.

## 6. Thiết kế giao diện

### 6.1. Bố cục tổng thể

Giao diện theo phong cách desktop tool gọn, rõ, hiện đại:

```text
+--------------------------------------------------------------------------------+
| Top Bar: HanSub OCR Studio      [Mở video] [Lưu dự án] [Cài đặt] [Trợ giúp]   |
+------------------------------+-------------------------------------------------+
| Video Preview                | Thiết lập OCR                                   |
|                              | - Tệp video                                     |
|  [khung video]               | - Định dạng xuất                                |
|  [ROI phụ đề overlay]        | - Nơi lưu phụ đề                                |
|                              | - Ngôn ngữ                                      |
| Timeline + điều khiển ROI    | - Bước quét khung hình                          |
|                              | - Độ tin cậy                                    |
+------------------------------+-------------------------------------------------+
| Bảng xem trước phụ đề                                                          |
| Bắt đầu   Kết thúc   Tin cậy   Nội dung                                        |
+--------------------------------------------------------------------------------+
| Trạng thái / Thanh tiến trình       [Bắt đầu OCR] [Dừng] [Chạy tiếp] [Xuất]   |
+--------------------------------------------------------------------------------+
```

### 6.2. Thanh trên

- Logo chữ: `HanSub OCR Studio`.
- Mô tả ngắn: `Trích xuất phụ đề tiếng Trung bằng PaddleOCR`.
- Nút có icon:
  - Mở video.
  - Lưu dự án.
  - Mở dự án.
  - Cài đặt.
  - Trợ giúp.

### 6.3. Vùng video

- Nền xanh rất nhạt khi chưa mở video để tránh cảm giác đen/trắng gắt.
- Khi có video, preview hiển thị frame hiện tại theo đúng tỉ lệ.
- ROI phụ đề có viền xanh cyan, overlay nhẹ và hiển thị tọa độ `x, y, w, h`.
- Có điểm resize ở 4 góc.
- Khi hover vào ROI, con trỏ đổi theo thao tác kéo hoặc resize.
- Nút nhanh có icon:
  - `Chọn 25% phía dưới`: tự động chọn 25% dưới video.
  - `Đặt lại vùng`: chọn toàn bộ frame.
  - `Xem vùng cắt`: xem ảnh crop gốc và ảnh sau tiền xử lý.

### 6.4. Panel cấu hình

Các trường dùng control rõ ràng:

- `QLineEdit` + nút folder: đường dẫn video.
- `QComboBox`: định dạng xuất `SRT`, `VTT`, `ASS`, `TXT`.
- `QLineEdit` + nút lưu: vị trí lưu phụ đề.
- `QComboBox`: ngôn ngữ `Tiếng Trung giản thể`, `Tiếng Trung phồn thể`, `Tiếng Trung + tiếng Anh`.
- `QDoubleSpinBox`: bước quét khung hình, mặc định `0.5s`.
- `QSlider`: ngưỡng tin cậy, mặc định `65%`.
- `QCheckBox`:
  - Khử nhiễu.
  - Phóng to 2x.
  - Tự gộp dòng trùng.
  - Thiết bị xử lý: `Tự động tối ưu`, `CPU`, `GPU`.
  - Ảnh xám.
  - Tăng tương phản CLAHE.
  - Ngưỡng thích nghi.

### 6.5. Bảng xem trước phụ đề

Cột:

- `#`
- `Bắt đầu`
- `Kết thúc`
- `Tin cậy`
- `Nội dung`
- `Thao tác`

Tính năng:

- Double-click để sửa text.
- Click dòng để video nhảy đến timestamp.
- Màu xanh cho confidence tốt.
- Màu vàng cho confidence trung bình.
- Màu đỏ cho confidence thấp.
- Tìm kiếm nội dung phụ đề.

## 7. Màu sắc và style UI

### 7.1. Palette hiện tại

Phong cách: sáng, sạch, xanh dịu, phù hợp công cụ video/OCR chạy lâu.

```css
:root {
  --bg-main: #eef5ff;
  --bg-panel: #ffffff;
  --bg-video-empty: #eaf3ff;
  --border-soft: #cfe0f5;
  --border-control: #bfd1e8;
  --text-main: #172033;
  --text-muted: #607089;
  --accent: #2563eb;
  --accent-soft: #dbeafe;
  --success: #16a34a;
  --warning: #d97706;
  --danger: #be123c;
}
```

### 7.2. QSS mẫu tham khảo

```css
QMainWindow,
QDialog {
    background: #eef5ff;
    color: #172033;
    font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
    font-size: 13px;
}

QFrame#TopBar,
QFrame#SidePanel,
QFrame#BottomBar {
    background: #ffffff;
    border: 1px solid #cfe0f5;
    border-radius: 12px;
}

QPushButton {
    background: #f8fbff;
    color: #172033;
    border: 1px solid #bfd1e8;
    border-radius: 8px;
    padding: 8px 12px;
}

QPushButton#PrimaryButton {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #2563eb;
    font-weight: 700;
}

QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    background: #ffffff;
    color: #111827;
    border: 1px solid #bfd1e8;
    border-radius: 8px;
    padding: 8px 10px;
}

QComboBox QAbstractItemView {
    background: #ffffff;
    color: #111827;
    selection-background-color: #dbeafe;
    selection-color: #111827;
}

QTableWidget {
    background: #ffffff;
    alternate-background-color: #f8fbff;
    color: #111827;
    gridline-color: #e4edf8;
    border: 1px solid #cfe0f5;
    border-radius: 10px;
}

QProgressBar::chunk {
    background: #2563eb;
    border-radius: 7px;
}
```

## 8. Thuật toán gộp phụ đề

### 8.1. Vấn đề

Khi quét video mỗi `0.5s`, cùng một câu phụ đề sẽ xuất hiện trong nhiều frame. Nếu ghi mỗi frame thành một dòng thì file SRT sẽ bị lặp rất nhiều.

### 8.2. Cách giải quyết

Mỗi kết quả OCR gồm:

```python
{
    "time": 12.5,
    "text": "我一直在等你",
    "confidence": 0.91
}
```

Quy tắc gộp:

- Nếu text mới giống text trước trên `85%`, kéo dài `end_time`.
- Nếu text mới khác text trước, đóng segment cũ và tạo segment mới.
- Nếu confidence dưới ngưỡng, bỏ qua hoặc đánh dấu cần xem lại.
- Nếu mất text trong 1-2 frame ngắn, có thể giữ segment để tránh bị cắt quá sớm.

Có thể dùng:

- `difflib.SequenceMatcher` cho fuzzy match đơn giản.
- `rapidfuzz` nếu muốn nhanh và ổn định hơn.

## 9. Tiền xử lý ảnh ROI

Phụ đề video thường có viền, shadow và nền phức tạp. Pipeline nên cho bật/tắt từng bước:

1. Crop ROI theo tọa độ người dùng.
2. Resize 2x nếu phụ đề nhỏ.
3. Chuyển grayscale.
4. Tăng contrast bằng CLAHE.
5. Sharpen nhẹ.
6. Threshold/adaptive threshold tùy video.
7. Gửi ảnh đến PaddleOCR.

Ứng dụng có chế độ **Xem vùng cắt** để người dùng xem ảnh crop gốc và ảnh sau xử lý trước khi chạy OCR toàn bộ video.

## 10. Cấu hình gợi ý mặc định

```yaml
language: tieng_trung_gian_the
output_format: srt
frame_step_seconds: 0.5
confidence_threshold: 0.65
roi_mode: manual
preprocess:
  upscale: true
  denoise: false
  grayscale: true
  contrast: true
merge:
  duplicate_similarity: 0.85
  max_blank_gap_seconds: 1.0
runtime:
  use_gpu: auto
  batch_size: 1
```

## 11. Ví dụ API nội bộ

```python
from paddleocr import PaddleOCR

class OcrEngine:
    def __init__(self, use_gpu: bool = False):
        self.ocr = PaddleOCR(
            lang="ch",
            use_angle_cls=True,
            use_gpu=use_gpu,
        )

    def recognize(self, image):
        result = self.ocr.ocr(image, cls=True)
        lines = []
        for block in result or []:
            for item in block or []:
                text, score = item[1]
                lines.append((text, float(score)))
        return lines
```

Lưu ý: tùy version PaddleOCR, tham số khởi tạo có thể thay đổi. Code thực tế nên fallback khi PaddleOCR không nhận `use_gpu`, `show_log` hoặc `cls`.

## 12. Rủi ro kỹ thuật và cách giảm

- **OCR sai do phụ đề quá nhỏ**: thêm upscale 2x/3x, contrast và chọn ROI chính xác.
- **Phụ đề bị trùng lặp**: dùng fuzzy matching để gộp segment.
- **Video dài chạy chậm**: cho chọn frame step, tự nhận GPU khi khả dụng và có nút dừng/chạy tiếp.
- **Phụ đề có nền động hoặc nhiều màu**: thêm adaptive threshold và preview tiền xử lý.
- **Tiếng Trung giản thể/phồn thể**: cho chọn ngôn ngữ OCR và có thể thêm `opencc` để chuyển đổi sau OCR.
- **UI bị treo**: mọi việc OCR/video decode phải chạy trong worker thread.
- **Khác biệt phiên bản PaddleOCR**: thử nhiều cấu hình khởi tạo trước khi báo lỗi.

## 13. Roadmap phiên bản

### MVP

- Mở video.
- Chọn ROI.
- OCR theo frame step.
- Gộp phụ đề cơ bản.
- Xuất SRT/TXT.
- UI sáng bằng PyQt6 + QSS.

### V1

- Xuất VTT/ASS.
- Preview crop và preview preprocess.
- Sửa phụ đề trong bảng.
- Save/load project config.
- Stop/resume task.
- Icon cho các nút chính.

### V2

- Auto detect subtitle region thông minh hơn.
- Batch nhiều video.
- Dịch phụ đề Trung -> Việt bằng plugin riêng.
- Căn lại timing bằng scene/text disappearance detection.
- Export ASS có style font, vị trí và màu sắc.

## 14. Gợi ý package

```text
PyQt6
opencv-python
paddleocr
paddlepaddle
numpy
Pillow
rapidfuzz
opencc-python-reimplemented
ffmpeg-python
```

Nếu dùng GPU, cần cài bản PaddlePaddle phù hợp với CUDA trên máy. Nếu không có GPU hoặc Paddle không hỗ trợ CUDA, ứng dụng tự fallback CPU.

## 15. Kết luận thiết kế

Ứng dụng nên được xây như một công cụ desktop tập trung vào workflow thực tế: chọn video, khoanh vùng phụ đề, chạy OCR, xem lại và xuất file. PaddleOCR đảm nhận phần nhận diện chữ Trung; OpenCV/FFmpeg đảm nhận đọc video và crop frame; PyQt6 đảm nhận giao diện nhanh, đẹp và dễ thao tác. Thiết kế này giữ MVP gọn nhưng vẫn đủ đường mở rộng thành batch subtitle extractor hoặc công cụ dịch phụ đề sau này.

