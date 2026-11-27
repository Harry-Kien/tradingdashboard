# Cập nhật biểu đồ khi chọn mã, khung, công cụ và chỉ báo

## Hành vi đã cải thiện

- Đổi mã/khung sẽ hủy lượt tải cũ, đóng luồng tick cũ và tăng số phiên chọn biểu đồ. Phản hồi muộn của lần chọn trước không được áp dụng, kể cả chuỗi A → B → A hoặc H1 → M5 → H1.
- Callback tick đã nằm trong hàng đợi của một kết nối SSE bị đóng cũng không được áp lại vào kết nối mới của cùng mã/khung.
- Trong lúc đổi biểu đồ, lớp trạng thái che dữ liệu cũ và công cụ/AI không được đọc dữ liệu đó như dữ liệu mã mới. Không dùng nến cache làm giá trực tiếp hoặc kế hoạch lệnh hiện tại.
- Công cụ đang vẽ dở được hủy khi đổi mã/khung. Chọn công cụ, chỉnh tham số và bật/tắt chỉ báo vẫn cập nhật trên trình duyệt.
- Chỉ báo tùy chỉnh tính trong **Web Worker**, sử dụng chính công thức đang được kiểm đối chiếu với pandas. Tính toán nặng không chạy trên luồng thao tác chính khi Worker hoạt động.
- Chỉ giữ một tác vụ Worker đang chạy và đánh dấu dữ liệu mới cần tính tiếp. Kết quả của mã, khung hoặc cấu hình chỉ báo trước đó bị bỏ. Khi đổi cấu hình, Worker cũ được kết thúc.
- Các cập nhật thông thường chỉ gửi phần đuôi kết quả để vẽ; ZigZag, Fractals và RSI phân kỳ vẫn nạp đầy đủ vì có thể sửa dấu trong quá khứ. Đổi lịch sử/nguồn nến cũng tính lại đầy đủ.
- Mã so sánh có một luồng tick riêng khi đang chọn. Đổi/bỏ mã so sánh hoặc ẩn tab sẽ đóng luồng; không đưa dữ liệu so sánh realtime vào Bar Replay.
- **Chất lượng realtime** hiển thị thời gian JavaScript nhận tick → cập nhật nến, P95 và tình trạng Worker/phép tính chỉ báo gần nhất. Đây không phải độ trễ sàn → màn hình hay độ trễ suy luận AI.

## Giới hạn thực tế

- Webapp thu thập một lần cho mỗi cặp mã và khung đang có người xem. Cùng một cặp dùng chung giá và nến hiện tại qua SSE. Mỗi bản chạy có tối đa 128 cặp và 256 kết nối giá. Khi đóng kết nối cuối, webapp thu hồi cặp đó sau khi phát hiện ngắt.
- Máy phục vụ đẩy bản trạng thái mới nhất để vẽ, có thể bỏ qua các trạng thái trung gian khi mạng chậm. Lịch sử nến do MT5 cung cấp. Khi luồng bị gián đoạn, biểu đồ lấy lại lịch sử để bổ sung nến đã đóng. Luồng này không phải kho lưu tất cả tick.
- Giữ riêng số đo đầu vào và số đo trình duyệt. `/api/song/tinh-trang` trên máy có số người xem, số cặp, số lần đọc, số gói đã phát và số cặp thiếu dữ liệu. Đây là bộ đếm từ lúc tiến trình mở.
- Cài đặt → Kết nối MT5 → Danh mục mã của broker hiển thị cả mã đang ẩn. Chủ tài khoản chọn mã và thêm vào Market Watch, sau đó mở lại trang Biểu đồ. Thao tác đăng ký báo giá không đặt lệnh.
- Có thể dùng chế độ kết nối độc lập bằng `gia.mt5.noi = "doc_lap"` trong cấu hình. Gói chia sẻ đi kèm cấu hình mẫu và thư viện vẽ. Mã nguồn và giấy phép thư viện được ghi trong `tinh/NGUON.md`. Báo giá vẫn lấy từ terminal MT5 đã đăng nhập vào broker.

Realtime phụ thuộc tick từ MT5, trạng thái kết nối, máy tính và trình duyệt. Không có tick mới thì hệ thống không tạo giá giả. Nến đang chạy và chỉ báo trên nến đó có thể thay đổi; tín hiệu xác nhận cần nến đóng. Web Worker giữ công thức đầy đủ, không biến một phép tính nặng thành tức thời. Trình duyệt không hỗ trợ Worker hoặc Worker lỗi sẽ dùng luồng dự phòng.

Không có chỉ báo luôn tốt nhất cho mọi thị trường/khung. Nâng cấp này cải thiện tốc độ và tính nhất quán của các chỉ báo bạn chọn; không tự thay chiến lược hoặc bảo đảm hiệu quả giao dịch.

## Kiểm tra

- `tests/test_chart_request_worker.py` chạy gate, loader, callback SSE và công thức Worker thật trong Node, kiểm phản hồi muộn và toàn bộ thư viện chỉ báo giữa full/tail.
- `tests/test_phan_tich_realtime_js.py` kiểm kết quả phân tích muộn không lọt vào lần chọn biểu đồ mới.
- `D:\TRADER DEVELOPER\out\chart_realtime_smoke.py` kiểm trong Chromium thật: mã/khung A-B-A, tick cũ, 500 tick, EMA chính xác, đổi chu kỳ EMA, chọn công cụ, mã so sánh và màn hình máy tính/điện thoại.
- Ảnh và báo cáo trình duyệt ở `D:\TRADER DEVELOPER\out\realtime-review`.

Trong thử nghiệm tổng hợp, P95 nhận tick → cập nhật nến khoảng 10 ms trên máy này. Đây là kết quả thử nghiệm cục bộ có dữ liệu giả, không phải cam kết tốc độ thị trường thực tế. Bộ kiểm thử tổng thể và kiểm tra MT5 thật được ghi riêng trong báo cáo nghiệm thu.

## Quan sát M5, M15 và M30

- Ô **Cảnh báo** của biểu đồ quét mã đang xem trên cả ba khung. Chỉ báo tìm phá đỉnh/đáy 12 nến hoặc hồi về EMA20 theo hướng EMA20/50 của khung đang xét và H1 đã đóng. Mỗi khung chỉ ra một kết quả cho mỗi nến. Các khung cùng mã, chiều và thời điểm đóng được gộp khi thông báo.
- Điểm tham chiếu dùng Ask cho MUA, Bid cho BÁN. Webapp lọc theo spread, độ lệch khỏi giá xác nhận, thời điểm tick và khoảng SL. Hạn quan sát là hai phút sau nến xác nhận. Khi lịch tin có mốc phù hợp, tạm dừng trong 15 phút trước và sau tin USD mạnh. Nếu lịch chưa được xác nhận, ô Cảnh báo ghi rõ.
- Khi tab đang mở, tín hiệu mới của mã đang xem có thể hiện thông báo. Muốn theo dõi ở nền khi máy chủ chạy, mở **Cài đặt → Cá nhân**, bật vòng cảnh báo rồi bật **Báo tín hiệu M5, M15, M30**. Có thể nhập tối đa 8 mã bổ sung đã hiện trong Market Watch. Phiên web xem trước có ô quan sát trực tiếp và thông báo trong tab.
- `python -X utf8 cong-cu/kiem_tin_hieu_ngan.py` chạy mô phỏng hồi cứu XAUUSD đến nến M1 cuối có sẵn. Phép so so sánh cùng bộ lọc với và không có nhánh hồi EMA, tính spread, phí và trượt giá giả định. Cả ba khung vẫn có kỳ vọng âm trên toàn kỳ 2015–2026. Các phép lọc H4, D1 và phiên giao dịch khảo sát riêng cũng âm trên toàn kỳ. Dùng các tín hiệu cho nghiên cứu và quan sát.

### Kết quả sau khi tín hiệu xuất hiện

- Trong ô **Cảnh báo**, mở **Kết quả tiến cứu** để xem từng khung và loại thiết lập của mã đang mở. Chỉ dùng tín hiệu do vòng nền ghi lúc còn hiệu lực. Báo cáo không trộn máy chủ broker, mã hoặc phiên bản công thức. Có thể có nhiều tín hiệu chồng nhau, vì thống kê đo mỗi kịch bản riêng.
- Giá tham chiếu và SL/TP được giữ cố định. Khi chấm, lệnh mua thoát theo Bid, lệnh bán theo Ask; dừng lỗ nhảy giá lấy quote bất lợi, chốt lời lấy mức mục tiêu. Nếu hết 12 nến kể từ nến xác nhận, lấy quote đầu tiên sau hạn nếu đủ dữ liệu. Spread đã nằm trong Bid/Ask, cộng một bước trượt giá giả định và hoa hồng khứ hồi từ **Cài đặt**. Mẫu có khoảng trống tick trên hai phút, hoặc thiếu thông tin quy đổi phí, hiện riêng và không tính vào tỷ lệ thắng hay R ròng.
- Bản chính ghi khi **Vòng canh cảnh báo**, **Báo tín hiệu M5, M15, M30** và **Ghi và chấm tín hiệu quan sát** đang bật. Bản xem thử có thể chạy `python -X utf8 -m so_cong_khai.web_preview --port 8779 --tien-cuu`. Tùy chọn này chỉ bật bộ ghi tín hiệu cùng webapp ở máy hiện tại. Sổ nằm trong `tin-hieu-tien-cuu.sqlite3` ở thư mục kết quả, và bản sao lưu thông thường chụp nhất quán tệp SQLite nếu tệp nằm trong thư mục dự án.
