# Hướng Dẫn Deploy Miễn Phí Lên Public (Public Deployment Guide)

Tài liệu này hướng dẫn bạn đưa **DTAMarkdown Studio** lên môi trường Internet công cộng (Public URL) hoàn toàn miễn phí thông qua **Render** (Full-Stack Backend + Frontend) hoặc **Vercel / Cloudflare Pages** (Frontend SPA).

---

## Cách 1: Deploy Full-Stack Miễn Phí trên Render.com (Khuyên Dùng)

Render hỗ trợ chạy ứng dụng Python FastAPI kết hợp với giao diện React tĩnh hoàn toàn tự động thông qua tệp cấu hình `render.yaml` đã tích hợp sẵn trong dự án.

### Các bước thực hiện:
1. Đẩy code lên tài khoản GitHub của bạn:
   ```powershell
   git add .
   git commit -m "feat: complete DTAMarkdown Studio with full-stack and theme support"
   git push origin main
   ```
2. Truy cập [Render.com](https://render.com) và đăng nhập bằng tài khoản GitHub.
3. Chọn **New +** > **Blueprint**.
4. Chọn repository GitHub của bạn (`markdown tu code`).
5. Render sẽ tự động nhận diện tệp `render.yaml`:
   - **Build Command**: Tự động cài đặt `pip install -r backend/requirements.txt` và biên dịch `frontend/dist`.
   - **Start Command**: `python backend/run.py`
6. Bấm **Apply**. Sau khoảng 2-3 phút, bạn sẽ nhận được một Public URL miễn phí:
   👉 `https://dtamarkdown-studio.onrender.com`

---

## Cách 2: Deploy Frontend trên Vercel

Nếu bạn muốn deploy riêng giao diện Frontend trên hệ thống CDN toàn cầu của Vercel:

### Cách thực hiện qua terminal:
```powershell
npx vercel --prod
```
*Tệp `vercel.json` đã được tạo sẵn ở thư mục gốc, Vercel sẽ tự động chạy `npm run build` và trỏ vào thư mục `frontend/dist`.*

### Hoặc qua giao diện Vercel Dashboard:
1. Truy cập [Vercel.com](https://vercel.com) > **Add New Project**.
2. Import repository GitHub của bạn.
3. Cấu hình:
   - **Framework Preset**: Vite
   - **Root Directory**: `./` (hoặc `frontend`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `frontend/dist`
4. Bấm **Deploy**. Bạn sẽ có link dạng:
   👉 `https://dtamarkdown-studio.vercel.app`

---

## Cách 3: Deploy Frontend trên Cloudflare Pages

1. Đăng nhập [Cloudflare Dashboard](https://dash.cloudflare.com/) > **Workers & Pages**.
2. Chọn **Create Application** > **Pages** > **Connect to Git**.
3. Chọn repo và cài đặt:
   - **Build command**: `npm run build`
   - **Build output directory**: `frontend/dist`
4. Bấm **Save and Deploy**. Bạn sẽ nhận được link:
   👉 `https://dtamarkdown-studio.pages.dev`

---

## 🔒 Biến Môi Trường (Environment Variables)

Khi deploy trên Render / Vercel, bạn có thể thiết lập các biến sau nếu cần:

| Biến | Giá Trị Mặc Định | Mô Tả |
| :--- | :--- | :--- |
| `PORT` | `8000` (Render tự đặt `10000`) | Cổng lắng nghe của Backend server |
| `HOST` | `0.0.0.0` | IP lắng nghe |
| `VITE_API_URL` | `/api/v1` | Đường dẫn tương đối hoặc URL backend công khai |
| `GEMINI_API_KEY` | *(Tùy chọn)* | Khóa API Google Gemini nếu muốn kích hoạt Gemini Vision OCR |

