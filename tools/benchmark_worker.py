import time
import json
import argparse
import sys
import os
import psutil

# Ghi nhận thời điểm OS vừa mới khởi tạo xong tiến trình này
process_start_time = time.time()

# 1. Đo lường Startup Overhead của việc nạp PyTorch & CUDA Context
try:
    import torch
    torch_load_time = time.time() - process_start_time
except ImportError:
    print(json.dumps({"error": "Không tìm thấy thư viện torch trong môi trường Subprocess."}))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=str, required=True)
    parser.add_argument("--duration", type=int, required=True, help="Độ dài video test (8, 15, 30)")
    args = parser.parse_args()

    # 2. Đo lường thời gian nạp Model
    model_load_start = time.time()
    
    # [Mock] Nạp Model (Giả lập việc cấp phát tài nguyên)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        # Giả lập model chiếm VRAM (~1.5GB cho MuseTalk, ~1GB cho Wav2Lip)
        vram_alloc = 1500 if args.engine == "musetalk" else 1000
        dummy_model = torch.empty((vram_alloc, 1024, 1024), dtype=torch.uint8, device="cuda")
        
    model_load_time = time.time() - model_load_start

    # 3. Đo lường thời gian Inference
    inference_start = time.time()
    
    # [Mock] Thời gian chạy tỷ lệ thuận với độ dài video
    time.sleep(args.duration * 0.4) 
    
    inference_time = time.time() - inference_start

    # 4. Thu thập các chỉ số Metrics từ PyTorch
    peak_vram_allocated = 0
    peak_vram_reserved = 0
    
    if device == "cuda":
        peak_vram_allocated = torch.cuda.max_memory_allocated() / (1024 * 1024)
        peak_vram_reserved = torch.cuda.max_memory_reserved() / (1024 * 1024)

    process = psutil.Process(os.getpid())
    peak_ram = process.memory_info().rss / (1024 * 1024)

    total_worker_time = time.time() - process_start_time

    # 5. Xuất kết quả qua Stdout dưới định dạng JSON
    result = {
        "engine": args.engine,
        "video_duration_sec": args.duration,
        "metrics": {
            "torch_init_time_sec": round(torch_load_time, 2),
            "model_load_time_sec": round(model_load_time, 2),
            "inference_time_sec": round(inference_time, 2),
            "total_worker_time_sec": round(total_worker_time, 2),
            "peak_vram_allocated_mb": round(peak_vram_allocated, 2),
            "peak_vram_reserved_mb": round(peak_vram_reserved, 2), # Chỉ số quan trọng về Fragmentation
            "peak_system_ram_mb": round(peak_ram, 2)
        }
    }
    
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()