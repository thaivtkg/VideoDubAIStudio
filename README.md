
# VideoDubAIStudio - Hướng dẫn Cài đặt & Triển khai

Tài liệu này cung cấp quy trình cài đặt, cấu hình và khởi chạy dự án VideoDubAIStudio. Trọng tâm của tài liệu hướng đến việc vận hành kiến trúc **Process Isolation** cho module Lip Sync (MuseTalk), nhằm đảm bảo an toàn VRAM trên các thiết bị có tài nguyên phần cứng giới hạn.

## 1. Yêu cầu hệ thống

**Phần cứng:**
*   **Baseline (Tối thiểu):** CPU AMD Ryzen 5 / Intel Core i5, RAM 16GB, GPU NVIDIA RTX 3050 (4GB VRAM).
*   **Khuyến nghị:** GPU NVIDIA RTX 4060 (8GB VRAM) hoặc cao hơn.
*   **Lưu ý thiết bị ngoại vi:** Nên sử dụng USB Sound Card hoặc cáp kết nối Type-C to 3.5mm. Tránh sử dụng cổng cắm 3.5mm Combo mặc định trên một số dòng laptop để ngăn chặn hiện tượng mất pha dải âm giọng nói (Phase Cancellation) do phần cứng bị lệch ngàm tiếp xúc vật lý.

**Phần mềm nền tảng:**
*   Hệ điều hành Windows 10/11.
*   Python 3.10 hoặc 3.11.
*   Trình quản lý gói Git.
*   Thư viện xử lý đa phương tiện FFmpeg.

---

## 2. Hướng dẫn Cài đặt (Deployment Guide)

### 2.1. Chuẩn bị Môi trường cơ sở
Mở Terminal / PowerShell và thực thi các lệnh sau:
```bash
# Clone repository của dự án
git clone <URL_REPO_CỦA_BẠN> VideoDubAIStudio
cd VideoDubAIStudio

# Khởi tạo và kích hoạt môi trường ảo (Virtual Environment)
python -m venv venv
.\venv\Scripts\activate

# Cài đặt FFmpeg (Yêu cầu khởi động lại máy/terminal sau khi cài)
winget install ffmpeg

```

### 2.2. Cài đặt Framework Lõi (PyTorch)

Dự án sử dụng chuẩn CUDA 12.1. Việc sử dụng sai phiên bản có thể dẫn đến lỗi không nhận diện GPU.

```bash
# Cài đặt PyTorch chuẩn CUDA 12.1
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

```

*(Với thư viện `mmcv`, nếu lệnh cài đặt tự động thất bại, vui lòng tải trực tiếp tệp `.whl` định dạng PyTorch 2.1.0/CUDA 12.1 và cài đặt ngoại tuyến qua pip).*

### 2.3. Tích hợp Engine MuseTalk (Vendor)

Mã nguồn engine được tách biệt khỏi codebase chính. Thực thi lệnh sau tại thư mục gốc của dự án:

```bash
git clone [https://github.com/Tencent/MuseTalk.git](https://github.com/Tencent/MuseTalk.git) vendor\MuseTalk

```

### 2.4. Cấu hình Trọng số (Model Weights)

Người dùng cần tải thủ công và sắp xếp các tệp trọng số vào đúng cấu trúc thư mục sau tại `vendor/MuseTalk/models/` để hệ thống inference có thể hoạt động:

```text
vendor/MuseTalk/models/
├── dwpose/
│   ├── dw-ll_ucoco_384.pth
│   └── yolox_l_8x8_300e_coco.pth
├── face-parse-bisent/
│   ├── 79999_iter.pth
│   └── resnet18-5c106cde.pth
├── musetalk/
│   └── musetalk.json
│   └── pytorch_model.bin
├── sd-vae-ft-mse/
│   ├── config.json
│   └── diffusion_pytorch_model.bin
└── whisper/
    └── tiny.pt

```

---

## 3. Cấu hình & Khởi chạy theo Phần cứng

Hệ thống hoạt động theo cơ chế **Isolated Worker**. Process chính (GUI) hoàn toàn không lưu trữ mô hình AI. Các lệnh gọi được chuyển thẳng xuống tiến trình ngầm (Subprocess) và tự động dọn dẹp bộ nhớ (Cleanup) sau khi hoàn tất.

### 3.1. Cấu hình Low-VRAM (RTX 3050 - 4GB)

Cấu hình phòng thủ bắt buộc để ngăn chặn tràn bộ nhớ (`CUDA Out of Memory`).

* **Chế độ FP16 (`--fp16`):** Giảm phân nửa độ lớn VRAM cấp phát.
* **Batch Size (`--batch_size 1`):** Xử lý đơn khung hình.
* **Device (`--device cuda`)**

**Cú pháp thực thi CLI Worker:**

```bash
python ai/lipsync/workers/musetalk_worker.py --video input.mp4 --audio voice.wav --face_json cache.json --output final.mp4 --device cuda --batch_size 1 --fp16

```

### 3.2. Cấu hình High-VRAM (RTX 4060 - 8GB trở lên)

Tối đa hóa tốc độ xử lý (FPS) bằng cách gia tăng Batch Size.

* **Chế độ FP16 (`--fp16`):** Bật để tăng tốc hoặc Tắt để giữ nguyên độ chính xác FP32.
* **Batch Size (`--batch_size 4` hoặc `8`):** Xử lý đa khung hình.

**Cú pháp thực thi CLI Worker:**

```bash
python ai/lipsync/workers/musetalk_worker.py --video input.mp4 --audio voice.wav --face_json cache.json --output final.mp4 --device cuda --batch_size 4 --fp16

```

### 3.3. Cấu hình CPU Fallback (Hệ thống không có GPU)

Nếu tham số `--device auto` không tìm thấy CUDA, hoặc người dùng truyền cứng `--device cpu`, hệ thống sẽ chặn kết nối GPU (tiêm biến `CUDA_VISIBLE_DEVICES = "-1"`) và tính toán bằng vi xử lý trung tâm. Thời gian thực thi sẽ gia tăng.

---

## 4. Công cụ Benchmark (Kiểm định Hệ thống)

Cung cấp công cụ đo lường mức độ chiếm dụng VRAM vật lý trong thời gian thực bằng `nvidia-smi`, mô phỏng chính xác điều kiện chạy Model thực tế. Được sử dụng để đánh giá năng lực phần cứng trước khi chốt tham số render cấu hình cao.

**Khởi chạy bài test 8 giây ở chuẩn FP16:**

```bash
python tools/benchmark_worker.py --engine musetalk --duration 8 --fp16

```

Kết quả trả về định dạng JSON, bao gồm: `execution_time_sec`, `peak_vram_allocated_mb` (Mức gia tăng VRAM tối đa), và chỉ báo trạng thái (OOM/Crash).

---

## 5. Khắc phục sự cố (Troubleshooting)

| Dấu hiệu | Nguyên nhân cốt lõi | Giải pháp |
| --- | --- | --- |
| **Crash Worker (Return Code != 0), thiếu file output MP4** | Lỗi định dạng mã hóa Unicode trong dữ liệu metadata (tên file tiếng Việt, ký tự tiếng Nhật) | Hệ thống Worker đã được thiết lập biến môi trường ép chạy chuẩn `UTF-8`. Đảm bảo file cấu hình không chứa ký hiệu bất hợp lệ. |
| **CUDA Out of Memory (OOM)** | Các tiến trình HĐH (Trình duyệt, DWM, OBS) chiếm dụng VRAM khả dụng (hiện tượng thường thấy ở GPU 4GB) | Dọn dẹp ứng dụng chạy ngầm trước khi render. Bắt buộc kích hoạt cờ `--fp16` và `--batch_size 1`. |
| **Lỗi Face Metadata không đồng bộ** | Hệ thống MuseTalk gốc tự kích hoạt logic nhận diện khuôn mặt làm tràn VRAM do không đọc Cache JSON | Đảm bảo file `face_json` chuẩn định dạng. Quá trình Worker đã bypass logic gốc và truyền trực tiếp bounding_box tọa độ. |

## 6. Kiến trúc Xử lý đa luồng (Non-blocking GUI)

VideoDubAIStudio sử dụng kiến trúc phân tách luồng nghiêm ngặt để đảm bảo trải nghiệm người dùng (UX) không bị gián đoạn khi xử lý các tác vụ AI nặng:

*   **Main Process (UI Thread):** Chỉ chịu trách nhiệm tiếp nhận sự kiện (click, kéo thả) và hiển thị tiến độ. Tuyệt đối KHÔNG import `torch` hoặc khởi tạo Model AI tại luồng này để tránh rò rỉ bộ nhớ.
*   **QThread Worker (`LipSyncQWorker`):** Luồng trung gian làm nhiệm vụ gọi và giám sát subprocess.
*   **Subprocess Worker (`musetalk_worker.py`):** Tiến trình độc lập tương tác trực tiếp với GPU. Khi tiến trình này hoàn tất hoặc bị hủy, hệ điều hành (OS) sẽ tự động thu hồi 100% VRAM (Hard CUDA Process Boundary).

## 7. Quản lý Dữ liệu Khuôn mặt (Face Cache Management)

Dự án áp dụng cơ chế Face Caching nhằm giảm thiểu tối đa VRAM khi chạy Lip Sync.
*   **Schema Versioning:** Cache được định cấu trúc JSON theo `schema_version`, cho phép hệ thống nhận biết các tệp cache lỗi thời (ví dụ khi thay đổi thư viện Face Detector) để tự động tái tạo.
*   **Hold-Last-Box Algorithm:** Xử lý triệt để bài toán Face Loss (nhân vật quay mặt, bị che khuất) bằng cách nội suy / níu giữ tọa độ (bounding box) của khung hình hợp lệ gần nhất. Ngăn chặn triệt để tình trạng MuseTalk Worker bị sập ngang do khuyết dữ liệu đầu vào.

**Luồng dữ liệu giao tiếp:**
`GUI Button Click` ➔ `LipSyncQWorker.start()` ➔ `Subprocess.run()` ➔ `Emit Signals (Progress/Error)` ➔ `GUI Update`
## 8. Kết quả Kiểm định Phần cứng (Gate S4.2 Benchmark)

Hệ thống đã trải qua quá trình kiểm định thực tế khắt khe bằng công cụ Benchmark nội bộ để đo lường khả năng chịu tải của VRAM khi vận hành MuseTalk 1.5. Công cụ giám sát trực tiếp `nvidia-smi` để bóc tách Baseline VRAM của OS và VRAM thực tế do tiến trình AI chiếm dụng.

**Ma trận Kiểm định (Test Matrix) trên GPU NVIDIA RTX 4060 (8GB VRAM):**
*   **Video 8 giây:** 🟢 PASS (Peak VRAM allocated: ~6.8GB | System Peak: ~7.9GB | Output Valid)
*   **Video 15 giây:** 🟢 PASS (Peak VRAM allocated: ~7.0GB | System Peak: ~7.8GB | Output Valid)
*   **Video 30 giây:** 🔴 FAIL (Tiến trình sập ở giây 44 do giới hạn phân mảnh bộ nhớ không gian (Spatial Tensor Fragmentation). Output không hợp lệ).

**Khuyến cáo cho cấu hình Low-VRAM (NVIDIA RTX 3050 - 4GB):**
*   **Trạng thái:** ⚠️ [Chưa xác minh thực tế - Nguy cơ OOM cực cao]
*   Dựa trên lượng Delta VRAM đo được từ RTX 4060, cấu hình 4GB không đủ không gian vật lý để chứa mô hình MuseTalk 1.5 cùng lúc với bộ nhớ đệm video. Dự kiến áp dụng cơ chế cắt nhỏ luồng video (Chunking) hoặc Fallback tự động sang Wav2Lip cho các thiết bị này ở phiên bản tới.

---

## 9. Quản lý Vòng đời & Ngăn chặn Zombie Process (Process Lifecycle)

Để đảm bảo hệ thống không rò rỉ tài nguyên khi xảy ra sự cố gián đoạn (User Cancel hoặc GUI Crash):
*   Áp dụng cơ chế **Process Tree Kill** (`taskkill /F /T /PID` trên Windows).
*   Khi Parent Process bị ngắt, tín hiệu sẽ tiêu diệt toàn bộ gia phả tiến trình bên dưới. Bất kể luồng CUDA của mô hình đang kẹt ở trạng thái nào, hệ điều hành (OS) sẽ can thiệp và thu hồi 100% VRAM (Hard Cleanup) ngay lập tức.

---

## 10. Tối ưu thuật toán Face Cache (Anti-Stale Tracking)

Xử lý triệt để các rủi ro liên quan đến mất dấu khuôn mặt (Face Loss) bằng hai cơ chế bảo vệ kép:
1.  **Ngưỡng níu giữ (Hold-Last-Box Limit):** Giới hạn thời gian bảo lưu tọa độ khuôn mặt cũ tối đa 15 frames (~0.5 giây). Nếu nhân vật hoàn toàn rời khỏi khung hình (Camera cut), hệ thống ngắt Box cũ để tránh hiện tượng render "bóng ma" (Stale Face Tracking).
2.  **Kìm kẹp tọa độ (Box Clamping):** Áp dụng thuật toán giới hạn tọa độ Bounding Box, triệt tiêu hoàn toàn rủi ro tọa độ âm ($x < 0, y < 0$) hoặc tràn viền màn hình khiến các bộ giải mã CV2/FFmpeg bị lỗi biên dịch.


```

```
