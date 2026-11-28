# AI biểu đồ và cấu hình quản trị

Kết quả nghiên cứu ngày 28/11/2026: đã replay bộ miễn phí trên 4,19 triệu nến M1 vàng và đánh giá lại mô hình xếp hạng theo năm, chỉ học quá khứ. Hai biến thể xác nhận entry mới chưa qua cổng kiểm định lợi nhuận/chi phí; chưa đưa vào bản sử dụng. Xem báo cáo [Backtest AI](out/ai-backtest-20261128/BAO_CAO_AI_BACKTEST.md). Đây là kết quả của bộ quy tắc và mô hình logistic, không phải backtest Claude API.

Bản làm việc chính: `D:\TRADER DEVELOPER\so-cong-khai`. Bản local thống nhất chạy ở [Biểu đồ](http://127.0.0.1:8769/bieu-do) và [Cài đặt AI](http://127.0.0.1:8769/cai-dat#ai-admin). Các tác vụ nền dùng cùng tiến trình; không mở thêm bản xem thử để sử dụng hằng ngày.

## Sử dụng ngay

1. Đăng nhập tài khoản biểu đồ **kien**, tài khoản chủ hiện có. Không tạo lại tài khoản chủ và không thay mật khẩu.
2. Trên chart mở **AI đọc chỉ báo → Miễn phí · Bộ quy tắc đa khung → Phân tích miễn phí**. Bộ này đọc EMA20/50/200, RSI14 và ATR14 SMA từ nến MT5 đã đóng, không cần API key, không trừ lượt AI API và không gửi dữ liệu ra ngoài. Đây là quy tắc lập trình, chưa phải mô hình được huấn luyện riêng.
3. Khi muốn dùng mô hình API, mở **Cài đặt → AI · Nhà cung cấp và gói sử dụng**, chọn nền tảng và model trong danh sách đã duyệt. Dán khóa API và chọn **Lưu khóa mã hóa**, hoặc đặt biến môi trường của nền tảng.
4. Dùng **Kiểm tra kết nối / model** để xác minh khóa và danh sách model. Thao tác này không sinh câu trả lời.
5. Trong bảng **AI đọc chỉ báo**, chọn **AI API · Đọc chỉ báo, ảnh và câu hỏi**, sau đó chọn chế độ phù hợp. Tùy chọn **Kèm ảnh biểu đồ đang xem** gửi ảnh nến và lớp vẽ, không chụp toàn màn hình hay ô tài khoản. Chỉ gửi API khi bấm nút phân tích.
6. **Bằng chứng / Phiếu** giữ bốn chế độ giải thích cũ, mỗi nhận xét có mã bằng chứng. Phiếu kế hoạch cũ hiện là dữ liệu của chủ hệ thống; chỉ chủ được giải thích rủi ro/review những phiếu này.

Bản cài local chỉ cho tài khoản chủ phân tích dữ liệu MT5 của bản cài đó. Tài khoản khác không được dùng MT5 của chủ như dữ liệu của mình. Bộ miễn phí hiển thị điều kiện đạt/chưa đạt và bảng chỉ báo làm căn cứ; thiếu dữ liệu hoặc các khung chưa đồng thuận thì đứng ngoài. Ngày giờ kết quả dùng UTC+7, giá hiển thị theo độ chính xác của mã. Kết quả quá hạn, đổi biểu đồ, giá dịch chuyển quá xa hoặc chạm mức vô hiệu sẽ không còn được dùng để vẽ mức tham chiếu. Các bộ phân tích này không đặt lệnh.

## Cấu hình đã áp dụng

| Mục | Giá trị |
|---|---|
| Nhà cung cấp mặc định | Anthropic |
| Model mặc định | `claude-opus-5-5` |
| Suy luận | high |
| Khóa | Dùng `ANTHROPIC_API_KEY` hiện có; đã kiểm tra API chấp nhận và thấy model trong danh sách |
| Đọc ảnh | Cho phép, khách hàng chủ động bật mỗi lượt |
| Miễn phí | 5 câu hỏi trọn đời/tài khoản, chủ được sửa |
| Giới hạn ngày | 5 lượt thành công/tài khoản, giữ mức cấu hình trước |
| Ngân sách | 5 USD/ngày và 5 USD/tháng UTC, giữ giới hạn thận trọng từ cấu hình trước |
| Gói mặc định | Pro: 200 lượt/tháng, 299.000đ; Premium: 600 lượt/tháng, 699.000đ; đều sửa được |

Giá gói là giá niêm yết mẫu để chủ hệ thống điều chỉnh, không phải giá đã nghiên cứu thị trường. Gói chỉ được kích hoạt khi chủ chọn tài khoản, gói và ngày hết hạn. Thanh toán tự động chưa được kết nối. Gói hết hạn trở về hạn mức miễn phí còn lại. Gia hạn không đặt lại số lượt đã dùng trong tháng.

## Cách hệ thống phân tích

Máy chủ đọc đúng mã và khung đang xem, Bid/Ask, thời gian tick, nến đã đóng và H1/H4/D1 từ MT5. AI chỉ nhận dữ liệu còn mới; mã phải được MT5 xác nhận thuộc forex hoặc CFD (bao gồm crypto CFD). Hiện chưa có nguồn crypto spot độc lập.

Máy chủ tính EMA20/50/200, RSI14, ATR14, đỉnh/đáy và các kịch bản phá vỡ/hồi về EMA. Mức entry/SL/TP và R:R do code tính trước; AI chỉ chọn ID kịch bản và diễn giải. Các chỉ báo người dùng bật được gửi thêm nhưng được đánh dấu là dữ liệu từ trình duyệt, chưa được xác minh. Chỉ báo và ảnh không được dùng như chỉ dẫn để thay đổi prompt nền.

Phản hồi phải qua kiểm tra JSON, ID kịch bản, chiều SL/TP và R:R. Máy chủ đọc lại giá sau khi AI trả lời. Nếu giá dịch chuyển quá xa hoặc ảnh chụp hết hiệu lực, kết quả được ghi rõ đã cũ và không cho vẽ như tín hiệu hiện tại. Lớp giá AI tự bỏ khi hết hạn, đổi mã/khung hoặc chạm SL/TP. Tất cả kịch bản đều có điều kiện xác nhận; không có thao tác đặt lệnh.

AI phân tích theo lần bấm, không suy luận lại ở mỗi tick. Nến vẫn cập nhật theo tick. Dịch vụ AI có độ trễ mạng và suy luận; không thể cam kết câu trả lời tức thời hoặc chính xác tuyệt đối. Nếu model trả lời chậm hơn thời gian hiệu lực, cần lấy ảnh chụp mới. Tin kinh tế chưa được tích hợp vào luồng phân tích mới; hệ thống ghi rõ đây là dữ liệu thiếu.

## Bảo vệ khóa, lượt hỏi và chi phí

- Mọi API đổi cấu hình, khóa, cấp gói và kiểm tra nhà cung cấp đều kiểm cookie tài khoản chủ ở máy chủ; không tin ID hoặc gói do trình duyệt tự gửi.
- Khóa lưu bằng Fernet. Trên Windows, master key được DPAPI bảo vệ theo tài khoản Windows. Trên hosting, cung cấp `HGR_AI_MASTER_KEY` qua secret manager hoặc dùng khóa API từ biến môi trường. Không đưa khóa vào JavaScript, localStorage hay cấu hình công khai.
- Các địa chỉ API là HTTPS cố định. Không cho khách hàng nhập endpoint tùy ý; chặn redirect để tránh gửi khóa nhầm nơi.
- Sổ SQLite giữ chỗ ngân sách và lượt hỏi trong giao dịch nguyên tử. Tối đa 3 lượt xử lý chung, 1 lượt đang chạy/tài khoản, cách nhau tối thiểu 5 giây. ID yêu cầu ngăn gọi API lặp.
- Lượt lỗi/JSON sai được hoàn số câu hỏi. API có thể vẫn tính phí; phần ngân sách giữ chỗ được giữ để đối soát khi không biết chắc chi phí. Khi tiến trình bị gián đoạn, sau 180 giây hoàn lượt cho khách và không gửi lại cùng ID.
- Ngày tính theo giờ Việt Nam; hạn mức gói/tháng và ngân sách tháng tính theo tháng UTC. Hạn mức miễn phí tính trọn đời, không đặt lại khi tải trang hay đăng nhập lại.
- Chi phí là dự toán theo đơn giá chủ nhập, không phải hóa đơn chính thức. Đặt đơn giá dự toán đủ bao gồm cache, suy luận và ảnh; đồng thời đặt trần chi trên dashboard của nhà cung cấp.
- Sao lưu SQLite dùng API backup nhất quán. Các tệp `*-secret.json` bị loại khỏi bản ZIP; khi phục hồi phải cấp lại khóa/master key phù hợp. Không chép kho Windows DPAPI sang máy khác rồi kỳ vọng giải mã được.

## Nhà cung cấp

Hỗ trợ OpenAI Responses API, Anthropic Messages API, Gemini qua giao thức OpenAI, DeepSeek Chat Completions. Có adapter cho Mistral và xAI, model do chủ tài khoản tự thêm và duyệt. Không tự đổi sang model khác khi lỗi. Danh sách gợi ý có thể thay đổi theo nhà cung cấp; dùng nút kiểm tra trước khi chọn model mới.

Claude Code là công cụ lập trình, không phải một nhà cung cấp model riêng cho khách hàng website; ở đây dùng Claude API.

Tài liệu giao thức đã đối chiếu:

- [OpenAI Responses](https://developers.openai.com/api/reference/resources/responses/methods/create), [danh sách model](https://developers.openai.com/api/docs/models).
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages), [danh sách model](https://platform.claude.com/docs/en/models/overview).
- [Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai).
- [DeepSeek API](https://api-docs.deepseek.com/).

## Phần cần làm trước khi bán công khai

Đây là nền tảng phân tích và quản trị dùng cho webapp cục bộ; chưa phải hệ thống SaaS đã sẵn sàng phát hành công khai. Server hiện chủ động chỉ nhận loopback. Không bỏ kiểm Host/Origin để đưa thẳng Python http.server ra Internet.

Triển khai thương mại cần một đích hosting cụ thể, HTTPS/cookie Secure, lớp xác thực dùng cho public (xác minh email, phục hồi mật khẩu, chống tạo tài khoản hàng loạt), phân quyền toàn bộ dữ liệu ngoài AI, cô lập phiếu/nhật ký/tài khoản MT5 theo khách hàng, cổng thanh toán và webhook xác minh chữ ký, chính sách hoàn tiền, giám sát vận hành và nguồn dữ liệu MT5 từ xa. Không cấp gói dựa vào giá hoặc trạng thái thanh toán do trình duyệt gửi. Hạn mức miễn phí hiện bảo vệ theo tài khoản, chưa chống được một người tạo nhiều tài khoản trên website công khai.

Chưa huấn luyện/fine-tune model riêng, chưa chứng minh hiệu quả giao dịch và chưa có mô hình quantum. Để bổ sung ML có ý nghĩa cần dữ liệu có quyền sử dụng, nhãn kết quả sau spread/slippage, tách tập theo thời gian, walk-forward, so với baseline và chạy thử trước khi mở cho khách hàng. Không thể suy ra hệ thống tốt hơn TradingView hoặc có lợi nhuận từ số lượng kỹ thuật AI được gắn tên.

## Kiểm tra và tệp chính

Chạy `python -X utf8 -m unittest discover -s tests` và `python -m ruff check so_cong_khai tests`. Kiểm tra trình duyệt độc lập ở `D:\TRADER DEVELOPER\out\ai_ui_smoke.py`, ảnh kiểm tra ở `D:\TRADER DEVELOPER\out\ai-review`.

Luồng mới ở `ai_chart.py`, `ai_evidence.py`, `ai_providers.py`, `ai_store.py`, `ai_ui.py`; các luồng AI cũ trên HTTP đã chuyển qua hạn mức mới. Gia sư cũ chỉ dành cho chủ hệ thống để không tạo đường vượt hạn mức khách hàng. Chưa thực hiện lượt sinh câu trả lời có phí trong phiên nâng cấp này; adapter được kiểm bằng phản hồi giả, khóa/model Anthropic được kiểm qua list-models, dữ liệu MT5 được kiểm trực tiếp.
