import argparse
import gc
import os
import time
import sys

try:
    import psutil
except ImportError:
    print("Lỗi: Thiếu thư viện đo lường hệ thống. Vui lòng chạy: pip install psutil")
    sys.exit(1)

try:
    import torch
except ImportError:
    print("Cảnh báo: Không tìm thấy PyTorch. Chỉ có thể đo lường RAM, không thể đo VRAM.")
    torch = None


def print_header(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def check_assets(video_path, audio_path):
    if not os.path.exists(video_path):
        print(f"[LỖI] Không tìm thấy video: {video_path}")
        return False
    if not os.path.exists(audio_path):
        print(f"[LỖI] Không tìm thấy audio: {audio_path}")
        return False
    return True


def clear_memory():
    """Dọn dẹp RAM và VRAM rác trước khi đo lường."""
    gc.collect()
    if torch and torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


def measure_execution(task_name, func, *args, **kwargs):
    """Hàm Wrapper để bao bọc và đo lường bất kỳ tiến trình AI nào."""
    print(f"\n[ RUN ] Đang đo lường: {task_name}...")
    clear_memory()

    process = psutil.Process(os.getpid())
    base_ram = process.memory_info().rss / (1024 * 1024)

    start_time = time.time()
    success = False
    error_msg = ""

    try:
        # Thực thi hàm Engine thực tế
        func(*args, **kwargs)
        success = True
    except Exception as e:
        error_msg = str(e)

    end_time = time.time()
    exec_time = end_time - start_time

    peak_ram = (process.memory_info().rss / (1024 * 1024)) - base_ram
    peak_vram = 0.0

    if torch and torch.cuda.is_available():
        peak_vram = torch.cuda.max_memory_allocated() / (1024 * 1024)

    clear_memory() # Dọn dẹp sau khi chạy xong

    # Báo cáo kết quả
    status = "PASS" if success else "FAIL"
    print(f"[{status}] {task_name}")
    print(f" ├─ Thời gian xử lý : {exec_time:.2f} giây")
    print(f" ├─ RAM tiêu thụ    : +{peak_ram:.2f} MB")
    if torch and torch.cuda.is_available():
        print(f" ├─ VRAM Đỉnh (Peak): {peak_vram:.2f} MB")
    
    if not success:
        print(f" └─ Lỗi phát sinh   : {error_msg}")

    return success, exec_time, peak_vram


# =====================================================================
# KHU VỰC CẮM ENGINE (Sẽ được thay bằng code thật ở S4.4 và S4.5)
# =====================================================================

def mock_musetalk_fp16(video_path, audio_path):
    """Giả lập hàm chạy MuseTalk để kiểm tra khung Benchmark"""
    print("  -> [Mock] Loading MuseTalk Model (FP16)...")
    time.sleep(1)
    if torch and torch.cuda.is_available():
        # Giả lập chiếm khoảng 2.5GB VRAM
        dummy = torch.randn(10, 3, 512, 512, device='cuda', dtype=torch.float16) 
    print("  -> [Mock] Processing frames...")
    time.sleep(2)
    print("  -> [Mock] Unloading Model...")

def mock_wav2lip_fp32(video_path, audio_path):
    """Giả lập hàm chạy Wav2Lip để kiểm tra khung Benchmark"""
    print("  -> [Mock] Loading Wav2Lip Model (FP32)...")
    time.sleep(1)
    if torch and torch.cuda.is_available():
        # Giả lập chiếm khoảng 1.5GB VRAM
        dummy = torch.randn(10, 3, 256, 256, device='cuda', dtype=torch.float32)
    print("  -> [Mock] Processing frames...")
    time.sleep(1.5)
    print("  -> [Mock] Unloading Model...")


# =====================================================================
# CHƯƠNG TRÌNH CHÍNH
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Lip Sync Benchmark Gate")
    parser.add_argument("--video", type=str, default="test_8s.mp4", help="Đường dẫn file video test")
    parser.add_argument("--audio", type=str, default="test_audio.wav", help="Đường dẫn file audio test")
    args = parser.parse_args()

    print_header("BENCHMARK GATE S4.2: LIP SYNC ENGINES")
    print(f"Video Input: {args.video}")
    print(f"Audio Input: {args.audio}")

    # (Tắt tạm hàm check_assets để bạn có thể chạy test khung script ngay)
    # if not check_assets(args.video, args.audio):
    #     sys.exit(1)

    if torch and torch.cuda.is_available():
        print(f"GPU Active : {torch.cuda.get_device_name(0)}")
    else:
        print("GPU Active : KHÔNG TÌM THẤY CUDA (Chạy bằng CPU)")

    print_header("KỊCH BẢN 1: MUSETALK 1.5 (FP16)")
    measure_execution("MuseTalk_8s_Test", mock_musetalk_fp16, args.video, args.audio)

    print_header("KỊCH BẢN 2: WAV2LIP (FP32 / Tương thích)")
    measure_execution("Wav2Lip_8s_Test", mock_wav2lip_fp32, args.video, args.audio)

    print("\n[ HOÀN TẤT BENCHMARK ]")


if __name__ == "__main__":
    main()