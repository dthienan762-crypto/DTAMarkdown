export type Locale = 'vi' | 'en';

export const DEFAULT_MARKDOWN_VI = `# DTAMarkdown Studio — Không Gian Biên Tập Đa Phương Thức

Chào mừng bạn đến với **DTAMarkdown Studio**, không gian làm việc trực tuyến hiệu năng cao được tối ưu hóa chuyên sâu cho **Markdown Tiếng Việt** và **Tiếng Anh**.

Hệ thống hỗ trợ chuyển đổi đa phương thức theo thời gian thực (Real-time Streaming): nhận diện hình ảnh, nhận dạng giọng nói tiếng Việt, và chuẩn hóa bảng biểu HTML thành Markdown chuẩn GitHub (GFM).

## Mục Lục Tài Liệu
- [Tổng Quan Tính Năng](#tong-quan-tinh-nang)
- [Báo Cáo Hiệu Năng Kinh Doanh](#bao-cao-hieu-nang-kinh-doanh)
- [Mô Hình Toán Học & Thống Kê](#mo-hinh-toan-hoc-thong-ke)
- [Kiến Trúc Hệ Thống Đa Phương Thức](#kien-truc-he-thong-da-phuong-thuc)
- [Mã Nguồn Ví Dụ](#ma-nguon-vi-du)
- [Ghi Chú & Định Hướng](#ghi-chu-dinh-huong)

---

## 🌟 Tổng Quan Tính Năng

- **Vision OCR Tiếng Việt**: Trích xuất bảng biểu quét, tài liệu scan, hóa đơn và công thức toán học từ ảnh PNG, JPG, PDF.
- **Voice STT Tiếng Việt**: Ghi âm giọng nói trực tiếp qua micro trình duyệt (16-bit PCM WAV 16kHz) và xuất thành văn bản có mốc thời gian.
- **Bộ Chuẩn Hóa Văn Bản**: Tự động dọn dẹp bảng HTML phức tạp (hỗ trợ \`colspan\`, \`rowspan\`), thoát ký tự \`|\`, và bảo vệ công thức LaTeX.
- **Xuất Bản Toàn Diện**: Xuất file Markdown (\`.md\`), trang HTML độc lập có nhúng KaTeX, và file PDF tiếng Việt chuẩn hóa.

---

## 📊 Báo Cáo Hiệu Năng Kinh Doanh

Dưới đây là bảng thống kê chỉ số tăng trưởng của hệ thống xử lý tài liệu trong Quý 4:

| Chỉ Số Vận Hành | Mục Tiêu (Q4) | Thực Tế Đạt Được | Tỷ Lệ Hoàn Thành | Doanh Thu (VNĐ) |
| :--- | :--- | :--- | :--- | :--- |
| **Tài liệu chuyển đổi** | 100,000 | 148,250 | +148.2% | 741,250,000 đ |
| **Độ chính xác OCR Tiếng Việt** | 96.0% | 99.1% | +103.2% | — |
| **Thời gian phản hồi trung bình** | < 150ms | 42ms | Vượt 72% | — |
| **Người dùng hoạt động hàng tháng** | 25,000 | 68,400 | +273.6% | 1,026,000,000 đ |

> **Lưu ý nghiệp vụ**: Dữ liệu tài chính được kiểm toán tự động bởi hệ thống báo cáo định kỳ. Toàn bộ ký tự tiếng Việt có dấu được bảo toàn 100% khi kết xuất báo cáo PDF.

---

## 📐 Mô Hình Toán Học & Thống Kê (KaTeX)

Hệ thống tích hợp bộ dựng công thức Toán học chuẩn xác cao qua KaTeX.

Tích phân chuẩn Gauss trong không gian xác suất:
$$
\\int_{-\\infty}^{\\infty} e^{-x^2} \\, dx = \\sqrt{\\pi}
$$

Hàm tối ưu hóa hồi quy tuyến tính với tham số điều hòa Ridge (L2 Regularization):
$$
\\min_{w} \\left( \\frac{1}{2n} \\sum_{i=1}^{n} (y_i - w^T x_i)^2 + \\frac{\\lambda}{2} \\|w\\|_2^2 \\right)
$$

Biến đổi Fourier rời rạc (Discrete Fourier Transform):
$$
X_k = \\sum_{n=0}^{N-1} x_n \\cdot e^{-i 2\\pi k n / N}, \\quad k = 0, 1, \\dots, N-1
$$

---

## 🔄 Kiến Trúc Hệ Thống Đa Phương Thức (Mermaid)

Quy trình xử lý dữ liệu đầu vào và phát trực tiếp đến trình duyệt:

\`\`\`mermaid
graph LR
  A[Dữ liệu Đa Phương Thức] --> B{Phân Loại Đầu Vào}
  B -->|Tài liệu scan / PDF| C[Bộ Xử Lý Vision OCR]
  B -->|Giọng nói Micro 16kHz| D[Voice STT Tiếng Việt]
  B -->|Văn bản thô / Bảng HTML| E[Bộ Chuẩn Hóa Text GFM]
  C --> F[WebSocket Stream Hub]
  D --> F
  E --> F
  F --> G[Giao Diện Trực Tiếp DTAMarkdown]
\`\`\`

---

## 💻 Mã Nguồn Ví Dụ (Python FastAPI)

\`\`\`python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="DTAMarkdown Studio API", version="1.0.0")

class DocumentRequest(BaseModel):
    title: str
    content: str
    locale: str = "vi"

@app.post("/api/v1/preview")
async def generate_preview(doc: DocumentRequest):
    # Xử lý văn bản tiếng Việt có dấu
    words = len(doc.content.split())
    return {
        "status": "success",
        "title": doc.title,
        "word_count": words,
        "message": f"Tài liệu '{doc.title}' đã sẵn sàng xuất bản!"
    }
\`\`\`

---

## 💡 Ghi Chú & Định Hướng

- [x] Tối ưu hóa phông chữ tiếng Việt cho bản in PDF (Arial Unicode).
- [x] Hỗ trợ song ngữ chuyển đổi tức thì (Tiếng Việt & English).
- [x] Đồng bộ cuộn tỉ lệ 1:1 giữa trình soạn thảo CodeMirror và khung xem trước.
- [x] Xuất bản HTML độc lập tương thích chế độ Sáng / Tối (Dark Mode).
`;

export const DEFAULT_MARKDOWN_EN = `# DTAMarkdown Studio — Live Workbench

Welcome to **DTAMarkdown Studio**, the production multimodal conversion workbench optimized for both **English** and **Vietnamese** markdown authoring.

## Features Overview
- **Vision OCR**: Extract scanned document tables and LaTeX math equations with pixel precision.
- **Voice STT**: Transcribe microphone voice into timestamped Markdown paragraphs.
- **Text Normalizer**: Clean messy HTML tables (with \`colspan\`/\`rowspan\`), escape pipes, and generate TOC.
- **Export Engine**: Instant downloads to Markdown (\`.md\`), standalone styled HTML, and server-compiled PDF.

---

## 📊 Tabular Financial Metrics

| Metric | Target (Q4) | Actual (Q4) | Growth | Revenue (USD) |
| :--- | :--- | :--- | :--- | :--- |
| **Multimodal Ingestion** | 100,000 | 148,500 | +48.5% | $320,000 |
| **OCR Table Precision** | 95.0% | 98.7% | +3.7% | — |
| **KaTeX Parsing Rate** | 92.0% | 97.4% | +5.4% | — |
| **Active Monthly Users** | 30,000 | 65,200 | +117.3% | $485,000 |

---

## 📐 Mathematical Formulas (KaTeX)

Standard Gauss probability density integral:
$$
\\int_{-\\infty}^{\\infty} e^{-x^2} \\, dx = \\sqrt{\\pi}
$$

Ridge regression loss function:
$$
\\mathcal{L}(w) = \\frac{1}{2N} \\|y - Xw\\|_2^2 + \\frac{\\lambda}{2} \\|w\\|_2^2
$$

Discrete Fourier Transform definition:
$$
X_k = \\sum_{n=0}^{N-1} x_n \\cdot e^{-i 2\\pi k n / N}
$$

---

## 🔄 Real-Time System Flow (Mermaid)

\`\`\`mermaid
graph LR
  Input[Multimodal Input] --> Pipeline{Detection}
  Pipeline -->|Image/Scan| OCR[Vision OCR Engine]
  Pipeline -->|Voice/Audio| STT[Voice STT 16kHz]
  Pipeline -->|Messy HTML| Text[Text Normalizer]
  OCR --> Stream[WebSocket Stream]
  STT --> Stream
  Text --> Stream
  Stream --> Studio[Live Split Studio]
\`\`\`

---

## 💻 Code Snippet

\`\`\`typescript
interface DocumentExportOptions {
  title: string;
  format: 'md' | 'html' | 'pdf';
  includeKatex: boolean;
}

export function exportDocument(options: DocumentExportOptions): void {
  console.log(\`Exporting document "\${options.title}" as \${options.format.toUpperCase()}...\`);
}
\`\`\`
`;

export const translations = {
  vi: {
    brandSubtitle: 'OCR Đa Phương Thức • STT Giọng Nói • KaTeX • Mermaid',
    serverChecking: 'Đang kết nối...',
    serverReady: 'Máy Chủ Sẵn Sàng',
    standaloneMode: 'Chế Độ Độc Lập',
    splitView: 'Chia Đôi',
    sourceView: 'Mã Nguồn',
    previewView: 'Xem Trước',
    newDocument: 'Tạo Mới',
    newDocumentTitle: 'Tạo tài liệu mới (Xóa trắng)',
    languageSwitch: 'Ngôn Ngữ',
    templates: 'Mẫu Tài Liệu',
    templateVi: 'Mẫu Tiếng Việt',
    templateEn: 'Mẫu English',
    dragDropPrompt: 'Kéo thả tệp tin vào đây hoặc dán trực tiếp',
    supportedFiles: 'PDF, Ảnh scan (PNG/JPG), Âm thanh (WAV/MP3), Bảng HTML',
    browseFiles: 'Chọn tệp từ máy',
    recordVoice: 'Ghi Âm Giọng Nói',
    recordVoiceTitle: 'Ghi âm qua micro (16-bit PCM WAV)',
    pasteTextHtml: 'Dán Chữ / Bảng HTML',
    pasteTextHtmlTitle: 'Dán văn bản thô hoặc mã bảng HTML để chuẩn hóa',
    micError: 'Lỗi micro',
    recordingVoice: 'Đang ghi âm...',
    stopRecording: 'Dừng & Chuyển Đổi',
    cancelRecording: 'Hủy Ghi Âm',
    pasteModalTitle: 'Chuẩn Hóa Văn Bản & Bảng Biểu HTML',
    pasteModalDesc: 'Dán văn bản thô, tài liệu copy từ web hoặc mã nguồn HTML chứa bảng để tự động chuyển thành Markdown chuẩn GitHub (GFM).',
    pastePlaceholder: 'Dán văn bản hoặc mã <table>...</table> vào đây...',
    normalizeButton: 'Bắt Đầu Chuẩn Hóa',
    cancelButton: 'Hủy Bỏ',
    statusReady: 'Sẵn Sàng',
    statusUploading: 'Đang tải lên...',
    statusConverting: 'Đang chuyển đổi...',
    statusFailed: 'Thất bại',
    statusCancelled: 'Đã hủy',
    bold: 'Chữ Đậm',
    italic: 'Chữ Nghiêng',
    heading1: 'Tiêu Đề 1',
    heading2: 'Tiêu Đề 2',
    insertTable: 'Chèn Bảng',
    insertMath: 'Chèn Công Thức KaTeX',
    insertCode: 'Chèn Đoạn Mã',
    insertMermaid: 'Chèn Sơ Đồ Mermaid',
    insertList: 'Chèn Danh Sách',
    streamingInput: 'Đang nhận dữ liệu trực tiếp...',
    previewEmpty: 'Bản xem trước trực tiếp sẽ hiển thị tại đây...',
    previewSupportNote: 'Hỗ trợ bảng GFM, công thức toán KaTeX ($..$ và $$..$$), và sơ đồ Mermaid',
    connected: 'Đã Kết Nối',
    offline: 'Ngoại Tuyến',
    words: 'từ',
    chars: 'ký tự',
    readingTime: 'phút đọc',
    copy: 'Sao Chép',
    copied: 'Đã Chép!',
    downloadMd: '.md',
    downloadHtml: 'HTML',
    exportPdf: 'PDF',
    quickPrint: 'In Nhanh / PDF Trình Duyệt',
    serverPdf: 'PDF Máy Chủ (Chuẩn Tiếng Việt)',
    toastSavedMd: 'Đã lưu Markdown',
    toastSavedMdDesc: 'Tệp document.md đã được tải về máy',
    toastCopied: 'Đã sao chép vào bộ nhớ tạm',
    toastCopiedDesc: 'Nội dung Markdown đã sẵn sàng để dán',
    toastConversionComplete: 'Chuyển đổi hoàn tất',
    toastConversionCompleteDesc: 'Nội dung Markdown đã hiển thị trong trình soạn thảo',
    toastTextNormalized: 'Đã chuẩn hóa văn bản',
    toastTextNormalizedDesc: 'Markdown chuẩn GFM đã được nạp vào trình soạn thảo',
    toastVoiceCaptured: 'Đã ghi âm giọng nói',
    toastVoiceCapturedDesc: 'Đang nhận dạng âm thanh 16-bit PCM WAV...',
    toastPdfCompiled: 'Đã biên dịch PDF',
    toastPdfCompiledDesc: 'File PDF tiếng Việt chuẩn hóa đã được tải về',
  },
  en: {
    brandSubtitle: 'Multimodal OCR • Voice STT • KaTeX • Mermaid',
    serverChecking: 'Checking...',
    serverReady: 'Server Ready',
    standaloneMode: 'Standalone Mode',
    splitView: 'Split',
    sourceView: 'Source',
    previewView: 'Preview',
    newDocument: 'New',
    newDocumentTitle: 'Clear document and start fresh',
    languageSwitch: 'Language',
    templates: 'Templates',
    templateVi: 'Vietnamese Template',
    templateEn: 'English Template',
    dragDropPrompt: 'Drag & drop files or paste directly',
    supportedFiles: 'PDF, Scanned Images (PNG/JPG), Audio (WAV/MP3), HTML tables',
    browseFiles: 'Browse files',
    recordVoice: 'Record Voice',
    recordVoiceTitle: 'Record microphone voice (16-bit PCM WAV)',
    pasteTextHtml: 'Paste Text/HTML',
    pasteTextHtmlTitle: 'Paste unstructured text or HTML to normalize',
    micError: 'Microphone error',
    recordingVoice: 'Recording voice...',
    stopRecording: 'Stop & Convert',
    cancelRecording: 'Cancel',
    pasteModalTitle: 'Normalize Text & HTML Tables',
    pasteModalDesc: 'Paste unstructured text, web content, or HTML tables to automatically convert into pristine GitHub Flavored Markdown (GFM).',
    pastePlaceholder: 'Paste text or <table>...</table> HTML here...',
    normalizeButton: 'Normalize to Markdown',
    cancelButton: 'Cancel',
    statusReady: 'Ready',
    statusUploading: 'Uploading...',
    statusConverting: 'Converting...',
    statusFailed: 'Failed',
    statusCancelled: 'Cancelled',
    bold: 'Bold',
    italic: 'Italic',
    heading1: 'Heading 1',
    heading2: 'Heading 2',
    insertTable: 'Insert Table',
    insertMath: 'Insert KaTeX Formula',
    insertCode: 'Code Block',
    insertMermaid: 'Mermaid Diagram',
    insertList: 'Unordered List',
    streamingInput: 'Streaming input...',
    previewEmpty: 'Live preview will appear here...',
    previewSupportNote: 'Supports GFM tables, KaTeX math formulas ($..$ and $$..$$), and Mermaid diagrams',
    connected: 'Connected',
    offline: 'Offline Mode',
    words: 'words',
    chars: 'chars',
    readingTime: 'min read',
    copy: 'Copy',
    copied: 'Copied!',
    downloadMd: '.md',
    downloadHtml: 'HTML',
    exportPdf: 'PDF',
    quickPrint: 'Quick Print / Browser PDF',
    serverPdf: 'Server-Compiled PDF',
    toastSavedMd: 'Saved Markdown',
    toastSavedMdDesc: 'document.md downloaded',
    toastCopied: 'Copied to clipboard',
    toastCopiedDesc: 'Markdown text is ready to paste',
    toastConversionComplete: 'Conversion complete',
    toastConversionCompleteDesc: 'Markdown output is live in the editor',
    toastTextNormalized: 'Text normalized',
    toastTextNormalizedDesc: 'Pristine Markdown loaded in editor',
    toastVoiceCaptured: 'Voice captured',
    toastVoiceCapturedDesc: 'Transcribing 16-bit PCM WAV with timestamps...',
    toastPdfCompiled: 'PDF compiled',
    toastPdfCompiledDesc: 'High-fidelity PDF downloaded from server',
  },
};

