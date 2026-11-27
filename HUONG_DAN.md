# Hướng dẫn cài và dùng webapp

Webapp phân tích thị trường chạy ngay trên máy của bạn, lấy giá trực tiếp từ MetaTrader 5 (MT5) của chính bạn.
Nó **chỉ đọc**: không đặt lệnh, không sửa gì trong MT5, không tự đưa dữ liệu MT5 lên website demo. AI hoặc Telegram chỉ gửi nội dung khi bạn bật và sử dụng chức năng tương ứng. Trang chỉ mở được trên máy này
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
4. Lần đầu, tạo tài khoản chủ trên trang mở ra (mật khẩu từ 12 ký tự). Những lần sau đăng nhập tài khoản này để xem dữ liệu MT5 riêng. Tài khoản đăng ký thêm trên cùng máy chỉ có kho biểu đồ riêng, không được xem MT5 của chủ.
5. Muốn tắt webapp thì đóng cửa sổ đen có tên "Harry Gold Research".

`CAI_DAT.bat` và `CHAY_WEBAPP.bat` vẫn còn cho ai quen cách cũ (cài riêng, chạy riêng).

## Có gì trong webapp

| Trang | Dùng để làm gì |
|---|---|
| **Thị trường** | Bảng giá trực tiếp của mọi mã trong MT5 (chạy theo từng tick), tín hiệu kỹ thuật 19 chỉ báo trên 4 khung, sức mạnh 8 đồng tiền, bản đồ nhiệt, tương quan, biến động theo giờ, bốn phiên lớn và lịch tin, thông số hợp đồng (pip, ký quỹ, swap). |
| **Tin tức** | Tin thị trường mới nhất và vị thế COT. |
| **Biểu đồ** | Nến M5 đến D1 cập nhật theo từng tick; EMA20, EMA50, Bollinger, RSI chạy theo tick; đồng hồ đếm ngược tới lúc nến đóng; hỗ trợ/kháng cự 2 giờ, khoảng trống giá (FVG), khối lệnh; công cụ vẽ; chọn mã bất kỳ trong MT5. **Công cụ vẽ** (cột bên trái biểu đồ, 83 công cụ) xếp theo nhóm như TradingView: Đường, kênh và pitchfork; Fibonacci và Gann; Mẫu hình (hài hòa, Elliott, chu kỳ); Dự báo và đo lường; Hình học; Chữ và chú thích; Biểu tượng. Nút nhóm mang công cụ dùng gần nhất, bấm mũi tên nhỏ bên phải nút (hoặc chuột phải vào nút; trên điện thoại chạm vào nút) để mở danh sách có ô tìm công cụ; bấm ☆ để đưa công cụ vào nhóm Yêu thích. Phím tắt vẽ: Alt+T đường xu hướng, Alt+F Fibonacci thoái lui, Alt+Shift+R hình chữ nhật. Ô **Độ sâu** ở dưới biểu đồ có công tắc **Hiện trên biểu đồ**: thanh khối lượng chờ mua bán của sàn nằm ngay cạnh thang giá và các mức chờ lớn nhất được kẻ nét đứt (chỉ khi sàn gửi khối lượng). **Bấm chuột phải** (trên điện thoại: giữ ngón tay) vào biểu đồ để chép giá, đặt cảnh báo giá, vẽ ngay tại mức đó, thử lệnh với dừng lỗ tại mức đó (vẽ vị thế, tính lot, mở trang Kiểm tra lệnh; không đặt lệnh), xem thông tin nến, tải hoặc chép ảnh biểu đồ; bấm chuột phải vào một hình đã vẽ để nhân bản, khóa, ẩn, đổi màu, đổi nét, đưa lên trên hoặc xuống dưới. Phím tắt: Alt+H đường ngang, Alt+J tia ngang, Alt+V đường dọc, Alt+A cảnh báo, Alt+C chép giá, Alt+R về nến mới nhất, Alt+S tải ảnh. Cảnh báo giá chỉ báo khi trang Biểu đồ của mã đó đang mở. Nút **Phân tích điểm vào** chạy các phương pháp tùy chọn tính theo ATR và cho biết kết quả đo lại của từng phương pháp trên dữ liệu của chính mã đó. |
| **Công cụ** | Tính khối lượng theo % rủi ro, giá trị pip, lãi lỗ, ký quỹ (hỏi thẳng MT5 để có số chính xác), pivot, Fibonacci, kỳ vọng R:R, xác suất chuỗi thua. |
| **Sổ giao dịch** | Nhật ký điểm vào (mọi điểm vào của các phương pháp, chấm bằng giá thật) và tài khoản MT5 (vốn, lệnh đang mở, lãi lỗ theo ngày; số tài khoản được che). |
| **Học** | Kiến thức CFD, Forex, các loại lệnh, phong cách giao dịch; giải thích từng chỉ báo. |

## Chỉnh cấu hình (`cau-hinh.json`)

Mở `cau-hinh.json` bằng Notepad. Sửa xong thì tắt rồi mở lại webapp. Các mục hay dùng nằm trong `"gia"`:

| Mục | Ý nghĩa | Mặc định |
|---|---|---|
| `gia.mt5.terminal` | Đường dẫn `terminal64.exe` của MT5 muốn dùng. Để trống thì webapp tự tìm MT5 đang mở; **máy mở nhiều MT5 cùng lúc thì phải ghi**, ví dụ `"D:\\MT5-San-A\\terminal64.exe"` (nhớ viết hai dấu `\\`). | `""` |
| `gia.ma_vang` | Tên mã vàng của sàn. Để trống thì tự tìm (XAUUSD, XAUUSDm, XAUUSD.r, GOLD…). | `""` |
| `gia.mt5.chi_demo` | `true`: chỉ đọc tài khoản demo. `false`: đọc cả tài khoản thật (webapp vẫn chỉ đọc giá, không đặt lệnh). | `true` |
| `gia.mt5.lech_gio_san` | Giờ máy chủ của sàn lệch UTC bao nhiêu giờ. Để `null` thì webapp tự đo từ tick lúc thị trường mở và nhớ lại cho lúc thị trường nghỉ; mọi giờ trên trang đã được đổi về giờ Việt Nam. Chỉ ghi số (ví dụ `2`) khi tự đo bị sai. | `null` |
| `thi_truong.chu_ky_giay` | Bảng giá đọc MT5 bao lâu một lần (giây). | `0.05` |
| `tin_tuc.bat`, `lich_mang.bat`, `cot.bat` | Bật/tắt phần tin tức, lịch tin kinh tế lấy từ Internet, vị thế COT của CFTC. Đây là những chỗ duy nhất webapp gọi ra Internet. | `true` |
| `ten` | Tên hiện ở góc trái trang. | |

## Tính năng tùy chọn

Webapp chạy đầy đủ mà không cần các phần dưới đây; mỗi phần chỉ bật thêm một tính năng.

- **Hỏi AI và Học với gia sư** cần khóa API Anthropic của chính bạn. Đặt một lần: mở PowerShell, gõ
  `setx ANTHROPIC_API_KEY "khóa-của-bạn"`, rồi tắt webapp và mở lại bằng `BAT_DAU.bat` (cửa sổ đã mở trước khi đặt khóa không thấy khóa mới).
  Mỗi câu trả lời tốn vài xu; webapp tự giới hạn số lượt và số tiền mỗi ngày. Khóa chỉ nằm trên máy bạn, chỉ được gửi tới Anthropic.
- **Ảnh biểu đồ kèm tin Telegram** cần Playwright: `python -m pip install playwright` rồi `python -m playwright install chromium`. Sau đó bật ô
  "Kèm ảnh biểu đồ của lệnh" ở trang Nhóm Telegram. Không cài thì tin vẫn được gửi bằng chữ.
- **Dò lỗi mã** (chỉ khi bạn sửa mã): `python -m pip install ruff`, rồi `python -m ruff check so_cong_khai`.

## Gặp sự cố

Ô trạng thái ở đầu trang **Thị trường** ("Trực tiếp · … mã" hoặc "Chưa có giá trực tiếp · lý do") và dòng nguồn giá trên trang
**Biểu đồ** luôn ghi rõ vì sao chưa có giá. Bản đầy đủ từng bộ phận nằm ở http://127.0.0.1:8769/api/tinh-trang.

| Thấy gì | Làm gì |
|---|---|
| "Chưa thấy MT5 nào đang mở" | Mở MT5, đăng nhập, chờ khoảng 1 phút rồi tải lại trang. |
| "Máy đang mở nhiều MT5" | Ghi đường dẫn MT5 muốn dùng vào `gia.mt5.terminal`. |
| "không phải tài khoản DEMO" | Đăng nhập tài khoản demo trong MT5, hoặc đặt `gia.mt5.chi_demo` = `false`. |
| "Sàn … không có mã vàng" | Ghi đúng tên mã vàng của sàn (xem trong Market Watch của MT5) vào `gia.ma_vang`. |
| Giờ trên biểu đồ lệch vài tiếng | Ghi `gia.mt5.lech_gio_san` theo giờ máy chủ của sàn (MT5 → Market Watch, góc trên có giờ máy chủ). |
| Cửa sổ đen báo "Chưa cài đủ thư viện" | Bấm đúp lại `BAT_DAU.bat` (tự cài lại thư viện). |
| Trình duyệt không mở | Tự mở http://127.0.0.1:8769 |
| "Nút Hỏi AI đang khóa" | Đặt khóa API như mục **Tính năng tùy chọn**, rồi mở lại webapp bằng `BAT_DAU.bat`. |

## An toàn

- Webapp không có lời gọi đặt lệnh nào tới MT5.
- Webapp không bao giờ tự mở MT5. Nếu thư viện MT5 lỡ tự mở thêm một MT5 khác, webapp ngắt kết nối và đóng bản vừa mở.
- Số tài khoản được che khi hiện (chỉ còn 3 số cuối).
- Không cần và không lưu mật khẩu MT5: webapp nối vào MT5 đang mở sẵn trên máy.

Phần thư viện biểu đồ là TradingView Lightweight Charts (giấy phép Apache-2.0), xem `tinh/NGUON.md`.

## Lưu bản vẽ riêng theo tài khoản

Tài khoản biểu đồ tách biệt tài khoản MT5. Bấm **Đăng nhập để vẽ và lưu chart** ở ngay trên khung nến, chọn **Tạo tài khoản**, đặt tên đăng nhập và mật khẩu từ 12 ký tự. Mỗi tài khoản có kho bản vẽ riêng theo mã. Đăng xuất, đăng nhập lại hoặc mở lại máy chủ webapp vẫn dùng kho đó.

- Khi thấy **Đã lưu trên máy chủ**, bản vẽ đã được máy chủ nhận. **Lưu ngay** gửi thay đổi đang chờ; bình thường hệ thống tự lưu.
- Khi mất mạng, bản nháp được giữ theo tài khoản trong trình duyệt hiện tại và gửi lại khi kết nối trở lại. Nếu còn chữ **Chưa đồng bộ**, đừng xóa dữ liệu trình duyệt hoặc đổi máy trước khi lưu thành công.
- **Lịch sử bản vẽ** giữ tối đa 20 phiên bản theo mã. **Khôi phục** tạo phiên bản mới và giữ các bản trước trong lịch sử.
- Khi hai tab cùng sửa một hình, trạng thái báo xung đột. Bấm vào trạng thái để chọn giữ bản trên máy này, bản trên máy chủ, hoặc cả hai. Các thay đổi trên những hình khác nhau được ghép tự động.

**Bản vẽ đã có từ trước khi nâng cấp:** đăng ký tài khoản đầu tiên của máy này, mở **Tài khoản chart**, bấm **Nhập kho bản vẽ cũ của máy này**. Kho cũ và phần nháp chưa gửi còn trong trình duyệt cũ đều được nhập khi có thể; giữ nguyên nguồn. Nhập lại cùng bản nháp không nhân đôi; khi trùng id nhưng khác nội dung thì giữ thêm một bản, không ghi đè chart mới. Các tài khoản tạo sau không được đọc hoặc nhập kho cũ.

Bản nháp vẽ khi chưa đăng nhập không tự gán cho tài khoản để tránh trộn dữ liệu. Sau khi đăng nhập, mở **Tài khoản chart → Nhập bản nháp mã đang xem** nếu muốn chuyển bản nháp đó vào kho riêng.

Kho này thuộc **cùng một máy chủ webapp**. Hai bản cài riêng trên hai máy không tự trở thành một dịch vụ đám mây. Máy chủ hiện chỉ nghe ở địa chỉ cục bộ; việc triển khai Internet, HTTPS, đăng nhập Google và bảo vệ toàn bộ dữ liệu tài khoản giao dịch cần một đợt triển khai riêng. Không có mật khẩu nào được lưu dạng rõ; mã phiên nằm trong cookie HttpOnly, không nằm trong localStorage. Hãy giữ bản sao lưu ở nơi độc lập với máy đang chạy.


## Vẽ chart và chỉ báo realtime (27/11/2026)

Bạn có thể xem chart, đổi mã/khung và dùng chỉ báo ngay. Khi chọn công cụ vẽ, sửa hình, hoàn tác hoặc vẽ từ menu chuột phải, webapp yêu cầu đăng nhập tài khoản chart. Đăng nhập xong chọn lại công cụ để vẽ; bản vẽ được lưu theo tài khoản như hướng dẫn ở trên. Các bản nháp từ trước nâng cấp được giữ để nhập lại, không bị xóa.

Trong **Thêm chỉ báo**, có **75 loại chỉ báo tùy chỉnh**, cho phép thêm nhiều bản cùng loại và chỉnh chu kỳ/màu. Ba loại mới là **Z-score giá đóng**, **Efficiency Ratio** và **NATR (%)**. Dùng ô tìm để chọn. Đây là phép đo giá/biến động, không phải xác suất thắng. Bộ chỉ báo đang bật được lưu riêng cho tài khoản trên trình duyệt hiện tại; **Mẫu của tôi** và danh sách yêu thích đồng bộ về kho riêng trên cùng máy chủ. Tài khoản đầu tiên có thể nhập mẫu cũ từ máy chủ khi chọn **Nhập kho bản vẽ cũ của máy này**, nếu chưa có kho mẫu riêng; kho nguồn được giữ nguyên. Mẫu chỉ báo có kiểm phiên bản cơ sở. Các mẫu khác nhau được ghép; cùng mẫu sửa khác nhau sẽ hiện nút báo xung đột trên thanh lưu để chọn giữ bản trên máy, trên máy chủ hoặc giữ cả hai.

Khi có nguồn MT5, nến/Bid/Ask cập nhật theo tick; chỉ báo tùy chỉnh được gom nhịp khoảng 250 ms, tự giãn nhịp nếu phép tính nặng. Cập nhật chuỗi thường chỉ thay đuôi; ZigZag, Fractals và phân kỳ RSI có thể sửa vị trí trong quá khứ nên được nạp lại đầy đủ. Chỉ báo theo khối lượng dùng **tick volume**, không phải khối lượng giao dịch tập trung. Nếu chỉ có kho nến cũ, không hiển thị nó như giá realtime.

Mở **Chất lượng realtime** trên chart để xem thời gian xử lý JavaScript của nến và P95 của tối đa 120 mẫu gần nhất. Đây không phải độ trễ từ sàn tới màn hình, không phải kết quả so sánh với TradingView. Bộ chỉ báo tùy chỉnh phản ánh nến đang chạy; luật/tín hiệu hệ thống vẫn dùng điều kiện nến đóng của từng phương pháp.

Sau nâng cấp, đóng rồi mở lại webapp để máy chủ nạp mã mới. Tài khoản chart hiện chạy trên cùng máy chủ cục bộ; việc triển khai công khai cho nhiều khách hàng còn cần HTTPS, xác thực và phân quyền toàn bộ dữ liệu, nguồn giá được cấp quyền và kiểm thử tải thực tế.


## Các sửa lỗi sau đợt rà soát tổng thể 27/11/2026

- **Mẫu chỉ báo:** không để tab cũ ghi đè tab mới; giữ thay đổi phát sinh khi đang gửi và gửi lại sau khi mất mạng. Bấm trạng thái mẫu trên thanh lưu để xử lý xung đột. Kho JSON hỏng được báo lỗi, giữ nguyên tệp để phục hồi sao lưu; không tự thay bằng kho rỗng.
- **Cảnh báo đường vẽ:** phải đăng nhập. Tài khoản chủ đầu tiên tiếp tục dùng cảnh báo cũ của máy; tài khoản khác có kho cảnh báo, lịch sử và kết nối Telegram riêng. Không xóa được cảnh báo của người khác. Vòng nền kiểm các kho riêng khi máy chủ chạy; một kho hỏng không chặn toàn bộ vòng.
- **Nối Telegram:** chọn Nối Telegram riêng, gửi lệnh `/start ...` chứa mã dùng một lần vào chat riêng của bạn với bot đã cấu hình, rồi bấm Kiểm tra. Mã hết hạn sau 10 phút. Webapp không đưa danh sách chat của những người khác để bạn chọn. Đóng trình duyệt vẫn có thể nhận Telegram khi máy chủ webapp tiếp tục chạy; tắt máy chủ thì cảnh báo nền dừng.
- **Phát lại:** bản vẽ đang dùng cho phân tích hiện tại được giữ riêng. Bạn có thể vẽ tạm trong phiên luyện mà không ghi đè kho thật; thoát phát lại sẽ trả bản vẽ thật về, gồm cả thay đổi vừa đồng bộ trong lúc luyện. Nháp chưa ghi được xuống bộ nhớ trình duyệt vẫn được giữ trong RAM khi đổi chế độ. Lưu/khôi phục kho thật tạm khóa khi đang luyện. Lịch sử luyện lưu theo tài khoản trên trình duyệt hiện tại; chọn lùi qua lệnh đã biết kết quả bắt đầu phiên mới và giữ tóm tắt phiên trước. Replay có mục **Chi phí mô phỏng**: nhập spread theo đơn vị giá, trượt giá bất lợi mỗi lần khớp và phí khứ hồi theo R. Mặc định bằng 0 nên chưa phản ánh chi phí. Kết quả là mô phỏng, không phải kết quả giao dịch thực.
- **Công cụ không cần nguồn giá:** Fibonacci theo đỉnh/đáy tự nhập, R:R và bảng chuỗi thua vẫn dùng được khi chưa nối MT5. Các phép tính tiền, lot và ký quỹ vẫn cần thông số hợp đồng. SL/TP cùng phía giá vào, tỷ lệ thắng ngoài 0–100% hoặc số lệnh quá lớn sẽ được báo rõ.
- **Tình trạng giá và lưu:** không báo đang có tick trước tick đầu tiên; không tự kết luận thị trường đóng chỉ vì thiếu tick. Khi bộ nhớ nháp trình duyệt hỏng/đầy và chưa đồng bộ, giữ trang mở để tránh mất sửa đổi chưa được máy chủ nhận.

Đợt này không bật đặt lệnh thật, không gửi Telegram thử, không gọi AI trả phí và không biến webapp cục bộ thành dịch vụ SaaS công khai. Mở lại webapp để máy chủ nạp mã mới.


### Nhãn phân tích tinh gọn (27/11/2026)

Nút **Mức giá** cạnh tên phương án mở bảng điểm vào, SL, toàn bộ TP và số R, kèm kiểu vào và thời điểm nến tín hiệu. Giá dùng đúng số chữ số của mã đang xem. Bảng cập nhật theo phương án hiện tại, hiện lý do hết hiệu lực và báo khi thiếu mức giá; không cần kéo thang giá để đọc các mốc ngoài vùng zoom. Bảng mặc định đóng và tự đóng khi ẩn phân tích hoặc vào replay.

Phần hiển thị phân tích trên chart có lựa chọn **Nhãn phân tích → Tinh gọn / Chi tiết**. Mặc định Tinh gọn giữ thẻ giá điểm vào, SL và TP ở trục giá, dùng vùng màu nhẹ, giảm nhãn phụ và chỉ lấy FVG gần nhất mỗi phía. Tên phương pháp và trạng thái nằm trên chart, ngoài vùng nến. Chi tiết hiện lại các nhãn Vào/Ra, nhiều vùng bối cảnh và mục tiêu lý thuyết như trước. Lựa chọn được nhớ trên trình duyệt; không sửa mức giá, điều kiện hay số đo phương pháp. Khi ẩn phân tích hoặc phát lại, dải phương án hiện tại cũng được ẩn. Công cụ chọn mật độ dành cho lớp vẽ Lightweight Charts; khi thư viện không tải được và dùng canvas dự phòng, ô này tạm khóa.

### Chi phí replay và an toàn khôi phục (27/11/2026)

- Replay giả định OHLC là **Bid**, mua vào Ask và bán đóng Ask với spread cố định tự nhập. Không dùng trực tiếp giả định này cho nến Last của sàn giao dịch nếu chưa chuyển đổi dữ liệu phù hợp.
- Spread và trượt giá nhập bằng đơn vị giá, không tự hiểu là pip/point. Ví dụ giá 4.000,00 và spread 0,20 thì nhập 0,20. Trượt giá bất lợi áp dụng cho mỗi lần vào và ra, kể cả chốt lời trong mô hình thận trọng này.
- Phí khứ hồi (R/lệnh) = tổng hoa hồng cả lượt vào và ra / số tiền rủi ro ban đầu. Ví dụ phí tổng 1 USD và rủi ro 20 USD thì nhập 0,05R. Phí qua đêm không được mô phỏng riêng.
- Mỗi lệnh giữ một bản chụp chi phí; đang có lệnh thì khóa sửa chi phí. SL/TP tính từ giá vào sau spread/trượt giá. Spread cộng trượt giá phải nhỏ hơn khoảng SL. Gap được xét tại giá mở; khi không biết thứ tự chạm trong nến thì SL trước.
- Tổng R và số lệnh thắng tính sau chi phí đã nhập. Tóm tắt lưu mô hình, tổng R trước chi phí và tổng chi phí R; các phiên cũ ghi rõ trước phí. Lịch sử này lưu cục bộ theo tài khoản trình duyệt, chưa đồng bộ lịch sử luyện giữa thiết bị.
- Đây là mô hình chi phí cố định, không phải spread lịch sử, dữ liệu tick khớp lệnh hay bằng chứng phương pháp có lãi. Khi cả ba chi phí bằng 0, thanh replay cảnh báo ngay.
- Khôi phục bản vẽ tạm khóa sửa, hoàn tác và vào replay cho đến khi phản hồi hoàn tất; đóng hộp lịch sử không bỏ khóa. Lỗi mạng cũng giải phóng khóa. Phản hồi khác tài khoản không được áp dụng; sửa đổi vượt qua giao diện vẫn được giữ bằng xử lý xung đột.


## AI biểu đồ, API và gói khách hàng

Xem [hướng dẫn cấu hình AI quản trị](AI_BIEU_DO_HUONG_DAN.md) để đổi nhà cung cấp/model, lưu khóa API mã hóa, đặt lượt miễn phí và cấp gói. Bản giao diện mới kiểm tra riêng tại http://127.0.0.1:8766/bieu-do; phiên 8765 được giữ vì đang chạy vòng Telegram.

Kết nối bằng ứng dụng Claude Desktop/Codex hoặc host hỗ trợ MCP: xem [MCP và các gói AI đã đăng ký](MCP_KET_NOI_AI.md). Cài đặt có mục MCP dành riêng cho chủ, cấu hình client và khóa thu hồi được. MCP local chưa phải remote connector cho ChatGPT web hay backend gói đăng ký dùng chung cho khách hàng.

Tốc độ khi đổi mã/khung, chọn công cụ và chỉ báo: xem [cập nhật realtime biểu đồ](REALTIME_BIEU_DO.md). Chỉ báo dùng Worker; nguồn giá và chỉ số độ trễ đo được xem ở **Chất lượng realtime** trên trang Biểu đồ.
