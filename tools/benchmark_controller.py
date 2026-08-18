import subprocess
import json
import sys
import time

def check_global_vram():
    """Sử dụng nvidia-smi để kiểm tra VRAM thực tế của toàn hệ thống (nếu có NVIDIA GPU)"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,nounits,noheader'],
            capture_output=True, text=True, check=True
        )
        return int(result.stdout.strip())
    except Exception:
        return -1

def run_isolated_benchmark(engine: str, duration: int):
    print(f"\n[{engine.upper()}] Khởi chạy Subprocess cho video {duration}s...")
    
    vram_before = check_global_vram()
    if vram_before != -1:
        print(f"  -> Hệ thống VRAM trước khi chạy: {vram_before} MB")

    # Bắt đầu gọi Subprocess
    wall_clock_start = time.time()
    
    try:
        # Gọi file worker độc lập
        process = subprocess.run(
            [sys.executable, "tools/benchmark_worker.py", "--engine", engine, "--duration", str(duration)],
            capture_output=True,
            text=True,
            check=True
        )
        
        wall_clock_time = time.time() - wall_clock_start
        data = json.loads(process.stdout.strip())
        metrics = data["metrics"]
        
        print("  -> [KẾT QUẢ TỪ SUBPROCESS]")
        print(f"     * Torch/CUDA Init : {metrics['torch_init_time_sec']}s")
        print(f"     * Model Load      : {metrics['model_load_time_sec']}s")
        print(f"     * Inference Time  : {metrics['inference_time_sec']}s")
        print(f"     * VRAM Allocated  : {metrics['peak_vram_allocated_mb']} MB (Thực dùng)")
        print(f"     * VRAM Reserved   : {metrics['peak_vram_reserved_mb']} MB (PyTorch Cache)")
        print(f"     * System RAM      : {metrics['peak_system_ram_mb']} MB")
        print(f"  -> Tổng Wall-clock   : {wall_clock_time:.2f}s (Bao gồm độ trễ OS)")
        
    except subprocess.CalledProcessError as e:
        print(f"[LỖI] Subprocess thất bại. Mã lỗi: {e.returncode}")
        print(f"Chi tiết: {e.stderr}")
    except json.JSONDecodeError:
        print("[LỖI] Không thể đọc được dữ liệu JSON từ Subprocess.")
        print(f"Raw Output: {process.stdout}")

    # Kiểm tra việc Hệ điều hành thu hồi VRAM sau khi process chết
    time.sleep(1) # Chờ OS dọn dẹp
    vram_after = check_global_vram()
    if vram_after != -1:
        print(f"  -> Hệ thống VRAM sau khi kết thúc: {vram_after} MB")
        diff = vram_after - vram_before
        if abs(diff) < 50:
            print("  => [VERIFIED] OS ĐÃ THU HỒI SẠCH VRAM (Process Isolation Hoạt Động Hoàn Hảo).")
        else:
            print(f"  => [CẢNH BÁO] VRAM chênh lệch {diff} MB. Có tiến trình khác đang dùng GPU.")

if __name__ == "__main__":
    print("="*60)
    print("BẮT ĐẦU BENCHMARK: HYBRID ARCHITECTURE (PROCESS ISOLATION)")
    print("="*60)
    
    run_isolated_benchmark("musetalk", 8)
    run_isolated_benchmark("musetalk", 15)
    run_isolated_benchmark("wav2lip", 30)