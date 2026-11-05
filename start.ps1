# DTAMarkdown Studio - 1-Click Startup Script
# Tác giả: Đinh Thiên Ân <dthienan762@gmail.com>

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " DTAMarkdown Studio - Starting Application" -ForegroundColor Green
Write-Host " Tác giả: Đinh Thiên Ân (dthienan762@gmail.com)" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Dọn dẹp tiến trình Node hoặc Python cũ còn chạy nền trên cổng 5173 và 8000 nếu có
$ports = @(5173, 5174, 8000)
foreach ($p in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($proc -and ($proc.ProcessName -like "*node*" -or $proc.ProcessName -like "*python*")) {
                Write-Host "Đang giải phóng cổng $p (PID: $($proc.Id), Process: $($proc.ProcessName))..." -ForegroundColor Yellow
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# 2. Khởi động Backend Python Server ở chế độ nền
Write-Host "Khởi động Backend API server trên http://localhost:8000..." -ForegroundColor Cyan
$backendJob = Start-Process -FilePath "python" -ArgumentList "backend/run.py" -PassThru -WindowStyle Minimized

# 3. Đợi backend khởi động
Start-Sleep -Seconds 1.5

# 4. Mở trình duyệt trực tiếp vào giao diện ứng dụng
$appUrl = "http://localhost:5173/"
Write-Host "Tự động mở trình duyệt tới $appUrl..." -ForegroundColor Green
Start-Process $appUrl

# 5. Chạy Frontend Vite Dev Server
Write-Host "Khởi động Frontend Vite Dev server..." -ForegroundColor Cyan
npm --prefix frontend run dev
