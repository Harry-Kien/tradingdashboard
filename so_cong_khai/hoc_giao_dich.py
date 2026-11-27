"""Trang Học giao dịch (/hoc-giao-dich): Forex và CFD là gì, các lớp tài sản (kèm số đo trực tiếp của sàn: số mã, spread, biên độ),
khái niệm cốt lõi, các loại lệnh, 16 phong cách và phương pháp giao dịch, bài chọn phong cách hợp với mình, và nguyên tắc quản lý rủi ro.

Nội dung là kiến thức chung, viết trung lập: mỗi phong cách đều có phần nhược điểm và lỗi hay gặp, phong cách rủi ro cao (lưới, gấp thếp)
được ghi rõ. Mỗi phong cách trỏ tới công cụ trong webapp dùng được cho nó."""
from __future__ import annotations

from html import escape

from . import thi_truong_trang as TTT
from . import trang

LOP_TAI_SAN = [
    ('fx_chinh', 'Forex chính', 'Bảy cặp có USD với các đồng tiền lớn: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD.',
     'Thanh khoản lớn nhất thế giới, spread thấp nhất, chạy 24 giờ từ thứ Hai tới thứ Sáu. Giá chịu tác động của lãi suất ngân hàng trung ương, lạm phát, việc làm.',
     'Người mới, scalping, day trading, swing'),
    ('fx_cheo', 'Forex chéo', 'Cặp giữa hai đồng tiền lớn không có USD: EURJPY, GBPJPY, EURGBP, AUDNZD…',
     'Spread rộng hơn cặp chính một chút. Các cặp có JPY biến động mạnh; EURGBP, AUDNZD thường đi ngang nên hợp giao dịch vùng.',
     'Swing, giao dịch vùng, giao dịch theo sức mạnh tiền tệ'),
    ('fx_ngoai_lai', 'Forex ngoại lai', 'Đồng tiền lớn với tiền của nền kinh tế nhỏ hoặc mới nổi: USDZAR, USDSGD, USDHKD, USDCNH…',
     'Spread rộng, thanh khoản mỏng, có thể nhảy giá mạnh khi có tin chính trị. Một số đồng tiền neo tỷ giá (HKD).',
     'Người có kinh nghiệm, position trading'),
    ('kim_loai', 'Kim loại', 'Vàng (XAU) và bạc (XAG), giao dịch theo USD và theo các đồng tiền khác.',
     'Vàng là tài sản trú ẩn, nhạy với lãi suất thực của Mỹ, đồng USD và tin địa chính trị. Biến động mạnh trong phiên London và New York.',
     'Day trading, swing, theo tin'),
    ('nang_luong', 'Năng lượng', 'Dầu Brent và dầu WTI dạng CFD.',
     'Chịu tác động của OPEC+, tồn kho dầu Mỹ (thứ Tư hằng tuần), địa chính trị. Có thể gap mạnh đầu tuần.',
     'Swing, theo tin'),
    ('chi_so', 'Chỉ số chứng khoán', 'CFD trên chỉ số: Dow Jones, S&P 500, Nasdaq 100, DAX, FTSE 100, Nikkei 225, Hang Seng…',
     'Đi theo khẩu vị rủi ro và lợi nhuận doanh nghiệp. Có giờ giao dịch riêng của từng thị trường; giá được điều chỉnh khi cổ phiếu thành phần trả cổ tức.',
     'Day trading phiên Mỹ/châu Âu, swing, theo xu hướng'),
    ('crypto', 'Tiền mã hóa (CFD)', 'Bitcoin, Ethereum và các đồng lớn khác dạng CFD, giao dịch cả cuối tuần.',
     'Biến động rất mạnh, spread và ký quỹ cao hơn Forex, phí qua đêm thường cao. Bạn không sở hữu đồng tiền thật.',
     'Người chịu được biến động lớn, swing'),
]

KHAI_NIEM = [
    ('CFD là gì', 'CFD (hợp đồng chênh lệch) là hợp đồng giữa bạn và sàn: hai bên thanh toán phần chênh lệch giá từ lúc mở tới lúc đóng lệnh. '
     'Bạn không sở hữu tài sản gốc (không có vàng, cổ phiếu hay bitcoin thật), nhưng bán trước được dễ như mua, và chỉ cần ký quỹ một phần giá trị. '
     'Forex giao ngay ở các sàn bán lẻ thực chất cũng vận hành như CFD trên tỷ giá.'),
    ('Bid, Ask và spread', 'Bid là giá sàn mua của bạn (bạn bán ở Bid), Ask là giá sàn bán cho bạn (bạn mua ở Ask). Spread = Ask − Bid là chi phí bạn trả ngay khi mở lệnh: '
     'lệnh mua mở ra là đang lỗ đúng bằng spread. Spread giãn rộng lúc ra tin, lúc giao phiên cuối ngày và khi thị trường mỏng. Xem spread trực tiếp ở trang Thị trường.'),
    ('Lot và kích thước hợp đồng', '1 lot Forex = 100.000 đơn vị đồng tiền gốc; 0,1 lot (mini) = 10.000; 0,01 lot (micro) = 1.000. Với CFD, kích thước hợp đồng do sàn quy định: '
     'ví dụ 1 lot vàng thường là 100 ounce, 1 lot chỉ số có thể là 1 hoặc 10 lần giá trị chỉ số. Xem kích thước hợp đồng của từng mã ở thẻ Thông số hợp đồng.'),
    ('Pip và điểm', 'Pip là bước giá chuẩn của Forex: 0,0001 với phần lớn cặp, 0,01 với cặp có JPY. Sàn báo giá thêm một chữ số lẻ (pipette = 1/10 pip). '
     'CFD thường tính theo điểm (bước giá nhỏ nhất). Với EURUSD, 1 pip ở 1 lot = 10 USD; công cụ "Giá trị pip" tính cho mọi mã theo tỷ giá hiện tại.'),
    ('Đòn bẩy và ký quỹ', 'Đòn bẩy 1:100 nghĩa là bạn chỉ cần ký quỹ 1% giá trị lệnh. Đòn bẩy không đổi số tiền lãi lỗ trên mỗi pip; nó chỉ quyết định bạn mở được lệnh lớn tới đâu. '
     'Rủi ro nằm ở khối lượng so với vốn, không nằm ở con số đòn bẩy. Sàn có thể đặt mức ký quỹ riêng cho chỉ số, dầu, crypto.'),
    ('Mức ký quỹ, gọi ký quỹ và đóng lệnh bắt buộc', 'Mức ký quỹ = vốn hiện tại (equity) / ký quỹ đang dùng × 100%. Khi xuống tới mức gọi ký quỹ (margin call), sàn cảnh báo và có thể không cho mở thêm; '
     'tới mức dừng (stop out) sàn tự đóng lệnh lỗ nhất. Công cụ "Ký quỹ và mức an toàn" tính giá chạm các mức này.'),
    ('Phí qua đêm (swap)', 'Giữ lệnh qua 0 giờ giờ máy chủ thì bị trừ hoặc được cộng swap, theo chênh lệch lãi suất của hai đồng tiền và phí của sàn. Thường có một ngày tính gấp ba '
     '(bù cho cuối tuần, thường là thứ Tư với Forex). Với lệnh giữ nhiều tuần, swap có thể lớn hơn spread nhiều lần.'),
    ('Hoa hồng và trượt giá', 'Tài khoản ECN/raw có spread thấp nhưng thu hoa hồng mỗi lot. Trượt giá là chênh giữa giá bạn muốn và giá khớp thật, hay xảy ra lúc ra tin hoặc với lệnh dừng.'),
    ('Gap cuối tuần', 'Thị trường Forex đóng từ tối thứ Sáu tới tối Chủ nhật (giờ New York). Tin cuối tuần có thể khiến giá mở cửa cách xa giá đóng cửa: lệnh dừng lỗ khớp ở giá mở, '
     'xa hơn mức bạn đặt. Crypto CFD giao dịch cả cuối tuần nên không gap theo cách này.'),
    ('Giờ giao dịch', 'Forex chạy 24 giờ, chia bốn phiên Sydney, Tokyo, London, New York; đông nhất khi London và New York cùng mở (chiều tối giờ Việt Nam). '
     'Chỉ số và dầu có giờ nghỉ riêng mỗi ngày. Xem phiên đang mở ở trang Thị trường.'),
    ('CFD so với mua tài sản thật và hợp đồng tương lai', 'Mua thật: sở hữu tài sản, không đòn bẩy, không swap. Hợp đồng tương lai: giao dịch trên sàn tập trung, có ngày đáo hạn, khối lượng công khai. '
     'CFD: linh hoạt khối lượng nhỏ, không đáo hạn (với CFD giao ngay), nhưng sàn là bên đối ứng của bạn và có phí qua đêm.'),
]

LENH = [
    ('Lệnh thị trường (Market)', 'Mua ngay ở Ask hoặc bán ngay ở Bid.', 'Vào lệnh tức thì; có thể trượt giá khi thị trường nhanh.', 0, 'thi'),
    ('Buy Limit', 'Đặt mua ở mức THẤP hơn giá hiện tại.', 'Chờ giá hồi về vùng hỗ trợ rồi mua.', -1, 'mua'),
    ('Sell Limit', 'Đặt bán ở mức CAO hơn giá hiện tại.', 'Chờ giá hồi lên vùng kháng cự rồi bán.', 1, 'ban'),
    ('Buy Stop', 'Đặt mua ở mức CAO hơn giá hiện tại.', 'Mua khi giá phá vỡ lên trên một mức (giao dịch phá vỡ).', 1, 'mua'),
    ('Sell Stop', 'Đặt bán ở mức THẤP hơn giá hiện tại.', 'Bán khi giá phá vỡ xuống dưới một mức.', -1, 'ban'),
    ('Buy Stop Limit', 'Khi giá chạm mức dừng phía trên, MT5 đặt một lệnh Buy Limit ở mức thấp hơn đó.', 'Chờ phá vỡ rồi mua lại ở nhịp hồi về.', 1, 'mua'),
    ('Sell Stop Limit', 'Khi giá chạm mức dừng phía dưới, MT5 đặt một lệnh Sell Limit ở mức cao hơn đó.', 'Chờ phá vỡ xuống rồi bán ở nhịp hồi lên.', -1, 'ban'),
    ('Dừng lỗ (Stop Loss)', 'Mức tự đóng lệnh khi giá đi ngược.', 'Giới hạn số tiền mất ở mỗi lệnh. Nên đặt ngay khi vào lệnh.', -1, 'sl'),
    ('Chốt lời (Take Profit)', 'Mức tự đóng lệnh khi giá đi đúng hướng.', 'Khóa lợi nhuận ở mục tiêu định trước.', 1, 'tp'),
    ('Dừng lỗ dời theo (Trailing Stop)', 'Dừng lỗ tự dời theo giá khi lệnh có lãi, giữ một khoảng cách cố định.', 'Để lệnh thắng chạy dài mà vẫn khóa dần lợi nhuận. Trong MT5 chạy trên máy của bạn, tắt máy là ngừng dời.', -1, 'sl'),
]

PHONG_CACH = [
    {'id': 'scalp', 'ten': 'Scalping (lướt sóng siêu ngắn)', 'khung': 'M1–M5', 'giu': 'Vài giây tới vài phút', 'tg': 3, 'rr': 3, 'muc': 'phut',
     'mo_ta': 'Ăn những nhịp giá rất nhỏ, nhiều lệnh mỗi ngày, vào lúc thanh khoản cao nhất.',
     'hop': 'Cặp spread thấp (EURUSD, USDJPY), vàng trong giờ London–New York',
     'cach': ['Chỉ giao dịch lúc spread hẹp và phiên đông (giao thoa London–New York).', 'Đặt mục tiêu và dừng lỗ cố định, rất gần; thoát ngay khi sai.', 'Tính chi phí: spread và hoa hồng có thể ăn phần lớn lợi nhuận.'],
     'loi': 'Giao dịch lúc ra tin, khi spread giãn; gồng lỗ thay vì cắt; đánh quá nhiều lệnh vì cảm xúc.',
     'cc': [('Spread trực tiếp', '/thi-truong#bang-gia'), ('Phiên giao dịch', '/thi-truong#phien'), ('Biểu đồ M1–M5', '/bieu-do')]},
    {'id': 'day', 'ten': 'Day trading (giao dịch trong ngày)', 'khung': 'M5–H1', 'giu': 'Vài phút tới vài giờ, đóng trong ngày', 'tg': 3, 'rr': 2, 'muc': 'ngay',
     'mo_ta': 'Mở và đóng lệnh trong cùng ngày, không chịu swap và rủi ro gap qua đêm.',
     'hop': 'Forex chính, vàng, chỉ số Mỹ và châu Âu',
     'cach': ['Xác định xu hướng khung lớn (H4, D1) trước, chỉ vào theo hướng đó ở khung nhỏ.', 'Dùng biên độ trung bình ngày (ADR) để biết giá còn đi được bao xa.', 'Tránh 15 phút quanh tin mạnh.'],
     'loi': 'Vào lệnh khi giá đã đi hết biên độ ngày; giao dịch quá nhiều trong phiên vắng.',
     'cc': [('Phân tích điểm vào', '/bieu-do'), ('Biên độ và ADR', '/thi-truong#bang-gia'), ('Lịch tin', '/thi-truong#phien'), ('Pivot hôm nay', '/cong-cu')]},
    {'id': 'swing', 'ten': 'Swing trading (giao dịch sóng)', 'khung': 'H1–D1', 'giu': '2–10 ngày', 'tg': 2, 'rr': 2, 'muc': 'tuan',
     'mo_ta': 'Bắt một con sóng giá kéo dài vài ngày, vào ở nhịp hồi trong xu hướng.',
     'hop': 'Forex chính và chéo, vàng, chỉ số',
     'cach': ['Tìm cặp có đồng tiền mạnh ghép với đồng tiền yếu trên khung tuần.', 'Vào ở vùng hồi Fibonacci 38,2–61,8% hoặc hỗ trợ cũ.', 'Dừng lỗ ngoài đỉnh/đáy sóng trước; tính trước swap nếu giữ lâu.'],
     'loi': 'Dừng lỗ quá gần nên bị quét bởi dao động trong ngày; quên swap và gap cuối tuần.',
     'cc': [('Sức mạnh tiền tệ', '/thi-truong#suc-manh'), ('Fibonacci', '/cong-cu'), ('Thông số swap', '/thi-truong#thong-so')]},
    {'id': 'position', 'ten': 'Position trading (giữ vị thế dài)', 'khung': 'D1–W1', 'giu': 'Vài tuần tới vài tháng', 'tg': 1, 'rr': 2, 'muc': 'thang',
     'mo_ta': 'Theo các xu hướng lớn do chu kỳ lãi suất và kinh tế vĩ mô, ít quan tâm dao động ngắn.',
     'hop': 'Forex chính, vàng, chỉ số',
     'cach': ['Theo dõi xu hướng lãi suất của các ngân hàng trung ương và vị thế COT.', 'Khối lượng nhỏ, dừng lỗ rộng theo khung tuần.', 'Đánh giá lại khi có quyết định lãi suất.'],
     'loi': 'Dùng khối lượng của day trading cho dừng lỗ rộng; bỏ qua chi phí swap tích lũy.',
     'cc': [('COT vàng trên biểu đồ', '/bieu-do'), ('Thay đổi theo tháng', '/thi-truong#ban-do-nhiet'), ('Ký quỹ và mức an toàn', '/cong-cu')]},
    {'id': 'trend', 'ten': 'Theo xu hướng (trend following)', 'khung': 'H1–D1', 'giu': 'Tới khi xu hướng gãy', 'tg': 2, 'rr': 2, 'muc': 'tuan',
     'mo_ta': 'Mua khi giá tạo đỉnh đáy cao dần, bán khi thấp dần; để lệnh thắng chạy dài.',
     'hop': 'Mã có xu hướng rõ: vàng, chỉ số, cặp có JPY',
     'cach': ['Xác nhận xu hướng bằng EMA20/EMA50 hoặc cấu trúc đỉnh đáy trên nhiều khung.', 'Vào ở nhịp hồi hoặc khi phá đỉnh mới.', 'Dùng dừng lỗ dời theo; chấp nhận tỷ lệ thắng thấp (30–45%).'],
     'loi': 'Chốt lời quá sớm nên lệnh thắng không bù được lệnh thua; vào khi thị trường đi ngang.',
     'cc': [('Xu hướng D1/H4/H1', '/'), ('Biểu đồ EMA', '/bieu-do'), ('R:R và kỳ vọng', '/cong-cu')]},
    {'id': 'range', 'ten': 'Giao dịch vùng / hồi về trung bình', 'khung': 'M15–H4', 'giu': 'Vài giờ tới vài ngày', 'tg': 2, 'rr': 2, 'muc': 'ngay',
     'mo_ta': 'Khi giá đi ngang, mua gần hỗ trợ và bán gần kháng cự, chờ giá về giữa vùng.',
     'hop': 'Cặp hay đi ngang: EURGBP, AUDNZD, EURCHF; phiên Á',
     'cach': ['Chỉ dùng khi không có xu hướng (EMA phẳng, giá chạm hai biên nhiều lần).', 'Vào gần biên với RSI quá mua/quá bán hoặc dải Bollinger.', 'Dừng lỗ ngay ngoài biên; thoát khi vùng bị phá.'],
     'loi': 'Tiếp tục bắt đỉnh đáy khi giá đã phá vùng và vào xu hướng mới.',
     'cc': [('Pivot và hỗ trợ/kháng cự', '/cong-cu'), ('Tương quan', '/thi-truong#tuong-quan')]},
    {'id': 'breakout', 'ten': 'Phá vỡ (breakout)', 'khung': 'M15–H4', 'giu': 'Vài giờ tới vài ngày', 'tg': 2, 'rr': 2, 'muc': 'ngay',
     'mo_ta': 'Vào lệnh khi giá thoát khỏi vùng tích lũy, đặc biệt lúc phiên lớn mở cửa.',
     'hop': 'Vàng, GBP, chỉ số lúc mở phiên London và New York',
     'cach': ['Đánh dấu vùng tích lũy (ví dụ phiên Á).', 'Đặt Buy Stop / Sell Stop ngoài vùng hoặc chờ nến đóng ngoài vùng.', 'Dừng lỗ ở giữa hoặc phía bên kia vùng.'],
     'loi': 'Phá vỡ giả rất nhiều; vào lệnh khi biên độ ngày đã cạn.',
     'cc': [('Phiên giao dịch', '/thi-truong#phien'), ('% ADR đã đi', '/thi-truong#bang-gia')]},
    {'id': 'news', 'ten': 'Giao dịch theo tin', 'khung': 'M1–M15', 'giu': 'Vài phút tới vài giờ', 'tg': 2, 'rr': 3, 'muc': 'phut',
     'mo_ta': 'Tận dụng biến động mạnh quanh tin như bảng lương phi nông nghiệp (NFP), lạm phát CPI, quyết định lãi suất FOMC.',
     'hop': 'USD, vàng, chỉ số Mỹ',
     'cach': ['Biết trước giờ ra tin và mức dự báo.', 'Thường chờ 5–15 phút sau tin để spread hẹp lại và hướng rõ hơn.', 'Giảm khối lượng vì trượt giá lớn.'],
     'loi': 'Đặt lệnh chờ hai phía ngay trước tin rồi bị khớp cả hai do giật giá; không tính spread giãn.',
     'cc': [('Lịch tin kinh tế', '/thi-truong#phien'), ('Cảnh báo trước tin', '/bieu-do')]},
    {'id': 'carry', 'ten': 'Carry trade (ăn chênh lệch lãi suất)', 'khung': 'D1–W1', 'giu': 'Vài tuần tới vài tháng', 'tg': 1, 'rr': 3, 'muc': 'thang',
     'mo_ta': 'Mua đồng tiền lãi suất cao, bán đồng tiền lãi suất thấp để nhận swap dương mỗi đêm.',
     'hop': 'Cặp có chênh lệch lãi suất lớn (ví dụ đồng lãi suất cao với JPY)',
     'cach': ['Xem swap mua/bán của từng cặp ở thẻ Thông số hợp đồng.', 'Chỉ giữ khi xu hướng giá cùng chiều với swap.', 'Khối lượng nhỏ: một đợt tháo chạy khỏi rủi ro có thể xóa nhiều tháng tiền swap trong vài ngày.'],
     'loi': 'Bỏ qua rủi ro tỷ giá; dùng đòn bẩy cao vì "lệnh tự sinh lãi". Lưu ý: tài khoản demo này đang tắt swap.',
     'cc': [('Swap từng mã', '/thi-truong#thong-so')]},
    {'id': 'pa', 'ten': 'Price Action (hành động giá)', 'khung': 'M15–D1', 'giu': 'Tùy khung', 'tg': 2, 'rr': 2, 'muc': 'ngay',
     'mo_ta': 'Đọc trực tiếp nến và cấu trúc giá (pin bar, nến nhấn chìm, đỉnh đáy) thay vì chỉ báo.',
     'hop': 'Mọi mã có thanh khoản tốt',
     'cach': ['Xác định vùng giá quan trọng trước.', 'Chờ mẫu nến từ chối tại vùng đó.', 'Dừng lỗ sau râu nến tín hiệu.'],
     'loi': 'Thấy mẫu nến ở mọi nơi, kể cả giữa vùng giá không có ý nghĩa.',
     'cc': [('Phương pháp Price Action', '/bieu-do'), ('Kiến thức', '/kien-thuc')]},
    {'id': 'smc', 'ten': 'SMC / ICT (dòng tiền lớn)', 'khung': 'M5–H4', 'giu': 'Vài giờ tới vài ngày', 'tg': 3, 'rr': 2, 'muc': 'ngay',
     'mo_ta': 'Theo dấu thanh khoản: quét đỉnh đáy, khoảng trống giá (FVG), khối lệnh, phá cấu trúc (BOS/CHoCH).',
     'hop': 'Vàng, Forex chính, chỉ số',
     'cach': ['Đánh dấu thanh khoản trên/dưới và vùng premium/discount.', 'Chờ giá quét thanh khoản rồi phá cấu trúc ngược lại.', 'Vào ở khoảng trống giá, dừng lỗ sau điểm quét.'],
     'loi': 'Gọi tên mọi thứ sau khi giá đã chạy; không đo kết quả. Trang Biểu đồ có số đo lại thật cho ICT trên từng mã.',
     'cc': [('Bản đồ ICT/SMC', '/bieu-do'), ('Nhật ký điểm vào', '/nhat-ky')]},
    {'id': 'elliott', 'ten': 'Sóng Elliott và Fibonacci', 'khung': 'H1–D1', 'giu': 'Vài ngày', 'tg': 2, 'rr': 2, 'muc': 'tuan',
     'mo_ta': 'Đếm sóng đẩy 1-2-3-4-5 và sóng điều chỉnh, dùng tỷ lệ Fibonacci để đoán điểm kết thúc sóng.',
     'hop': 'Mã có xu hướng rõ',
     'cach': ['Tìm sóng 1 mạnh và sóng 2 hồi 38,2–78,6%.', 'Vào khi giá vượt đỉnh sóng 1 (bắt đầu sóng 3).', 'Mục tiêu 1,618 lần sóng 1.'],
     'loi': 'Đếm lại sóng mỗi khi sai; có nhiều cách đếm hợp lệ cùng lúc.',
     'cc': [('Sóng Elliott trên biểu đồ', '/bieu-do'), ('Máy tính Fibonacci', '/cong-cu')]},
    {'id': 'algo', 'ten': 'Giao dịch thuật toán (EA, bot)', 'khung': 'Mọi khung', 'giu': 'Theo luật', 'tg': 1, 'rr': 2, 'muc': 'tuan',
     'mo_ta': 'Viết luật thành chương trình (EA trên MT5) để vào ra lệnh tự động, không cảm xúc.',
     'hop': 'Mọi mã có dữ liệu lịch sử tốt',
     'cach': ['Viết luật rõ ràng và đo trên dữ liệu nhiều năm, có tính spread và trượt giá.', 'Kiểm ngoài mẫu (dữ liệu chưa dùng để chọn tham số).', 'Chạy demo đủ lâu, ghi sổ công khai trước khi dùng tiền thật.'],
     'loi': 'Tối ưu quá khớp quá khứ (overfitting); tin vào backtest không có chi phí.',
     'cc': [('Sổ công khai', '/'), ('Nhật ký điểm vào', '/nhat-ky'), ('Tài khoản MT5', '/tai-khoan')]},
    {'id': 'hedge', 'ten': 'Phân tán và phòng hộ theo tương quan', 'khung': 'H1–D1', 'giu': 'Tùy chiến lược', 'tg': 1, 'rr': 1, 'muc': 'tuan',
     'mo_ta': 'Dùng tương quan để không dồn rủi ro vào một hướng, hoặc mở lệnh ngược ở mã tương quan để giảm rủi ro.',
     'hop': 'Danh mục nhiều lệnh',
     'cach': ['Kiểm tra tương quan trước khi mở lệnh thứ hai.', 'Coi hai lệnh cùng chiều trên hai mã tương quan cao là một lệnh lớn.', 'Phòng hộ có chi phí: spread hai lần và swap.'],
     'loi': 'Mua EURUSD, GBPUSD, AUDUSD cùng lúc và nghĩ là đã phân tán.',
     'cc': [('Ma trận tương quan', '/thi-truong#tuong-quan')]},
    {'id': 'grid', 'ten': 'Lưới và gấp thếp (grid, martingale)', 'khung': 'Mọi khung', 'giu': 'Tới khi cả lưới có lãi', 'tg': 1, 'rr': 3, 'muc': 'tuan', 'canh_bao': True,
     'mo_ta': 'Đặt nhiều lệnh cách đều nhau, hoặc nhân khối lượng sau mỗi lệnh thua để gỡ một lần.',
     'hop': 'Không khuyến khích',
     'cach': ['Hiểu để nhận ra: đường vốn đẹp và đều rồi mất gần hết trong một lần.', 'Rủi ro thật nằm ở chuỗi đi một chiều dài mà vốn không chịu được.', 'Nếu thấy EA hay tín hiệu "thắng 95%", hỏi sụt vốn lớn nhất và khối lượng lớn nhất từng mở.'],
     'loi': 'Đánh giá bằng tỷ lệ thắng; không có dừng lỗ tổng cho cả lưới.',
     'cc': [('Sụt vốn và chuỗi thua', '/cong-cu')]},
    {'id': 'copy', 'ten': 'Copy trade và theo tín hiệu', 'khung': 'Theo người dẫn', 'giu': 'Theo người dẫn', 'tg': 1, 'rr': 2, 'muc': 'tuan',
     'mo_ta': 'Sao chép lệnh của người khác hoặc vào lệnh theo tín hiệu được gửi.',
     'hop': 'Người ít thời gian, nhưng cần biết cách kiểm người dẫn',
     'cach': ['Chỉ theo nguồn có sổ đầy đủ: mọi lệnh kể cả lệnh thua, đủ dài (hơn 100 lệnh, nhiều tháng).', 'Xem sụt vốn lớn nhất và khối lượng so với vốn, không chỉ lợi nhuận.', 'Dùng khối lượng của mình theo % rủi ro của mình.'],
     'loi': 'Chọn theo lợi nhuận tháng gần nhất; nguồn khoe lệnh thắng, giấu lệnh thua.',
     'cc': [('Nhật ký điểm vào', '/nhat-ky'), ('Khối lượng theo rủi ro', '/cong-cu')]},
]

QUY_TAC = [
    ('Rủi ro mỗi lệnh 0,5–2% vốn', 'Ở 1%, chuỗi 10 lệnh thua liên tiếp còn để lại khoảng 90% vốn; ở 10% thì chỉ còn khoảng 35%.'),
    ('Luôn có dừng lỗ trước khi vào', 'Quyết định mức chấp nhận sai lúc còn tỉnh táo, không phải lúc đang lỗ.'),
    ('Tính khối lượng từ dừng lỗ, không ngược lại', 'Khoảng dừng lỗ do thị trường quyết định; khối lượng là thứ bạn điều chỉnh.'),
    ('Biết tỷ lệ thắng hòa vốn của kế hoạch', 'Với R:R 1:2, bạn cần thắng trên 33% (chưa tính phí) mới có lãi.'),
    ('Đừng cộng dồn rủi ro qua các mã tương quan', 'Mua EURUSD và GBPUSD cùng lúc gần như là một lệnh gấp đôi.'),
    ('Giới hạn lỗ theo ngày và tuần', 'Ví dụ dừng giao dịch trong ngày khi đã mất 3% vốn.'),
    ('Ghi sổ mọi lệnh', 'Chỉ con số từ sổ đầy đủ mới cho biết phương pháp có lợi thế hay không.'),
]


def _so_do_lenh(huong: int, loai: str) -> str:
    """Hình nhỏ: vạch giá hiện tại và vạch lệnh (trên hoặc dưới)."""
    mau = {'mua': 'var(--gain)', 'ban': 'var(--loss)', 'sl': 'var(--loss)', 'tp': 'var(--gain)', 'thi': 'var(--series)'}[loai]
    y = 36 if huong == 0 else (14 if huong > 0 else 58)
    ten = {'mua': 'Lệnh mua', 'ban': 'Lệnh bán', 'sl': 'Dừng lỗ', 'tp': 'Chốt lời', 'thi': 'Khớp ngay'}[loai]
    return ('<svg viewBox="0 0 150 72" class="sdl" aria-hidden="true"><line x1="6" y1="36" x2="144" y2="36" stroke="var(--mute)" stroke-dasharray="4 3"/>'
            '<text x="8" y="32" font-size="10" fill="var(--mute)">Giá hiện tại</text>'
            + (f'<line x1="6" y1="{y}" x2="144" y2="{y}" stroke="{mau}" stroke-width="2"/><text x="8" y="{y - 4 if huong > 0 else y + 12}" font-size="10" fill="{mau}">{ten}</text>'
               if huong else f'<circle cx="110" cy="36" r="5" fill="{mau}"/><text x="88" y="54" font-size="10" fill="{mau}">{ten}</text>') + '</svg>')


def _cham(n: int, toi: int = 3) -> str:
    return '<span class="cham3">' + ''.join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(toi)) + '</span>'


CSS = r"""
.hg-nav{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 0}.hg-nav a{font-size:12.5px;color:var(--ink2);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:5px 12px;background:var(--card)}
.hg-nav a:hover{color:var(--series);border-color:var(--series)}
.hg h2{margin:28px 0 4px;font-size:20px}.hg>section>p.sub{margin:0 0 12px;color:var(--ink2);max-width:860px}
.hg-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:12px}
.hg-c{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.hg-c h3{margin:0;font-size:15px;color:var(--head);text-transform:none;letter-spacing:0}.hg-c p{margin:0;font-size:13px;color:var(--ink2)}
.hg-c .so{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mute);border-top:1px solid var(--line);padding-top:8px;margin-top:auto}.hg-c .so b{color:var(--ink);font-weight:600}
.hg-c a.mo{font-size:12px;color:var(--series);text-decoration:none;display:inline-block;padding:5px 0}
.kn details{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:0 0 8px;padding:0 16px}.kn summary{font-size:14px;text-transform:none;letter-spacing:0;color:var(--ink);padding:12px 0}
.kn details p{margin:0 0 12px;color:var(--ink2);font-size:13.5px;max-width:900px}
.sdl{width:150px;height:72px;display:block;margin:4px 0}
.pc{position:relative}.pc.canh{border-color:color-mix(in srgb,var(--loss) 45%,var(--line))}
.pc .tt{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:12.5px;color:var(--ink2)}.pc .tt b{color:var(--mute);font-weight:500}
.pc ol{margin:4px 0 0;padding-left:18px;font-size:13px;color:var(--ink2)}.pc ol li{margin:2px 0}
.pc .loi{font-size:12.5px;color:var(--warn)}.pc .cc{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
.pc .cc a{font-size:12px;color:var(--ink2);text-decoration:none;border:1px solid var(--line);border-radius:8px;padding:3px 8px}.pc .cc a:hover{color:var(--series);border-color:var(--series)}
.pc.hl{box-shadow:0 0 0 2px var(--series)}
.cham3{display:inline-flex;gap:3px;vertical-align:1px}.cham3 i{width:7px;height:7px;border-radius:50%;background:var(--track)}.cham3 i.on{background:var(--warn)}
.quiz{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.quiz fieldset{border:0;padding:0;margin:0 0 14px}.quiz legend{font-weight:600;margin-bottom:6px;color:var(--ink)}
.quiz .sg button{min-height:34px}
.kqz{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px}
.kqz a{display:block;text-decoration:none;color:inherit;background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:12px}
.kqz a:hover{border-color:var(--series)}.kqz b{display:block;font-size:14px}.kqz small{color:var(--ink2);font-size:12.5px}.kqz em{font-style:normal;color:var(--series);font-weight:700;font-size:12px}
.qt{counter-reset:q;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));gap:10px}
.qt div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px 12px 46px;position:relative}
.qt div::before{counter-increment:q;content:counter(q);position:absolute;left:14px;top:12px;width:22px;height:22px;border-radius:50%;background:color-mix(in srgb,var(--series) 18%,transparent);color:var(--series);font-weight:700;font-size:12px;display:grid;place-items:center}
.qt b{display:block;font-size:13.5px}.qt span{font-size:12.5px;color:var(--ink2)}
.gs{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:grid;gap:10px;grid-template-columns:minmax(0,1fr)}
.gs>*{min-width:0}.gs .hang{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.gs select{min-height:36px;max-width:100%;flex:1 1 260px}
.gs .log{display:grid;gap:8px;max-height:560px;overflow:auto;padding:2px}.gs .log:empty{display:none}
.gs .m{border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:14px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}
.gs .m.ai{background:var(--card2)}.gs .m.ban{border-color:color-mix(in srgb,var(--series) 45%,var(--line));margin-left:auto;max-width:88%}
.gs .m pre{margin:6px 0;padding:8px 10px;background:var(--bg);border-radius:8px;overflow-x:auto;white-space:pre;font-size:12.5px;line-height:1.35}
.gs textarea{width:100%;min-height:72px;resize:vertical;padding:8px 10px;font:inherit;box-sizing:border-box}
.gs .lenh button{min-height:30px;font-size:12.5px}.gs .tt{font-size:12.5px;color:var(--mute)}.gs .bao{font-size:13px;color:var(--warn);min-height:1em}
.gs .gsl summary{cursor:pointer;font-size:13px;color:var(--ink2)}.gs .gsl .b{border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin:6px 0;display:grid;gap:4px}
.gs .gsl .b pre{margin:0;font-size:11.5px;line-height:1.3;overflow-x:auto}.gs .gsl .b small{color:var(--mute)}
.pc .gsb{font-size:12px;color:var(--series);background:none;border:1px solid color-mix(in srgb,var(--series) 40%,var(--line));border-radius:8px;padding:3px 8px;cursor:pointer}.gsb,.gs .hang button,#gs-bd{min-height:30px}
"""

JS = r"""
(()=>{const T=TT,$=s=>document.querySelector(s),esc=T.esc,fmt=T.fmt;
const tv=a=>{const v=a.filter(x=>x!=null&&isFinite(x)).sort((p,q)=>p-q);return v.length?v[Math.floor(v.length/2)]:null};
T.on(l=>{if(l!=='anh')return;const g={};for(const x of T.by().values())(g[x.lop]=g[x.lop]||[]).push(x);
 document.querySelectorAll('[data-lop]').forEach(el=>{const ds=g[el.dataset.lop]||[];if(!ds.length){el.innerHTML='<span>Sàn của bạn chưa có mã nào thuộc nhóm này.</span>';return}
  const fx=el.dataset.lop.startsWith('fx'),sp=tv(ds.map(x=>{const s=T.spread(x);return s&&s.v})),spp=tv(ds.map(x=>x.q?(x.q[1]-x.q[0])/x.q[0]*100:null)),adr=tv(ds.map(x=>x.adr&&x.q?x.adr/x.q[0]*100:null));
  el.innerHTML=`<span><b>${ds.length}</b> mã ở sàn của bạn</span><span>spread trung vị <b>${fx?fmt(sp,1)+' pip':fmt(spp,3)+'%'}</b></span><span>biên độ ngày TB <b>${fmt(adr,2)}%</b></span>`})});
// ---- chọn phong cách
const PC=JSON.parse(document.getElementById('pc-data').textContent),tl={};
document.querySelectorAll('.quiz .sg').forEach(g=>g.addEventListener('click',e=>{const b=e.target.closest('button[data-v]');if(!b)return;tl[g.dataset.q]=b.dataset.v;g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));chon()}));
function chon(){if(Object.keys(tl).length<4){$('#kqz').innerHTML='<p class="small">Trả lời đủ 4 câu để xem gợi ý.</p>';return}
 const muc={phut:0,ngay:1,tuan:2,thang:3},giu={phut:0,ngay:1,tuan:2,thang:3}[tl.giu],tg={it:1,vua:2,nhieu:3}[tl.tg];
 const kq=PC.filter(p=>!p.canh_bao).map(p=>{let s=0,ly=[];const d=Math.abs(muc[p.muc]-giu);s+=3-d*1.5;if(d===0)ly.push('đúng thời gian giữ lệnh bạn muốn');
  if(p.tg<=tg){s+=1.5;if(p.tg<tg)ly.push('không đòi nhiều thời gian hơn bạn có')}else s-=2.5*(p.tg-tg);
  if(tl.rr==='thap'&&p.rr>=3)s-=2.5;if(tl.rr==='thap'&&p.rr<=1){s+=1;ly.push('rủi ro thấp')}if(tl.rr==='cao'&&p.rr>=2)s+=.5;
  const ks={bieu_do:['scalp','day','swing','pa','smc','elliott','breakout','range','trend'],vi_mo:['position','carry','news','swing'],luat:['algo','trend','hedge','copy']}[tl.kieu]||[];
  if(ks.includes(p.id)){s+=2;ly.push(tl.kieu==='bieu_do'?'dựa vào biểu đồ':tl.kieu==='vi_mo'?'dựa vào tin và vĩ mô':'theo luật cố định')}
  return{p,s,ly}}).sort((a,b)=>b.s-a.s).slice(0,3);
 $('#kqz').innerHTML='<div class="kqz">'+kq.map((k,i)=>`<a href="#pc-${k.p.id}" data-id="${k.p.id}"><em>Hợp ${['nhất','thứ hai','thứ ba'][i]}</em><b>${esc(k.p.ten)}</b><small>${esc(k.ly.slice(0,2).join(', ')||'cân bằng với các lựa chọn của bạn')}. Khung ${esc(k.p.khung)}, giữ ${esc(k.p.giu.toLowerCase())}.</small></a>`).join('')+'</div><p class="small">Gợi ý theo câu trả lời, không phải lời khuyên. Thử phong cách nào cũng nên bắt đầu bằng tài khoản demo và ghi sổ.</p>';
 $('#kqz').querySelectorAll('a[data-id]').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('.pc.hl').forEach(x=>x.classList.remove('hl'));const c=document.getElementById('pc-'+a.dataset.id);if(c)c.classList.add('hl')}))}
chon();T.batDau(120)})();

// ---- gia sư (kỹ năng socratic-tutor của Jane Street, giấy phép MIT)
(()=>{const $=s=>document.querySelector(s),e=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const box=$('#gs');if(!box)return;let phien=null,dang=false;const sel=$('#gs-cd'),log=$('#gs-log'),o=$('#gs-o'),bao=$('#gs-bao');
const nho=v=>{try{v?localStorage.setItem('gs_phien',JSON.stringify(v)):localStorage.removeItem('gs_phien')}catch(_){}},doc=()=>{try{return JSON.parse(localStorage.getItem('gs_phien')||'null')}catch(_){return null}};
const ve=t=>e(t).replace(/```[a-z]*\n?([\s\S]*?)```/g,(m,c)=>'<pre>'+c.replace(/\n$/,'')+'</pre>').replace(/\*\*([^*\n]+)\*\*/g,'<b>$1</b>');
const them=(ai,t)=>{const d=document.createElement('div');d.className='m '+(ai?'ai':'ban');d.innerHTML=ai?ve(t):e(t);log.appendChild(d);log.scrollTop=log.scrollHeight};
const usd=x=>String((+x||0).toFixed(2)).replace('.',',');
const ds=b=>{const w=$('#gs-ds-w');if(!b||!b.length){w.hidden=true;return}w.hidden=false;$('#gs-ds').innerHTML=b.map(x=>`<div class="b"><b>${e(x.ten)}</b><small>${x.luot} lượt · ${usd(x.usd)} USD · ${x.luc?new Date(x.luc).toLocaleString('vi-VN'):''}</small>${x.ban_do?'<pre>'+e(x.ban_do)+'</pre>':''}<div><button type="button" class="ghost" data-tiep="${e(x.phien)}">Học tiếp</button></div></div>`).join('');w.querySelectorAll('[data-tiep]').forEach(b=>b.onclick=()=>tiep(b.dataset.tiep))};
const tiep=id=>fetch('/api/gia-su?phien='+encodeURIComponent(id),{cache:'no-store'}).then(r=>r.ok?r.json():null).then(b=>{if(!b||!b.hien){bao.textContent='Không mở được buổi học này.';return}phien=b.phien;sel.value=b.chu_de;log.innerHTML='';b.hien.forEach(m=>them(m.ai,m.chu_gs));nho({phien,chu_de:b.chu_de});bao.textContent='Đang học tiếp: '+b.ten+'.';box.scrollIntoView({block:'start'})});
const tt=s=>{if(s&&s.buoi)ds(s.buoi);$('#gs-tt').textContent=s?`Hôm nay đã dùng ${s.hom_nay}/${s.moi_ngay} lượt · đã tiêu ${String(s.da_tieu_usd.toFixed(2)).replace('.',',')}/${String(s.ngan_sach_usd.toFixed(2)).replace('.',',')} USD`+(s.chan&&s.chan.length?' · '+s.chan.join(' '):''):''};
fetch('/api/gia-su',{cache:'no-store'}).then(r=>r.json()).then(s=>{const g={};for(const c of s.chu_de)(g[c.nhom]=g[c.nhom]||[]).push(c);
 sel.innerHTML=Object.entries(g).map(([n,l])=>`<optgroup label="${e(n)}">`+l.map(c=>`<option value="${e(c.id)}">${e(c.ten)}</option>`).join('')+'</optgroup>').join('');tt(s);const c=doc();if(c&&c.phien&&(s.buoi||[]).some(x=>x.phien===c.phien))tiep(c.phien)}).catch(()=>{bao.textContent='Không đọc được trạng thái gia sư.'});
const gui=cau=>{if(dang)return;dang=true;bao.textContent='Gia sư đang soạn câu hỏi…';box.querySelectorAll('button').forEach(b=>b.disabled=true);
 let song=null,chu='';const xong=j=>{if(j.phien){phien=j.phien;nho({phien,chu_de:sel.value})}if(j.trang_thai)tt(j.trang_thai);if(!j.ok){if(song)song.remove();bao.textContent=j.ly_do||'Chưa hỏi được.';return}bao.textContent='';if(song)song.innerHTML=ve(j.tra_loi);else them(true,j.tra_loi);o.focus()};
 fetch('/api/gia-su',{method:'POST',headers:{'Content-Type':'application/json','X-So-Cong-Khai':'1'},body:JSON.stringify({phien,chu_de:sel.value,cau,luong:1})})
 .then(async r=>{if(!r.body||!(r.headers.get('content-type')||'').includes('event-stream')){xong(await r.json());return}
  const rd=r.body.getReader(),td=new TextDecoder();let dem='',ket=null;
  for(;;){const{value,done}=await rd.read();if(done)break;dem+=td.decode(value,{stream:true});let i;
   while((i=dem.indexOf('\n\n'))>=0){const dong=dem.slice(0,i);dem=dem.slice(i+2);if(!dong.startsWith('data: '))continue;const ev=JSON.parse(dong.slice(6));
    if(ev.xong){ket=ev;continue}chu+=ev.chu||'';if(!song){song=document.createElement('div');song.className='m ai';log.appendChild(song);bao.textContent=''}
    song.innerHTML=ve(chu);log.scrollTop=log.scrollHeight}}
  xong(ket||{ok:false,ly_do:'Mất kết nối giữa chừng; gửi lại câu trả lời.'})})
 .catch(()=>{if(song)song.remove();bao.textContent='Không nối được với webapp.'}).finally(()=>{dang=false;box.querySelectorAll('button').forEach(b=>b.disabled=false)})};
$('#gs-bd').onclick=()=>{phien=null;log.innerHTML='';gui('')};
$('#gs-gui').onclick=()=>{const t=o.value.trim();if(!t)return;if(!phien){bao.textContent='Bấm "Bắt đầu học" trước.';return}them(false,t);o.value='';gui(t)};
o.addEventListener('keydown',ev=>{if(ev.key==='Enter'&&(ev.ctrlKey||ev.metaKey)){ev.preventDefault();$('#gs-gui').click()}});
box.querySelectorAll('[data-lenh]').forEach(b=>b.onclick=()=>{if(!phien){bao.textContent='Bấm "Bắt đầu học" trước.';return}them(false,b.dataset.lenh);gui(b.dataset.lenh)});
document.querySelectorAll('.gsb[data-cd]').forEach(b=>b.onclick=()=>{sel.value=b.dataset.cd;box.scrollIntoView({behavior:'smooth',block:'start'});bao.textContent='Đã chọn chủ đề; bấm "Bắt đầu học".'});
})();
"""


def trang_hoc(ten: str) -> str:
    import json
    lop = ''.join(f'<article class="hg-c"><h3>{escape(t)}</h3><p>{escape(a)}</p><p>{escape(b)}</p><p><b style="color:var(--mute);font-weight:500">Hợp với:</b> {escape(c)}</p>'
                  f'<div class="so" data-lop="{k}"><span>Đang đọc số liệu của sàn…</span></div><a class="mo" href="/thi-truong#bang-gia">Xem bảng giá →</a></article>'
                  for k, t, a, b, c in LOP_TAI_SAN)
    kn = ''.join(f'<details><summary>{escape(t)}</summary><p>{escape(n)}</p></details>' for t, n in KHAI_NIEM)
    lenh = ''.join(f'<article class="hg-c"><h3>{escape(t)}</h3>{_so_do_lenh(h, l)}<p>{escape(a)}</p><p>{escape(b)}</p></article>' for t, a, b, h, l in LENH)
    pc = ''.join(
        f'<article class="hg-c pc{" canh" if p.get("canh_bao") else ""}" id="pc-{p["id"]}"><h3>{escape(p["ten"])}</h3><p>{escape(p["mo_ta"])}</p>'
        f'<div class="tt"><b>Khung</b><span>{escape(p["khung"])}</span><b>Giữ lệnh</b><span>{escape(p["giu"])}</span>'
        f'<b>Thời gian cần</b><span>{_cham(p["tg"])}</span><b>Rủi ro</b><span>{_cham(p["rr"])}</span><b>Hợp với</b><span>{escape(p["hop"])}</span></div>'
        '<ol>' + ''.join(f'<li>{escape(c)}</li>' for c in p['cach']) + '</ol>'
        f'<p class="loi"><b>Lỗi hay gặp:</b> {escape(p["loi"])}</p>'
        '<div class="cc">' + ''.join(f'<a href="{h}">{escape(n)}</a>' for n, h in p['cc'])
        + f'<button type="button" class="gsb" data-cd="{p["id"]}">Học với gia sư</button></div></article>' for p in PHONG_CACH)
    q = [('tg', 'Mỗi ngày bạn có bao nhiêu thời gian nhìn thị trường?', [('it', 'Dưới 1 giờ'), ('vua', '1–3 giờ'), ('nhieu', 'Trên 3 giờ')]),
         ('giu', 'Bạn muốn giữ một lệnh trong bao lâu?', [('phut', 'Vài phút'), ('ngay', 'Trong ngày'), ('tuan', 'Vài ngày'), ('thang', 'Vài tuần trở lên')]),
         ('rr', 'Bạn chịu được biến động và chuỗi thua tới đâu?', [('thap', 'Muốn an toàn'), ('vua', 'Vừa phải'), ('cao', 'Chịu được biến động lớn')]),
         ('kieu', 'Bạn thích ra quyết định dựa trên gì?', [('bieu_do', 'Biểu đồ và mẫu giá'), ('vi_mo', 'Tin tức, lãi suất, vĩ mô'), ('luat', 'Luật cố định, tự động')])]
    quiz = ''.join(f'<fieldset><legend>{escape(c)}</legend><div class="sg" data-q="{k}">'
                   + ''.join(f'<button type="button" data-v="{v}" aria-pressed="false">{escape(n)}</button>' for v, n in ds) + '</div></fieldset>' for k, c, ds in q)
    qt = ''.join(f'<div><b>{escape(t)}</b><span>{escape(n)}</span></div>' for t, n in QUY_TAC)
    data = json.dumps([{k: p[k] for k in ('id', 'ten', 'khung', 'giu', 'tg', 'rr', 'muc')} | {'canh_bao': bool(p.get('canh_bao'))} for p in PHONG_CACH],
                      ensure_ascii=False).replace('</', '<\\/')
    gs = ('<section id="gia-su"><h2>Gia sư giao dịch</h2><p class="sub">Chọn một chủ đề; gia sư hỏi từng câu để biết bạn đang ở đâu, rồi dạy bằng câu hỏi '
          'cho tới khi bạn tự làm được. Trả lời sai thì gia sư không đọc đáp án mà hỏi hẹp lại. Gia sư chỉ dạy kiến thức, không đưa tín hiệu hay lời khuyên đầu tư.</p>'
          '<div class="gs" id="gs"><div class="hang"><select id="gs-cd" aria-label="Chủ đề"></select><button type="button" id="gs-bd">Bắt đầu học</button></div>'
          '<div class="log" id="gs-log" aria-live="polite"></div>'
          '<textarea id="gs-o" placeholder="Câu trả lời của bạn (Ctrl+Enter để gửi)" maxlength="1500" aria-label="Câu trả lời"></textarea>'
          '<div class="hang lenh"><button type="button" id="gs-gui">Gửi</button>'
          '<button type="button" class="ghost" data-lenh="xem tiến độ">Xem tiến độ</button><button type="button" class="ghost" data-lenh="khó hơn">Khó hơn</button>'
          '<button type="button" class="ghost" data-lenh="dễ hơn">Dễ hơn</button><button type="button" class="ghost" data-lenh="nói luôn đáp án">Nói luôn đáp án</button>'
          '</div>'
          '<div class="bao" id="gs-bao" role="status"></div><div class="tt" id="gs-tt"></div>'
          '<div class="tt">Cách dạy theo kỹ năng socratic-tutor của Jane Street (giấy phép MIT). Mỗi câu trả lời dùng khóa API Anthropic của máy này và tốn '
          'vài xu. Buổi học được tự lưu trên máy này: tắt webapp rồi mở lại vẫn học tiếp được.</div>'
          '<details class="gsl" id="gs-ds-w" hidden><summary>Các buổi học gần đây</summary><div id="gs-ds"></div></details></div></section>')
    muc = ''.join(f'<a href="#{k}">{n}</a>' for k, n in (('gia-su', 'Gia sư'), ('lop', 'Các lớp tài sản'), ('khai-niem', 'Khái niệm cốt lõi'), ('lenh', 'Các loại lệnh'),
                                                         ('chon', 'Chọn phong cách'), ('phong-cach', '16 phong cách giao dịch'), ('rui-ro', 'Quản lý rủi ro')))
    return '\n'.join([
        '<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        f'{trang.KHOI_TAO_NEN}{trang.BIEU_TUONG}<title>Học giao dịch · {escape(ten)}</title><style>{trang.CSS}{TTT.CSS}{CSS}</style></head><body>',
        trang.thanh_dau(ten, 'hoc', '<button id="theme" type="button">Nền tối</button>') + '<main class="rong hg">',
        '<div class="tt-top"><div><h1>Học giao dịch Forex &amp; CFD</h1><p>Từ khái niệm cơ bản tới các phong cách giao dịch, mỗi phần kèm công cụ trong webapp '
        'để thực hành ngay với giá trực tiếp của sàn.</p></div></div>',
        f'<nav class="hg-nav">{muc}</nav>',
        '<p class="note"><b>Rủi ro:</b> CFD và Forex dùng đòn bẩy nên có thể mất tiền rất nhanh; phần lớn tài khoản cá nhân giao dịch CFD bị lỗ. '
        'Trang này là kiến thức chung, không phải lời khuyên đầu tư. Hãy luyện trên tài khoản demo trước.</p>',
        gs,
        f'<section id="lop"><h2>Các lớp tài sản</h2><p class="sub">Số liệu dưới mỗi thẻ lấy trực tiếp từ sàn trong MT5 của bạn.</p><div class="hg-g">{lop}</div></section>',
        f'<section id="khai-niem" class="kn"><h2>Khái niệm cốt lõi</h2><p class="sub">Bấm từng mục để mở.</p>{kn}</section>',
        f'<section id="lenh"><h2>Các loại lệnh trong MT5</h2><p class="sub">Lệnh chờ đặt trên hay dưới giá hiện tại quyết định nó là Limit hay Stop.</p><div class="hg-g">{lenh}</div></section>',
        f'<section id="chon"><h2>Phong cách nào hợp với bạn?</h2><p class="sub">Bốn câu hỏi, gợi ý ba phong cách gần nhất với cách bạn muốn giao dịch.</p>'
        f'<div class="quiz">{quiz}<div id="kqz"></div></div></section>',
        f'<section id="phong-cach"><h2>16 phong cách và phương pháp giao dịch</h2><p class="sub">Mỗi phong cách có cách làm cơ bản, lỗi hay gặp và công cụ trong webapp dùng được. '
        f'Thời gian và rủi ro chấm từ 1 tới 3 chấm.</p><div class="hg-g">{pc}</div></section>',
        f'<section id="rui-ro"><h2>Quản lý rủi ro: 7 nguyên tắc</h2><p class="sub">Phương pháp quyết định bạn vào lệnh ở đâu; quản lý rủi ro quyết định bạn còn ở lại thị trường bao lâu. '
        f'<a href="/cong-cu">Mở công cụ tính khối lượng →</a></p><div class="qt">{qt}</div></section>',
        f'<script type="application/json" id="pc-data">{data}</script>',
        '<footer>' + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script><script>{TTT.JS_CHUNG}</script><script>{JS}</script></body></html>'])
