# Mã nguồn mở của bên thứ ba dùng trong webapp

## TradingView Lightweight Charts™ 5.3.0

- Dùng để: vẽ biểu đồ nến trên trang Biểu đồ.
- Tệp: `lightweight-charts-5.3.0/lightweight-charts.standalone.production.js` (198.600 byte).
- Tải ngày 21/11/2026 từ `https://cdn.jsdelivr.net/npm/lightweight-charts@5.3.0/dist/lightweight-charts.standalone.production.js`.
- SHA-256: `338a625ece52c5b85fb026e222dad5d0f365f745060afbfae96bda91636142e9` (đã so khớp với mã băm jsDelivr công bố cho tệp này).
- Kho mã gốc: https://github.com/tradingview/lightweight-charts
- Giấy phép: Apache License 2.0, https://www.apache.org/licenses/LICENSE-2.0 . Bản quyền (c) TradingView, Inc.
- Ghi nguồn: giấy phép của thư viện yêu cầu ghi nguồn TradingView trên trang dùng nó. Webapp giữ biểu tượng TradingView ở góc biểu đồ
  (tùy chọn `attributionLogo`) và có dòng "Biểu đồ vẽ bằng TradingView Lightweight Charts™" dưới biểu đồ. Đừng tắt hai chỗ này.
- Tệp được phục vụ từ máy qua `/tinh/lightweight-charts.js`; lúc chạy webapp không gọi ra mạng. Tệp không bị sửa.
- Nếu xóa tệp, trang Biểu đồ tự quay về lớp vẽ canvas dự phòng (cũng có thể ép bằng `?ve=cu`).

## Phông chữ Be Vietnam Pro

- Dùng để: phông chữ của cả năm trang (giao diện đổi ngày 24/11/2026).
- Tệp: `phong/be-vietnam-pro-{400,500,600,700}-{vietnamese,latin-ext,latin}.woff2` (12 tệp, tổng 189.656 byte) và `phong/phong.json` (danh sách tệp,
  độ đậm và khoảng ký tự của từng tệp, do bước tải ghi ra).
- Tải ngày 24/11/2026 từ Google Fonts (`https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700`, các tệp nằm ở
  `fonts.gstatic.com`), theo lời đồng ý của chủ dự án. Mỗi tệp đã được kiểm là đúng định dạng WOFF2 trước khi lưu.
- Kho mã gốc: https://github.com/bettergui/BeVietnamPro
- Giấy phép: SIL Open Font License 1.1, https://openfontlicense.org . Bản quyền (c) The Be Vietnam Pro Project Authors.
- Tệp được phục vụ từ máy qua `/tinh/phong/<tên tệp>`; lúc chạy webapp không gọi ra mạng. Tệp không bị sửa.
- Nếu xóa thư mục `phong`, trang tự dùng phông có sẵn của máy (Segoe UI).
