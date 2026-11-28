# MCP và các gói AI đã đăng ký

MCP cung cấp **dữ liệu và công cụ**, để AI trong ứng dụng đã kết nối phân tích. Luồng này không gọi API sinh câu trả lời của website. Model, quota, tốc độ suy luận và quyền sử dụng vẫn do ứng dụng AI/tài khoản đó quyết định.

Website tự trả lời khách hàng tiếp tục dùng API hoặc tích hợp thương mại được nhà cung cấp hỗ trợ. Gói cá nhân không tự trở thành backend dùng chung qua MCP. Không dùng mật khẩu, cookie hay session token của ChatGPT/Claude làm API key.

## Đã bổ sung

- Cài đặt MCP chỉ dành cho chủ: bật/tắt, chọn cổng và tạo lại khóa cục bộ.
- Khóa MCP riêng, lưu mã hóa, không đưa vào cấu hình plugin/trình duyệt. Tắt MCP hoặc đổi khóa sẽ chặn client cũ.
- Stdio MCP, không mở listener public và không tạo tunnel.
- `phan_tich_realtime`: snapshot MT5 mới, đúng mã/khung, nến đa khung, EMA/RSI/ATR, đồng thuận và kịch bản entry/SL/TP do code tính.
- `doc_realtime`: đọc lại cùng snapshot; `anh_realtime`: PNG từ chính nến đó. Ảnh không chụp desktop, tài khoản hoặc bản vẽ cá nhân đang mở.
- Snapshot hết hiệu lực bị từ chối. Công cụ bằng chứng cũ cũng kiểm tra tuổi snapshot.
- 13 công cụ đọc/tính, 1 prompt có bằng chứng và 1 tài nguyên hướng dẫn. Không có công cụ đặt/sửa/đóng lệnh, shell, SQL hoặc đọc tệp tùy ý.
- Nguồn plugin local ở `integrations/harry-market-mcp`. Chưa tự cài vào tài khoản AI nào.

## Dùng tại máy này

1. Mở [Cài đặt MCP](http://127.0.0.1:8769/cai-dat#mcp-admin), đăng nhập tài khoản chủ `kien`.
2. Bật MCP, chọn cổng `8769` của bản local chuẩn và lưu. Các bản xem thử ở cổng cũ đã được hợp nhất.
3. Claude Desktop: ghép mục `mcpServers` hiển thị vào cấu hình của ứng dụng, giữ các server khác; nạp lại kết nối theo hướng dẫn của Claude.
4. Codex: ghép khối `[mcp_servers.harry_market]` hiển thị vào cấu hình; nạp lại kết nối theo phiên bản đang dùng.
5. Trong AI, chọn prompt `phan_tich_chuyen_gia` hoặc hỏi: “Dùng Harry Market MCP phân tích XAUUSDp M15. Lấy snapshot mới, đối chiếu đa khung và ảnh nến; chỉ dùng entry/SL/TP tham chiếu đã tính; nêu xác nhận, vô hiệu, rủi ro và lý do đứng ngoài nếu có.”

Gói đăng ký không bảo đảm host gọi tool mỗi tick. MCP ở đây là dữ liệu theo yêu cầu: mỗi phân tích có thời điểm; không phải mô hình liên tục nhìn màn hình. Theo dõi liên tục cần bộ điều phối, ngân sách/giới hạn và cơ chế cập nhật riêng.

## Khả năng từng nền tảng

| Nền tảng | Cách kết nối | Giới hạn |
|---|---|---|
| Claude Desktop | Stdio cục bộ | Cần nạp lại và cho phép tool. Quota nằm trong Claude. |
| Codex | Stdio cục bộ | Model/quota của host vẫn áp dụng. Plugin local không tự có trên web/mobile. |
| Claude web / remote connectors | Remote MCP HTTPS công khai phù hợp | Kết nối từ hạ tầng Claude; localhost của máy bạn không phải endpoint remote. Chưa triển khai. |
| ChatGPT web | Remote MCP hoặc Secure MCP Tunnel được hỗ trợ, với quyền tài khoản/workspace phù hợp | Không dùng trực tiếp stdio. Phải kiểm tra quyền đúng gói/workspace. |
| Gemini và host khác | Phụ thuộc host hỗ trợ stdio/remote MCP | Có gói trả phí không đồng nghĩa hỗ trợ mọi connector. Chưa xác minh đăng nhập hoặc hoạt động trong các host này. |

Tài liệu chính thức đối chiếu ngày 27/11/2026:

- [ChatGPT custom MCP servers](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).
- [OpenAI: thanh toán ChatGPT và API](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform). Hai hệ thanh toán tách biệt; gói đủ điều kiện có thể có ưu đãi API credit, không có nghĩa quota vô hạn.
- [Claude remote MCP](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).
- [MCP local setup](https://modelcontextprotocol.io/docs/develop/connect-local-servers).
- [MCP prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts), [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

## Trước khi bán qua website

MCP local dành cho chủ máy, có thể đọc phiếu và thông tin rủi ro của chủ qua các công cụ cũ. Không phân phối khóa/thư mục dữ liệu cho khách hàng. Remote cần OAuth riêng từng khách, phạm vi dữ liệu và gói tương ứng, chống lạm dụng, nhật ký truy cập, HTTPS, giới hạn yêu cầu và nguồn thị trường phù hợp. Cần xác minh điều kiện thương mại theo hình thức triển khai.

Mục tiêu chất lượng là phân tích có bằng chứng, biết khi nào không nên giao dịch, và đo hiệu quả sau chi phí bằng kiểm định ngoài mẫu/tiến cứu. MCP không tự nâng độ chính xác, không huấn luyện AI và không bảo đảm thu nhập hoặc kết quả như chuyên gia. Tin kinh tế, crypto spot độc lập và thanh toán tự động chưa được bổ sung trong nâng cấp này.
