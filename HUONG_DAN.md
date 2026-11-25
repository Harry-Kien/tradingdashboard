# Hướng dẫn cài và dùng webapp

Webapp phân tích thị trường chạy ngay trên máy của bạn, lấy giá trực tiếp từ MetaTrader 5 (MT5) của chính bạn.
Nó **chỉ đọc**: không đặt lệnh, không sửa gì trong MT5, không gửi dữ liệu của bạn đi đâu. Trang chỉ mở được trên máy này
(địa chỉ 127.0.0.1), máy khác trong mạng không vào được.

> Mọi con số trên trang là số liệu mô tả thị trường và kết quả đo lại trên dữ liệu quá khứ, **không phải lời khuyên đầu tư**.
> Giao dịch CFD và Forex có rủi ro mất vốn cao.

## Cần có

- Máy tính Windows 10 hoặc 11.
- **MetaTrader 5** bản máy tính, của bất kỳ sàn nào, đã **đăng nhập tài khoản DEMO**. Mặc định webapp chỉ nhận tài khoản demo
  (đổi ở trang Cài đặt nếu muốn).
- Python 3.11 trở lên. **Không cần tự cài**: chưa có thì `BAT_DAU.bat` hỏi rồi cài giúp bằng winget có sẵn trong Windows
  (nguồn chính thức của Python). Máy không có winget thì tải ở https://www.python.org/downloads/windows/ và tick ô **"Add python.exe to PATH"**.

## Bắt đầu: bấm đúp một tệp

1. Giải nén tệp zip vào một thư mục, ví dụ `C:\HarryGoldResearch`.
2. Mở MT5 và đăng nhập tài khoản demo.
3. Bấm đúp **`BAT_DAU.bat`**. Lần đầu nó tự cài Python (nếu thiếu, có hỏi trước) và thư viện, tạo cấu hình, tạo biểu tượng
   **Harry Gold Research** ngoài màn hình, rồi mở trang trong trình duyệt. Những lần sau bấm biểu tượng đó là xong.
4. Muốn tắt webapp thì đóng cửa sổ đen có tên "Harry Gold Research".

`CAI_DAT.bat` và `CHAY_WEBAPP.bat` vẫn còn cho ai quen cách cũ (cài riêng, chạy riêng).

## Có gì trong webapp

| Trang | Dùng để làm gì |
|---|---|
| **Thị trường** | Bảng giá trực tiếp của mọi mã trong MT5 (chạy theo từng tick), tín hiệu kỹ thuật 19 chỉ báo trên 4 khung, sức mạnh 8 đồng tiền, bản đồ nhiệt, tương quan, biến động theo giờ, bốn phiên lớn và lịch tin, thông số hợp đồng (pip, ký quỹ, swap). |
| **Tin tức** | Tin thị trường mới nhất và vị thế COT. |
| **Biểu đồ** | Nến M5 đến D1 cập nhật theo từng tick; EMA20, EMA50, Bollinger, RSI chạy theo tick; đồng hồ đếm ngược tới lúc nến đóng; hỗ trợ/kháng cự 2 giờ, khoảng trống giá (FVG), khối lệnh; công cụ vẽ; chọn mã bất kỳ trong MT5. Nút **Phân tích điểm vào** chạy các phương pháp tùy chọn tính theo ATR và cho biết kết quả đo lại của từng phương pháp trên dữ liệu của chính mã đó. |
| **Công cụ** | Tính khối lượng theo % rủi ro, giá trị pip, lãi lỗ, ký quỹ (hỏi thẳng MT5 để có số chính xác), pivot, Fibonacci, kỳ vọng R:R, xác suất chuỗi thua. |
| **Sổ giao dịch** | Nhật ký điểm vào (mọi điểm vào của các phương pháp, chấm bằng giá thật) và tài khoản MT5 (vốn, lệnh đang mở, lãi lỗ theo ngày; số tài khoản được che). |
| **Học** | Kiến thức CFD, Forex, các loại lệnh, phong cách giao dịch; giải thích từng chỉ báo. |

## Chỉnh cấu hình (`cau-hinh.json`)

Mở `cau-hinh.json` bằng Notepad. Sửa xong thì tắt rồi mở lại webapp. Các mục hay dùng nằm trong `"gia"`:

| Mục | Ý nghĩa | Mặc định |
|---|---|---|
| `gia.mt5.terminal` | Đường dẫn `terminal64.exe` của MT5 muốn dùng. Để trống thì webapp tự tìm MT5 đang mở; **máy mở nhiều MT5 cùng lúc thì phải ghi**, ví dụ `"C:\\Program Files\\MetaTrader 5\\terminal64.exe"` (nhớ viết hai dấu `\\`). | `""` |
| `gia.ma_vang` | Tên mã vàng của sàn. Để trống thì tự tìm (XAUUSD, XAUUSDm, XAUUSD.r, GOLD…). | `""` |
| `gia.mt5.chi_demo` | `true`: chỉ đọc tài khoản demo. `false`: đọc cả tài khoản thật (webapp vẫn chỉ đọc giá, không đặt lệnh). | `true` |
| `gia.mt5.lech_gio_san` | Giờ máy chủ của sàn lệch UTC bao nhiêu giờ. Để `null` thì webapp tự đo từ tick lúc thị trường mở và nhớ lại cho lúc thị trường nghỉ; mọi giờ trên trang đã được đổi về giờ Việt Nam. Chỉ ghi số (ví dụ `2`) khi tự đo bị sai. | `null` |
| `thi_truong.chu_ky_giay` | Bảng giá đọc MT5 bao lâu một lần (giây). | `0.05` |
| `tin_tuc.bat`, `lich_mang.bat`, `cot.bat` | Bật/tắt phần tin tức, lịch tin kinh tế lấy từ Internet, vị thế COT của CFTC. Đây là những chỗ duy nhất webapp gọi ra Internet. | `true` |
| `ten` | Tên hiện ở góc trái trang. | |

## Gặp sự cố

Ô trạng thái ở đầu trang **Thị trường** ("Trực tiếp · … mã" hoặc "Chưa có giá trực tiếp · lý do") và dòng nguồn giá trên trang
**Biểu đồ** luôn ghi rõ vì sao chưa có giá. Bản đầy đủ từng bộ phận nằm ở http://127.0.0.1:8765/api/tinh-trang.

| Thấy gì | Làm gì |
|---|---|
| "Chưa thấy MT5 nào đang mở" | Mở MT5, đăng nhập, chờ khoảng 1 phút rồi tải lại trang. |
| "Máy đang mở nhiều MT5" | Ghi đường dẫn MT5 muốn dùng vào `gia.mt5.terminal`. |
| "không phải tài khoản DEMO" | Đăng nhập tài khoản demo trong MT5, hoặc đặt `gia.mt5.chi_demo` = `false`. |
| "Sàn … không có mã vàng" | Ghi đúng tên mã vàng của sàn (xem trong Market Watch của MT5) vào `gia.ma_vang`. |
| Giờ trên biểu đồ lệch vài tiếng | Ghi `gia.mt5.lech_gio_san` theo giờ máy chủ của sàn (MT5 → Market Watch, góc trên có giờ máy chủ). |
| Cửa sổ đen báo "Chưa cài đủ thư viện" | Bấm đúp lại `BAT_DAU.bat` (tự cài lại thư viện). |
| Trình duyệt không mở | Tự mở http://127.0.0.1:8765 |

## An toàn

- Webapp không có lời gọi đặt lệnh nào tới MT5.
- Webapp không bao giờ tự mở MT5. Nếu thư viện MT5 lỡ tự mở thêm một MT5 khác, webapp ngắt kết nối và đóng bản vừa mở.
- Số tài khoản được che khi hiện (chỉ còn 3 số cuối).
- Không cần và không lưu mật khẩu MT5: webapp nối vào MT5 đang mở sẵn trên máy.

Phần thư viện biểu đồ là TradingView Lightweight Charts (giấy phép Apache-2.0), xem `tinh/NGUON.md`.
