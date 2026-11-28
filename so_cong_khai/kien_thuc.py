"""Trang Kiến thức: giải thích từng chỉ báo, luật và chỉ số đang dùng trong webapp, kèm con số của chính hệ thống này.
Số liệu lấy từ tài liệu và báo cáo trong EA Promax và Tele dự báo, đọc tới 20/11/2026; khi luật đổi thì phải sửa lại ở đây."""
from __future__ import annotations

import re

import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from . import duong, trang

# (nhóm, [(thuật ngữ, nghĩa là gì, trong hệ thống của bạn)])
MUC = [
    ('Đọc biểu đồ', [
        ('Nến đã đóng và nến đang chạy',
         'Một cây nến chỉ có giá mở, cao, thấp, đóng cố định sau khi hết khung thời gian của nó. Trước lúc đó nó còn thay đổi.',
         'Mọi luật trong hệ thống chỉ tính trên nến đã đóng. Biểu đồ vẽ nến đang chạy mờ hơn ở cuối, chỉ để nhìn.'),
        ('Bid và Ask',
         'Bid là giá bạn bán được, Ask là giá bạn mua được. Khoảng cách giữa hai giá là spread, tức chi phí của mỗi lệnh.',
         'Biểu đồ vẽ đường Bid màu xám và đường Ask màu đỏ như MT5. Spread ghi nhận gần đây của XAUUSDp khoảng 0,17 giá.'),
        ('EMA20 và EMA50',
         'Đường trung bình động lũy thừa của 20 và 50 nến gần nhất. EMA20 nằm trên EMA50 thì đà ngắn hạn đang lên, và ngược lại.',
         'Bot dùng EMA20 so với EMA50 trên H1 và H4, và giá so với EMA200 trên D1, để xác định xu hướng. Luật ba khung dùng EMA20 so với EMA50 trên cả D1, H4, H1.'),
        ('Dải Bollinger',
         'Đường trung bình 20 nến cộng trừ hai lần độ lệch chuẩn. Giá ra ngoài dải nghĩa là đang chạy mạnh hơn mức thường.',
         'Kiểu vào lệnh theo dải Bollinger có trong mã của bot nhưng đang tắt. EA BB dùng dải Bollinger 20, 2 trên H4.'),
        ('RSI14',
         'Chỉ số sức mạnh tương đối, từ 0 đến 100, tính theo cách của Wilder. Trên 70 thường gọi là quá mua, dưới 30 là quá bán.',
         'Sổ thí nghiệm của bot ghi: lọc lệnh bằng RSI hay MACD chỉ đổi số lệnh lấy lãi mỗi lệnh, không được nhận vào luật. RSI trên biểu đồ chỉ để tham khảo.'),
        ('ATR14',
         'Biên độ dao động trung bình của 14 nến. Dùng làm thước đo: dừng lỗ, vùng giá và bộ lọc thường tính theo bội số của ATR.',
         'Bot lọc lệnh theo ATR14 của nến ngày và của chính khung tín hiệu. Ô tính khối lượng có nút lấy SL bằng 1,5 lần ATR M15.'),
        ('Hỗ trợ và kháng cự 2 giờ',
         'Đáy thấp nhất và đỉnh cao nhất của 2 giờ gần đây. Giá hay phản ứng quanh các mức này.',
         'Bot đặt SL ngoài vùng hỗ trợ hoặc kháng cự 1 giá, và chỉ nhận SL cách giá vào 17 đến 28 giá.'),
        ('Khoảng trống giá (FVG) và khối lệnh',
         'FVG là khoảng giá mà ba nến liên tiếp để hở, cho thấy giá chạy quá nhanh. Khối lệnh là cây nến cuối cùng ngược chiều trước một cú chạy mạnh.',
         'Ngưỡng trong mã: FVG rộng từ 0,1 lần ATR14 H1, khối lệnh cần cú chạy từ 1 lần ATR14 H1. Sổ thí nghiệm của bot ghi kiểu vào lệnh theo FVG lỗ ở 2015–2023 trong cả 16 biến thể.'),
        ('Giờ tin USD mạnh',
         'Các tin như bảng lương Mỹ, lạm phát, quyết định lãi suất làm vàng giật mạnh và spread giãn rộng.',
         'Bot và các luật né 15 phút trước và sau tin. Lịch lấy từ lịch kinh tế của MT5 và phải xuất lại khoảng ba tuần một lần.'),
    ]),
    ('Các luật của bạn', [
        ('Luật của bot tín hiệu (phá đỉnh, phá đáy)',
         'Chỉ ra lệnh khi xu hướng các khung lớn cùng chiều (từ đêm 24/11/2026: MUA cần H1 và H4 cùng tăng, BÁN cần H1, H4 và D1 cùng giảm; trước đó cả hai chiều cần đủ ba khung) và nến tín hiệu đóng vượt đỉnh cao nhất hoặc thủng đáy thấp nhất của quãng trước đó.',
         'Có thêm bộ lọc độ dãn (0,5 đến 2 lần ATR ngày) và thân nến (từ 0,5 lần ATR). Sáu mức TP từ 0,5R đến 3R. MUA cần H1 và H4 cùng tăng, BÁN cần H1, H4 và D1 cùng giảm (từ đêm 24/11/2026); tối đa 6 lệnh mở cùng lúc (từ sáng 25/11/2026, trước là 3). Bot tự đo 2024–26: 1.249 lệnh, +4,38 giá mỗi lệnh, sụt giảm 621 giá; phần tăng chủ yếu do nhiều lệnh cùng chiều mở chồng lên nhau. Webapp đo độc lập với chi phí thật, trên nến đã sửa lệch giờ (3.522 lệnh): −0,002R mỗi lệnh ở 2015–2021, +0,174R ở 2022–2026. Vàng tăng gần suốt 2015–2026 nên phép đo ưu ái lệnh MUA, và cấu hình chọn khi đã nhìn dữ liệu nên con số lạc quan.'),
        ('Luật xu hướng ba khung',
         'Khi D1, H4, H1 cùng chiều và nến M15 vừa đóng đi ngược chiều đó, vào lệnh thuận xu hướng. Chốt lời 5 USD, dừng lỗ 20 USD ở 0,01 lot.',
         'Cần thắng trên 80% số lệnh mới hòa vốn (80,7% khi tính phí). Kiểm bản né tin 2023–10/2026: 2.610 lệnh, thắng 81,8%, lãi 730 USD; 2016–2022 lỗ 52 USD. Đang đo, cần 300 lệnh mới kết luận.'),
        ('Luật đỉnh/đáy 8 giờ',
         'Bán khi nến M15 chạm đỉnh 8 giờ rồi đóng giảm, mua đối xứng ở đáy. SL lùi 0,5 lần ATR, chốt hết ở 1,5R.',
         'Khi kiểm lại có lãi mỏng năm 2026 nhưng lỗ cả ba năm 2023–2025. Sổ chạy bóng mới có vài lệnh.'),
        ('AI phân tích điểm vào',
         'Gửi nến M5 đến H1, các vùng giá và tin sắp tới cho Claude theo lời nhắc v3, nhận lại hành động, giá vào, SL, ba TP và lý do; rồi kiểm câu trả lời bằng bộ luật.',
         'Phát lại 19 ngày: thắng 41% số lệnh, âm 4,82R. Sáu điều kiện cổng trong mã: ít nhất 100 lệnh, trải 28 ngày, R trung bình dương, hệ số lợi nhuận từ 1,2, hơn hai đối chứng, tỷ lệ không hợp lệ dưới 10%. Chưa đạt.'),
    ]),
    ('Đọc bảng phân tích điểm vào', [
        ('Nút Phân tích điểm vào',
         'Bấm nút thì trang gọi bốn luật đã viết sẵn và ghi ra mức giá mỗi luật sẽ dùng nếu ra lệnh ngay lúc đó: chiều, giá vào, dừng lỗ, các mức chốt lời.',
         'Không có công thức mới và không gọi AI: đây là luật bot (hai kiểu vào), luật ba khung và luật đỉnh/đáy. Luật nào không có điều kiện thì trang ghi rõ lý do thay vì cố ra mức giá.'),
        ('"Còn hiệu lực" và "Chỉ để tham khảo"',
         'Một phương án còn hiệu lực khi luật thật cũng sẽ vào lệnh đúng lúc đó. Quá hạn thì mức giá chỉ còn để xem luật nghĩ gì, không phải tín hiệu.',
         'Hết hiệu lực khi: giá cũ hơn 20 phút, đang trong 15 phút quanh tin USD mạnh, nến tín hiệu đã đóng quá 3 phút (bot) hoặc 5 phút (luật ba khung, đỉnh/đáy), hoặc luật ba khung đang ngoài khung giờ 14:00–03:00.'),
        ('Bội số R',
         'R là khoảng cách từ giá vào tới dừng lỗ. TP ở 1,5R nghĩa là nếu chạm thì lãi gấp rưỡi phần chấp nhận mất.',
         'Luật bot đặt sáu TP từ 0,5R tới 3R. Luật ba khung chốt 5 dừng 20, tức 0,25R, nên phải thắng hơn 80% số lệnh mới hòa vốn.'),
        ('Vùng đỏ, vùng xanh trên biểu đồ',
         'Khi vẽ một phương án, vùng đỏ là khoảng từ giá vào tới dừng lỗ (phần có thể mất), vùng xanh là khoảng tới mức chốt lời xa nhất.',
         'Thang giá tự nới tới SL và TP1 để nhìn được cả hai. Vùng xanh rộng hơn vùng đỏ không có nghĩa là dễ thắng: giá phải đi tới đó trước khi chạm SL.'),
        ('Kiểm chứng lịch sử',
         'Chạy lại đúng luật trên nến 1 phút của kho nến gần nhất để xem những lần trước luật ra lệnh cùng chiều thì kết thúc ra sao.',
         'Dùng bộ kiểm của chính dự án (tinhieu.backtest, ai_trend_history, ai.scorer). Quãng kiểm chỉ khoảng bốn tháng và dự án đã nhìn thấy dữ liệu này, nên số chỉ cho biết luật vừa qua hành xử thế nào, không dự báo được lệnh sắp tới.'),
        ('Bối cảnh giống lúc này, nửa học và nửa kiểm',
         'Một bộ lọc trông đẹp trên toàn bộ dữ liệu có thể chỉ là trùng hợp. Cách thử đơn giản là cắt dữ liệu theo thời gian: tìm trên phần đầu, rồi xem phần sau có còn đúng không.',
         'Trang chạy lại ba luật trên dữ liệu từ 2024, gắn cho mỗi lệnh chiều, phiên và biên độ, rồi cắt 70% đầu làm nửa học, 30% cuối làm nửa kiểm. Bối cảnh chỉ được ghi "Có lãi ở cả hai nửa" khi mỗi nửa đủ 30 lệnh. Ví dụ: vàng tăng suốt 2024–2025 nên lệnh BÁN của bot không có lệnh nào ở nửa học, và trang ghi "Chưa đủ mẫu".'),
        ('Luật bot và luật ba khung trên 11 năm (đo ngày 22/11/2026)',
         'Trang nhận xét ba luật trong sổ trên dữ liệu từ 2024, đúng quãng vàng tăng mạnh nhất. Để biết phần lãi đó có giữ được ở các năm trước không, luật bot và luật ba khung đã được chạy lại từ 2015 bằng chính bộ chấm của dự án. '
         'Luật bot: 2015–2023 có 1.605 lệnh, 49,4% có lãi, trung bình −0,06 USD mỗi lệnh, 4 trên 9 năm có lãi; 2024–2026 có 841 lệnh, +4,94 USD mỗi lệnh. '
         'Luật ba khung: 2015–2023 có 1.668 lệnh, thắng 80,5% trong khi hòa vốn cần 80,7%, trung bình −0,07 USD mỗi lệnh, 4 trên 9 năm có lãi; 2024–2026 có 2.403 lệnh, +0,40 USD mỗi lệnh.',
         'Nghĩa là phần lãi của cả hai luật nằm gần hết ở 2025–2026; chín năm trước đó cả hai quanh hòa vốn. Một giới hạn của phép so: mức chốt lời và dừng lỗ của hai luật là số giá cố định, đặt cho mặt bằng giá hiện nay, '
         'nên ở những năm vàng còn 1.100–2.000 USD thì các năm cũ không phải phép kiểm giống hệt. Phiếu lệnh trên trang Biểu đồ có dòng Các năm trước quãng này để nêu các con số này; nhận xét Có lãi ở cả hai nửa và nút Kỷ luật vẫn dùng quãng từ 2024. '
         'Bộ chấm luật ba khung của dự án đã được đối chiếu với Backtesting.py trên 4.144 lệnh: 98,9% giống hệt; chỗ khác duy nhất là khi nến mở cửa nhảy qua mức, bộ chấm vẫn tính đúng −20 hoặc +5 (11 lệnh dừng lỗ thực tế nặng hơn tổng cộng 67,5 giá, 34 lệnh chốt lời thực tế hơn 163 giá). '
         'Phần thoát lệnh của bộ chấm luật bot (sáu mức chốt chia đều, giữ tối đa 24 giờ) cũng đã được đối chiếu với Backtesting.py ngày 23/11/2026: 2.461 lệnh từ 2015, 99,3% giống hệt, 0 lệnh chưa giải thích được; '
         '9 lệnh nhảy qua mức chốt lời và 7 lệnh ở nến hết hạn giữ được bộ chấm tính thấp hơn tổng cộng khoảng 23 giá. Phép này không kiểm việc chọn tín hiệu nào được vào. '
         'Bộ chấm luật đỉnh/đáy (ba phần chốt ở ba mức, chốt phần đầu thì dời dừng lỗ về giá vào, giữ tối đa 8 giờ) cũng đã được đối chiếu ngày 23/11/2026: '
         '5.865 lệnh từ 2015, 5.856 giống hệt (99,8%), 9 lệnh nhảy qua mức chốt lời, 0 lệnh chưa giải thích được. Cả bốn bộ chấm của webapp nay đều có đối chiếu độc lập ở phần thoát lệnh. '
         'Phần chọn nến vào lệnh của luật bot và luật đỉnh/đáy cũng đã được đối chiếu ngày 23/11/2026 với một bản dựng lại độc lập (viết từ lời mô tả luật, tính theo cách khác, mỗi nến chỉ nhìn dữ liệu đã có lúc quyết định): '
         'luật bot 10.385 nến tín hiệu và 2.450/2.450 lệnh trùng; luật đỉnh/đáy 5.119/5.119 tín hiệu trùng; 0 chỗ lệch, không thấy dấu hiệu nhìn trước tương lai. '
         'Phép này cũng cho thấy bộ kiểm luật bot xếp tín hiệu theo giờ mở nến chứ không theo giờ quyết định: 79 trên 2.450 quyết định sẽ khác nếu xử lý đúng thứ tự thời gian, tổng cả quãng đổi từ +4.053 thành +4.008 giá (khoảng 1%). '
         'Chạy lại: python -X utf8 cong-cu/doi_chieu_ba_khung.py, cong-cu/doi_chieu_bot.py, cong-cu/doi_chieu_dinh_day.py và cong-cu/doi_chieu_diem_vao.py'),
        ('Kiểm định thống kê, và một lỗi rò rỉ dữ liệu nó bắt được (ngày 23/11/2026)',
         'Các bài báo về dự báo tài chính đòi hai điều mà phép đo thông thường hay bỏ qua: sai số phải tính tới việc các lệnh dồn cụm theo thời gian, và phải tính tới việc đã thử nhiều phương án rồi mới chọn. '
         'Khi áp phép này lên điểm mô hình, lần đầu nhóm 10% điểm cao nhất cho +0,087R mỗi tín hiệu, trong khi mô phỏng giao dịch lại âm. Truy ra thì đó là rò rỉ: lúc học, đặc trưng đồng thuận chỉ đếm các tín hiệu về sau có khớp lệnh, '
         'mà một lệnh chờ có khớp hay không là thông tin của tương lai. Lúc chạy thật trang đếm mọi tín hiệu, nên mô hình được học một thứ và dùng một thứ khác.',
         'Sau khi sửa (lúc học cũng đếm mọi tín hiệu): nhóm 10% điểm cao nhất, cuốn chiếu 2019–2026, 4.930 tín hiệu, chốt 2R trung bình −0,017R, khoảng tin cậy 95% từ −0,077 đến +0,042, tức không khác 0. '
         'Nhóm này vẫn hơn mức không lọc +0,104R, còn ý nghĩa sau hiệu chỉnh cho 16 cấu hình đã thử: mô hình xếp hạng tốt hơn ngẫu nhiên, nhưng nhóm nó chọn không có lãi, và chỉ dương ở 2024–2026. '
         'Với nút Kỷ luật: trong 223 bối cảnh đủ mẫu của 11 luật và phương pháp, chỉ 24 cái (11%) có lãi ở cả hai nửa, còn 97 cái (43%) lỗ ở cả hai nửa. Nếu không bối cảnh nào có lợi thế thật thì riêng may rủi đã cho khoảng 25% có lãi ở cả hai nửa. '
         'Vì vậy qua được Kỷ luật không phải bằng chứng có lợi thế; Kỷ luật chỉ loại bớt những chỗ số đo đã cho thấy rõ là kém. Chạy lại: python -X utf8 cong-cu/kiem_dinh_thong_ke.py'),
        ('Kiểm định SPA: sau khi đã thử nhiều luật, có luật nào lãi thật không (ngày 23/11/2026, sửa ngày 24/11/2026)',
         'Khi nhìn mấy chục luật và bối cảnh cùng lúc, cái đứng đầu luôn trông đẹp, kể cả khi không cái nào có lợi thế. Kiểm định SPA của Hansen và Reality Check của White trả lời đúng câu này: cái tốt nhất có vượt được mức mà may rủi tạo ra trên cả tập hay không. '
         'Đo trên 52.097 lệnh của 11 luật và phương pháp, vàng 2015–2026, gộp theo tuần, chuẩn so sánh là không vào lệnh. Trong 33 chiến lược (gộp và từng chiều), cái tốt nhất là luật bot chiều MUA, +3.691 USD cả quãng ở 0,01 lot.',
         'Nếu coi như chỉ thử một mình luật bot chiều MUA thì giá trị p là 0,010, trông có ý nghĩa. Tính cả tập bằng bản SPA tự viết thì p là 0,082, và 0,26 khi thêm từng chiều trong từng phiên (119 chiến lược). '
         'Ngày 24/11/2026 bản tự viết được đối chiếu với thư viện arch. Trên dữ liệu dựng từ chính bảng lãi lỗ thật sau khi ép mọi chiến lược về lãi thật bằng 0, bản tự viết chỉ báo động nhầm 2,0% ở mức 5% (quá thận trọng), arch 4,7% (đúng mức), nên số của arch đáng đọc hơn: '
         'p = 0,030 với 33 chiến lược (chạy lại đêm 25/11/2026 với bot mới; trước đó 0,025), tức CÓ ý nghĩa ở mức 5%; p = 0,22 với 119 chiến lược, không có ý nghĩa. Câu cũ ở mục này, chưa luật nào có lãi có ý nghĩa thống kê ở mức 5%, vì vậy không còn đúng cho tập 33. '
         'Nhưng phần lãi đó nằm trọn ở 2024–2026. Tách tập 33 theo giai đoạn: riêng 2015–2023 thì p = 0,51 và chỉ 4 trên 33 chiến lược có tổng dương; riêng 2024–2026 thì p = 0,006. '
         'Tham số của luật bot được chọn khi đã nhìn chính quãng 2024–2026, lúc vàng tăng mạnh một chiều, và kiểm định SPA không tính được việc chọn tham số. Nên con số 0,030 không phải bằng chứng luật bot sẽ có lãi về sau. Phép xác suất khớp quá mức (PBO, Bailey và López de Prado) trên cùng bảng cho 0,08 với 33 chiến lược: chọn theo quá khứ không phải chọn bừa, nhưng cùng giới hạn đó. '
         'Mô phỏng Monte Carlo 10.000 năm (cong-cu/rui_ro_monte_carlo.py): với dữ liệu 2022–2026 luật bot có 2,7% số năm lỗ, với dữ liệu 2015–2021 có 59%; rủi ro 5% vốn mỗi lệnh thì có 10 đến 40% khả năng có lúc mất nửa vốn trong một năm, 25% mỗi lệnh thì 78 đến 94%; '
         'bằng chứng còn thiếu vẫn là dữ liệu sau ngày chốt luật (sổ chạy bóng, nhật ký điểm vào). Chạy lại: python -X utf8 cong-cu/kiem_dinh_spa.py rồi python -X utf8 cong-cu/doi_chieu_spa.py'),
        ('Điểm vào lệnh: vào kiểu nào, dừng lỗ ở đâu là tốt nhất theo số đo (ngày 24/11/2026)',
         'Trên cùng một bộ tín hiệu của tám phương pháp (vàng 2015–2026), trang đã so các kiểu vào, cách đặt dừng lỗ, cách chốt lời và bộ lọc bối cảnh: 107 phép so, chọn trên 2015–2021, xác nhận trên 2022–2026, với spread thật của từng nến, trượt giá lúc tin và phí qua đêm. '
         'Lệnh chờ ở giữa khoảng trống giá bỏ lỡ đúng các lệnh thắng mạnh: tín hiệu ICT không khớp lệnh chờ, nếu vào ngay, cho +0,83R tới +0,96R mỗi lệnh, còn tín hiệu có khớp cho −0,37R tới −0,48R. Ngược lại, lệnh chờ dừng ở đỉnh hoặc đáy nến tín hiệu bỏ được các tín hiệu hỏng ngay (gần như toàn thua). '
         'Lệnh thắng thường đi ngược 0,4–0,5R trước khi về đích, nên nới dừng lỗ giúp năm phương pháp. Không cách chốt lời nào hơn chốt hết ở 2R: sau khi vào lệnh giá đi gần như ngẫu nhiên (44–49% lệnh từng đạt 1R, 29–30% đạt 2R).',
         'Kết quả: khoản lỗ mỗi lệnh giảm khoảng một nửa, nhưng trên 2015–2021 cả tám phương pháp vẫn lỗ, và trên 2022–2026 chỉ ba phương pháp quanh hòa vốn. Với 107 phép so, một phần cải thiện có thể do may. '
         'Vì vậy công thức mới chỉ hiện ở phiếu vào lệnh trong bảng phân tích (loại lệnh, giá vào, dừng lỗ, hai mức chốt, khối lượng theo % rủi ro bạn nhập, thời hạn, điều kiện hủy, số đo trước và sau); luật gốc và nhật ký điểm vào giữ nguyên. '
         'Điểm chất lượng điểm vào đã thử và bị bỏ vì nhóm điểm cao không tốt hơn nhóm thấp. '
         'Luật bot tín hiệu được đo cùng cách và đo lại mỗi lần mã bot đổi (lần gần nhất sáng 25/11/2026, bản 6 lệnh mở, 3.518 lệnh): bản hiện tại −0,002R mỗi lệnh ở 2015–2021 và +0,177R ở 2022–2026, gần hết phần lãi nằm ở 2025–2026. Bản qua cổng đổi theo từng phiên bản bot: với bản 3 lệnh mở là chờ phá đỉnh hoặc đáy nến tín hiệu, với bản 6 lệnh mở là vào ngay, dừng lỗ lùi thêm 3 giá, chốt hết ở 2R (+0,224R ở phần kiểm tra); kết quả đổi theo cấu hình như vậy nghĩa là lợi thế của kiểu vào không vững. Phiếu của luật bot tự theo bản qua cổng của lần đo gần nhất. Trang chỉ đo, không sửa bot. '
         'Tỷ lệ thắng theo năm khi chỉ đổi mức chốt lời: chốt ở 0,25R cho khoảng 74% lệnh thắng nhưng chỉ 4 đến 5 trong 12 năm đạt 75%, và lãi mỗi lệnh âm (cần thắng trên 80% mới hòa vốn trước chi phí); luật bot tốt nhất ở 2R với 49% thắng và +0,093R mỗi lệnh. Tỷ lệ thắng dễ làm đẹp bằng cách chốt sớm; thước đo đúng là lãi mỗi lệnh sau chi phí. '
         'Lọc lệnh luật bot bằng mô hình học máy (meta-labeling, kiểm định chéo có tách khoảng theo López de Prado 2018) không qua cổng: biến thể chọn trên 2015–2021 kém hơn không lọc ở 2022–2026 và không hơn chọn ngẫu nhiên; khả năng phân biệt lệnh thắng gần như đoán bừa (AUC 0,47–0,55). Bản 2 thêm thông tin liên thị trường (bạc, dầu Brent, S&P 500, vị thế quỹ đầu cơ trong COT) cũng không qua cổng và không làm AUC tăng. '
         'Luật ba khung và luật đỉnh/đáy cũng đã đo cùng cách: ba khung thắng 70 đến 81% nhưng gần hòa vốn vì chốt 5 giá mà dừng 20; chốt 2R qua cổng nhưng thắng còn 44% và sụt giảm tăng gấp bốn rưỡi; đỉnh/đáy lỗ ở mọi biến thể và mọi năm. Không luật nào bị sửa. '
         'Khi bot có tín hiệu nến, trang kèm một phiếu chờ phá đỉnh hoặc đáy nến tín hiệu (kiểu vào duy nhất qua cổng, cả trước và sau khi bot đổi lọc xu hướng) và ghi nó vào nhật ký, chấm theo TP1 như lệnh gốc, để giá thật trả lời kiểu vào này có hơn không. '
         'Từ đêm 25/11/2026 mỗi điểm vào trong nhật ký mang dấu băm SHA-256 nối với dòng trước, nên không ai sửa, xóa hay chèn được một tín hiệu cũ mà chuỗi không gãy; phần tự kiểm báo ngay nếu chuỗi gãy. '
         'Mọi thứ đã chốt ngày 24/11/2026 được đo lại nguyên trạng trên giá mới từ 25/11/2026 bằng DO_LAI_DU_LIEU_MOI.bat (bảng ở đầu trang này); đó là cách duy nhất để biết phần lãi gần đây là thật hay may. '
         'Báo cáo đầy đủ: DIEM_VAO_BAO_CAO.md. Chạy lại: python -X utf8 cong-cu/diem_vao.py, cong-cu/diem_vao_bot.py, cong-cu/ty_le_thang_nam.py và cong-cu/loc_lenh_bot.py'),
        ('Chuẩn hóa phương pháp theo sách: sửa gì, đo ra sao (ngày 24/11/2026)',
         'Ba thay đổi được xét để điểm vào đúng định nghĩa chuẩn hơn; luật và ngưỡng chấp nhận được ghi ra trước khi đo (cong-cu/CHUAN_HOA_DANG_KY.md), đo trên vàng 2015–2026 bằng đúng phép chấm của trang. '
         'Một: khoảng trống giá chỉ tính khi nến giữa là nến đẩy cùng chiều, đúng định nghĩa của ICT. Đã áp dụng; bỏ khoảng 1% tín hiệu (102 ở mỗi phương pháp ICT), kết quả gần như không đổi (R trung bình mỗi lệnh −0,095 thành −0,093 và −0,151 thành −0,150). '
         'Hai: bắt lệnh ICT phải đủ cả năm điều kiện hợp lưu trong bảng điều kiện. Không áp dụng: 11 năm chỉ còn 284 và 577 lệnh, và R trung bình kém hơn hẳn (−0,217 và −0,226), ở cả hai nửa dữ liệu.',
         'Ba: Wyckoff có xác nhận bằng khối lượng. Không đo được vì dữ liệu nến nhiều năm chỉ có khối lượng cho 2015–2017. '
         'Điều rút ra: làm phương pháp đúng sách hơn là việc nên làm cho đúng tên gọi của nó, nhưng trên dữ liệu cũ nó không làm phương pháp có lãi hơn; thêm nhiều điều kiện còn làm ít lệnh đi và kết quả xấu đi. '
         'Sau thay đổi một, khoảng trống giá của trang trùng hẳn với thư viện smartmoneyconcepts. Phá cấu trúc (BOS, CHoCH) và quét thanh khoản được dựng lại độc lập theo cách tính khác và trùng hẳn trên 11 năm (19.972/19.972 lần phá cấu trúc, cong-cu/doi_chieu_cau_truc.py). Chạy lại: python -X utf8 cong-cu/chuan_hoa.py'),
        ('Xác suất của mô hình có đáng tin không (ngày 23/11/2026)',
         'Một mô hình có thể xếp hạng đúng mà nói sai xác suất. Phép hiệu chuẩn so xác suất mô hình nêu với tỷ lệ thắng thật, trên 47.724 tín hiệu mà mô hình chưa thấy lúc học (2019–2026). '
         'Kết quả: xác suất khớp thực tế, cả mười nhóm đều lệch không quá 2,1 điểm phần trăm, và tỷ lệ thắng tăng đều từ nhóm thấp nhất (28,2%) lên nhóm cao nhất (35,5%). Mô hình không nói quá.',
         'Nhưng mô hình phân biệt được rất ít: bốn phần năm số tín hiệu được chấm trong khoảng 28–34%, và so với việc luôn nói tỷ lệ thắng trung bình thì nó chỉ tốt hơn 0,18% theo điểm Brier. '
         'Nhóm cao nhất thắng 35,5% khi chốt ở 2R, trong khi hòa vốn cần hơn 33,3% cộng chi phí, nên nhóm đó vẫn lỗ nhẹ (−0,014R). Vì vậy điểm mô hình là một thứ hạng tham khảo trung thực, không phải bộ lọc tạo ra lãi. Chạy lại: python -X utf8 cong-cu/kiem_hieu_chuan.py'),
        ('Vào lệnh trễ vài phút thì sao (ngày 23/11/2026)',
         'Một lợi thế thật phải chịu được việc người dùng thấy tín hiệu rồi vài phút sau mới đặt lệnh. Tám phương pháp và nhóm điểm mô hình từ 90 được chạy lại với độ trễ 1, 5 và 15 phút, giữ nguyên mức dừng lỗ. Không ô nào dương ở bất kỳ độ trễ nào.',
         'Các phương pháp đặt lệnh chờ (ICT, Fibonacci) gần như không đổi khi trễ, chỉ ít lệnh hơn vì một số tín hiệu đã qua. Các phương pháp vào theo giá thị trường kém đi rõ khi trễ từ 5 phút: hồi về EMA từ −0,137R xuống −0,274R ở 15 phút, Wyckoff từ −0,186R xuống −0,225R, Price Action từ −0,192R xuống −0,238R. '
         'Nhóm điểm mô hình từ 90: −0,029R xuống −0,047R. Chạy lại: python -X utf8 cong-cu/kiem_vao_tre.py'),
        ('Khối lượng "cá mập" và báo cáo COT (đo ngày 23/11/2026)',
         'Vàng và forex giao ngay không có sàn tập trung, nên không nguồn nào cho xem khối lượng của các tay lớn theo thời gian thực. Khối lượng trong MT5 chỉ là số lần giá nhảy. '
         'Thứ gần nhất có nguồn chính thức là báo cáo COT của CFTC: mỗi tuần cho biết quỹ đầu cơ, ngân hàng và nhà sản xuất đang giữ bao nhiêu hợp đồng vàng tương lai ở COMEX. '
         'Số chốt thứ Ba, công bố thứ Sáu. Trang biểu đồ vàng có một khung hiện báo cáo mới nhất; webapp tự tải tệp công khai từ cftc.gov và không gửi đi dữ liệu nào.',
         'Đo trên 463 tuần từ 2018 tới 11/2026, vào ở phiên đầu tiên sau ngày công bố: nhóm tuần quỹ mua ròng cao (từ 80% trở lên so với 3 năm trước đó) có lợi suất 1 tuần sau +0,26%, nhóm thấp +0,28%; '
         '4 tuần sau +1,82% so với +0,94% (p = 0,39). Tuần quỹ mua thêm: 1 tuần sau +0,06%, tuần quỹ bán bớt +0,39% (p = 0,08). Không phép nào trong bốn phép vượt ngưỡng 0,0125. '
         'Trong chính tuần chốt, quỹ mua thêm ở 72% số tuần giá tăng và 19% số tuần giá giảm: vị thế đi theo giá. Vì vậy COT là bối cảnh, không phải tín hiệu. Chạy lại: python -X utf8 cong-cu/kiem_cot.py'),
        ('Luật đỉnh/đáy trên 11 năm (đo ngày 23/11/2026)',
         'Luật đỉnh/đáy cũng đã được chạy lại từ 2015 bằng chính bộ chấm của dự án, sau chi phí. 2015–2023 có 3.680 lệnh, 36,9% có lãi, trung bình −0,64 USD mỗi lệnh, không năm nào trong 9 năm có lãi. '
         '2024–2026 có 1.438 lệnh, 41,1% có lãi, −0,53 USD mỗi lệnh. Cả hai chiều MUA và BÁN đều lỗ ở cả hai quãng.',
         'Khác với luật bot và luật ba khung, luật này đặt dừng lỗ theo biên độ lúc đó (ATR) nên các năm cũ so được với hiện nay. Tham số của nó được chọn trên dữ liệu 5/1–31/7/2026, '
         'nên mọi năm trước 2026 là dữ liệu luật chưa từng thấy; trên các năm đó luật lỗ đều. Với tỷ lệ chốt 1,5R, cần khoảng 40% lệnh thắng mới hòa vốn trước chi phí; luật đạt 34–42% tùy năm.'),
        ('"Lệnh có lãi" khác "chạm TP1"',
         'Lệnh của bot chia đều cho sáu TP. Chạm TP1 mới chốt một phần sáu; phần còn lại vẫn có thể quay về dừng lỗ và làm cả lệnh lỗ.',
         'Vì vậy bảng kiểm chứng ghi cả hai: tỷ lệ chạm TP1 và tỷ lệ lệnh có lãi ròng sau chi phí. Hai số có thể cách nhau hơn 20 điểm phần trăm.'),
    ]),
    ('Các phương pháp phân tích tùy chọn', [
        ('Bài học từ 11 năm dữ liệu (2015–2026): đọc mục này trước',
         'Cả tám mô hình đã được chạy lại trên 4,19 triệu nến 1 phút của vàng từ 2015. Kết quả: không mô hình nào có lãi ổn định. Tính theo R (bội số của khoản rủi ro), chấm riêng từng tín hiệu, mọi mô hình đều âm ở mọi mức chốt lời, từ −0,01R (Elliott) tới −0,20R mỗi lệnh. Quãng 2024–2026 trông có lãi vì vàng biến động rất mạnh, không đại diện cho cả 11 năm.',
         'Tỷ lệ thắng đo được gần đúng công thức của một điểm vào ngẫu nhiên, 1 chia cho (1 cộng mức chốt): chốt ở 0,25R thắng 70–77% (ngẫu nhiên là 80%), ở 0,5R thắng 60–66% (66,7%), ở 1R thắng 45–50% (50%), ở 2R thắng 31–36% (33,3%), ở 3R thắng 24–30% (25%). Phần thiếu hụt là spread và phí. Vì vậy muốn thắng 85–90% số lệnh thì phải chốt lời ở khoảng 0,11–0,18R, và khi đó một lệnh thua xóa sạch sáu tới chín lệnh thắng: tỷ lệ thắng cao mà vẫn lỗ. Đã thử tìm bộ lọc cải tiến (thuận H1, thuận D1, phiên, biên độ, chiều) trên 2015–2021, kiểm trên 2022–2024 và thi trên 2025–2026: trong 16 lần tìm chỉ 1 bộ lọc còn có lãi ở cả hai quãng sau (Elliott chốt 1R khi biên độ cao, 70 và 64 lệnh), đúng mức có thể chờ đợi do may. Tính theo USD ở 0,01 lot, mỗi lúc một lệnh, từ 2015: ICT quét thanh khoản 4.658 lệnh, +0,55 USD mỗi lệnh ở 2R nhưng lỗ ở nửa học; ICT hồi về khoảng trống giá 4.592 lệnh, +0,36 USD, chiều MUA có lãi ở cả hai nửa nhưng nửa học chỉ +0,07; Elliott 1.553 lệnh, +0,33 USD, không ổn định; năm mô hình còn lại lỗ. Chạy lại phép thử này bằng lệnh: python -X utf8 cong-cu/nghien_cuu.py'),
        ('Vì sao phải viết thành quy tắc máy',
         'Phần lớn trường phái (SMC/ICT, Wyckoff, Price Action, Elliott) được dạy bằng ví dụ và phán đoán. Hai người nhìn cùng một biểu đồ có thể vẽ khác nhau, nên không đo được.',
         'Mỗi phương pháp ở đây là một quy tắc cố định mà máy tự xét được, để vừa tìm điểm vào lúc này, vừa chạy lại được trên dữ liệu từ 2024. Tham số được chọn trước khi chạy và không chỉnh lại sau khi xem kết quả.'),
        ('ICT/SMC: quét thanh khoản và khoảng trống giá',
         'Giá thường quét qua đáy hoặc đỉnh gần nhất (nơi nhiều lệnh dừng lỗ nằm) rồi đảo chiều mạnh, để lại một khoảng trống giá (FVG). Vào khi giá hồi về giữa khoảng trống đó.',
         'Quy tắc: quét đáy/đỉnh 5 giờ rồi đóng ngược lại, kèm khoảng trống giá ít nhất 0,1 ATR; lệnh chờ ở giữa khoảng trống, sống 4 giờ. Khi chỉ nhìn vàng 2024–2026: 1.164 lệnh, 36,1% có lãi, trung bình +1,28 USD mỗi lệnh ở 0,01 lot. Trên 2015–2026: 4.587 lệnh, 33,3% có lãi, +0,11 USD mỗi lệnh; cả hai chiều lỗ ở nửa học và lãi ở nửa kiểm, tức không ổn định. Bản trước ghi +2,38 và +0,52 USD; phần chênh là do lỗi nhìn trước của phép chấm ở lệnh chờ, đã sửa ngày 22/11/2026 (xem mục công cụ ngoài).'),
        ('ICT/SMC: hồi về khoảng trống giá sau khi phá cấu trúc',
         'Mô hình ICT thứ hai: khi H1 có xu hướng và một nhịp bật mạnh phá cấu trúc theo xu hướng, giá thường hồi về khoảng trống giá mà nhịp bật để lại rồi mới đi tiếp.',
         'Quy tắc: H1 có xu hướng, nhịp bật đóng vượt đỉnh (thủng đáy) 5 giờ và để lại khoảng trống giá ít nhất 0,1 ATR; lệnh chờ ở giữa khoảng trống, dừng lỗ sau điểm bắt đầu nhịp bật, sống 4 giờ. Khi chỉ nhìn vàng 2024–2026: 1.182 lệnh, 32,5% có lãi, trung bình −0,48 USD mỗi lệnh ở 0,01 lot. Trên 2015–2026: 4.589 lệnh, 31,5% có lãi, −0,41 USD mỗi lệnh, cả hai chiều lỗ ở cả hai nửa. Bản trước ghi +1,24 và +0,34 USD; toàn bộ phần lãi đó đến từ lỗi nhìn trước của phép chấm ở lệnh chờ, đã sửa ngày 22/11/2026.'),
        ('Bản đồ ICT trên biểu đồ',
         'Khi nhóm ICT/SMC đang bật, trang tự vẽ lên biểu đồ: BSL và SSL (thanh khoản trên và dưới, tức đỉnh và đáy 5 giờ), khoảng trống giá (FVG) chưa lấp gần giá nhất, các lần phá cấu trúc (BOS, CHoCH), các điểm quét thanh khoản (dấu ✕), EQ 50% (mức giữa biên độ 24 giờ: premium ở trên, discount ở dưới), PDH và PDL (đỉnh, đáy hôm trước). Rê chuột vào từng ghi chú để xem giải thích cụ thể.',
         'Bảng điều kiện cho biết điều kiện nào đã đạt, điều kiện nào còn thiếu, kèm kịch bản chờ có giá cụ thể. Bản đồ chỉ mô tả cấu trúc giá. Điểm vào chỉ xuất hiện khi một trong hai mô hình đã đo có đủ điều kiện; trang không ép ra lệnh. BOS và CHoCH ở đây tính bằng đỉnh, đáy có 3 nến mỗi bên xác nhận, có thể khác cách vẽ tay của bạn.'),
        ('Wyckoff: spring và upthrust',
         'Sau một quãng đi ngang (tích lũy hoặc phân phối), giá đâm thủng biên vùng để gom thanh khoản rồi quay lại bên trong. Bản gốc cần khối lượng để xác nhận.',
         'Quy tắc: đi ngang 12 giờ trong vùng rộng 2–8 ATR, nến đâm thủng biên rồi đóng trở lại. Kho nến không có khối lượng nên thiếu phần xác nhận. Khi chỉ nhìn vàng 2024–2026: 981 lệnh, trung bình −0,59 USD mỗi lệnh, không ổn định giữa hai nửa.'),
        ('Price Action: pin bar và nến nhấn chìm',
         'Đọc trực tiếp hình dạng nến tại vùng quan trọng: pin bar (đuôi dài, thân nhỏ) và nến nhấn chìm cho thấy một phe vừa bị đẩy lùi.',
         'Quy tắc: H1 có xu hướng, nến M15 tạo đáy/đỉnh 2 giờ rồi thành pin bar hoặc nhấn chìm theo xu hướng. Khi chỉ nhìn vàng 2024–2026: 1.226 lệnh, trung bình −0,34 USD mỗi lệnh; chiều MUA lỗ ở cả hai nửa.'),
        ('Fibonacci 61,8% (phần đo được của sóng Elliott)',
         'Sau một nhịp đẩy, giá thường hồi về một phần rồi mới đi tiếp; mức 61,8% là mức hay được dùng nhất. Đếm sóng Elliott thì mỗi người một cách, không viết được thành quy tắc nhất quán.',
         'Quy tắc: nhịp đẩy ít nhất 4 ATR trong 6 giờ vừa kết thúc, lệnh chờ ở mức hồi 61,8%. Khi chỉ nhìn vàng 2024–2026: 868 lệnh, 33,6% có lãi, trung bình −0,41 USD mỗi lệnh. Trên 2015–2026: 3.694 lệnh, 32,9% có lãi, −0,37 USD mỗi lệnh, lỗ ở cả hai chiều và cả hai nửa. Khoảng một phần mười số tín hiệu đến lúc giá đã ở bên kia mức 61,8%; trang Biểu đồ báo các tín hiệu đó là đã qua, và từ ngày 22/11/2026 phép chấm cũng không tính chúng nữa. Phần đếm sóng nằm ở mục Sóng Elliott ngay dưới.'),
        ('Sóng Elliott: vào sóng 3',
         'Lý thuyết Elliott cho rằng xu hướng đi thành năm sóng, trong đó sóng 3 thường mạnh nhất. Đếm đủ năm sóng thì mỗi người một cách; phần viết được thành quy tắc máy là cặp sóng 1–2 và điểm vào sóng 3.',
         'Quy tắc: đỉnh và đáy lấy theo zigzag (mỗi lần đảo chiều ít nhất 2 ATR); sóng 1 dài ít nhất 3 ATR; sóng 2 hồi 38,2–78,6% và không vượt điểm bắt đầu sóng 1; vào khi nến M15 đóng vượt cuối sóng 1; dừng lỗ ngay sau cuối sóng 2; mục tiêu lý thuyết là sóng 3 bằng 1,618 lần sóng 1. Tham số chọn trước khi chạy và không chỉnh lại. Số đo ở 0,01 lot: vàng từ 2024 có 379 lệnh, 37,2% có lãi, +1,54 USD mỗi lệnh (MUA +3,87, BÁN −0,83); riêng vàng năm 2026 có 115 lệnh, 38,3% có lãi, +3,28 USD mỗi lệnh; BTC năm 2026 có 179 lệnh, 41,3% có lãi, +0,60 USD mỗi lệnh. Chốt ở mục tiêu sóng 3 thay cho 2R: vàng 2026 +2,68 USD mỗi lệnh, BTC 2026 −0,06 USD. Lợi thế đo được chỉ khoảng 0,1R mỗi lệnh trên hơn một trăm lệnh, còn nằm trong khoảng có thể do may. Trên biểu đồ, trang vẽ các điểm (0), (1), (2), mục tiêu (3) và mức nến phải đóng vượt; cách đếm của máy có thể khác cách bạn đếm tay.'),
        ('Vì sao tỷ lệ thắng thấp, và bậc thang chốt lời',
         'Tỷ lệ thắng không phải thước đo chất lượng của điểm vào; nó đi liền với mức chốt lời. Chốt ở 2R nghĩa là giá phải đi xa gấp đôi khoản rủi ro trước khi quay lại chạm dừng lỗ, nên dù điểm vào thế nào cũng chỉ khoảng một phần ba số lệnh tới nơi. Chốt gần hơn thì thắng nhiều lần hơn, nhưng mỗi lần thắng nhỏ hơn.',
         'Phiếu lệnh của vàng có hàng "Tỷ lệ thắng theo mức chốt" và, trong phần Số đo và giải thích, một bảng sáu mức từ 0,25R tới 3R: tỷ lệ thắng đo được, tỷ lệ cần để hòa vốn (1 chia cho 1 cộng mức chốt), và trung bình R mỗi lệnh. Số đo lấy từ mọi tín hiệu của chính phương pháp và chiều đó trên vàng từ 2015. Ví dụ chung cho cả tám phương pháp: chốt 0,25R thắng 70–77% (cần hơn 80%), chốt 0,5R thắng 60–66% (cần hơn 66,7%), chốt 1R thắng 45–50% (cần hơn 50%), chốt 2R thắng 31–36% (cần hơn 33,3%). Ở mọi mức, tỷ lệ thắng đo được đều thấp hơn mức cần một chút, phần thiếu là spread và phí. Vì vậy đổi mức chốt làm đổi tỷ lệ thắng nhưng không làm đổi việc có lãi hay không.'),
        ('Đồng thuận giữa các phương pháp, và mô hình hiện dùng (đính chính ngày 23/11/2026)',
         'Bản trước của mục này viết rằng càng nhiều phương pháp cùng báo một chiều thì điểm vào càng kém (−0,11R, −0,15R, −0,25R) và mô hình ngoài mẫu đạt +0,13R. Cả hai con số đều sai vì lỗi rò rỉ: phép đếm chỉ tính các tín hiệu về sau có khớp lệnh. '
         'Đếm đúng, trên mọi tín hiệu như lúc chạy thật (vàng từ 2015, chốt 2R): không có phương pháp khác cùng chiều trong 2 giờ thì trung bình −0,168R mỗi lệnh (thắng 31,0%); có một thì −0,139R; từ hai trở lên thì −0,119R (thắng 32,2%). '
         'Khác biệt nhỏ, không nhất quán giữa các quãng, và cả ba nhóm đều lỗ. Nhiều phương pháp cùng báo vì vậy không làm điểm vào chắc hơn, cũng không làm nó kém đi rõ rệt. Nhãn Đồng thuận nhiều: thận trọng đã bỏ.',
         'Mô hình hiện dùng, kiểm ngoài mẫu (học tới hết 2021, chấm trên 2022–2026): nhóm điểm từ 90 thắng 37,0% ở 2R, trung bình +0,04R mỗi tín hiệu (3.029 tín hiệu), so với 32,5% và −0,09R của mọi tín hiệu; ở 1R thắng 51,3% và gần đúng hòa vốn. '
         'Theo năm: 2022 −0,03R, 2023 −0,15R, 2024 +0,08R, 2025 +0,12R, 2026 +0,17R. Chạy lại: python -X utf8 cong-cu/dong_thuan.py'),
        ('Kiểm lại mô hình theo cách khắt khe: không có lãi',
         'Phép kiểm cuốn chiếu: với mỗi năm từ 2019 tới 2026, mô hình chỉ học các tín hiệu trước năm đó, rồi mới chấm năm đó. Khi chấm riêng từng tín hiệu, nhóm điểm từ 90 âm ở năm năm 2019–2023 (từ −0,18R tới −0,03R) và dương ở ba năm 2024–2026 (+0,08R tới +0,14R).',
         'Khi cho các tín hiệu được chọn đi qua đúng phép mô phỏng của webapp (mỗi lúc một lệnh, chốt 2R, giữ tối đa 24 giờ), kết quả tám năm là 2.448 lệnh, thắng 35,0%, trung bình −0,03R mỗi lệnh, tổng −71R, sụt giảm lớn nhất 158R, 38 trên 95 tháng có lãi. '
         'Với chi phí gấp đôi: −0,09R mỗi lệnh. Không lọc gì, cùng cách mô phỏng: −0,11R. Bộ lọc của mô hình giảm được mức lỗ nhưng kết quả vẫn không dương, nên điểm mô hình chỉ để tham khảo. Chạy lại: python -X utf8 cong-cu/kiem_mo_hinh.py'),
        ('Điểm mô hình, bản đầu chưa có đồng thuận (đã thay)',
         'Một mô hình học máy (hồi quy logistic) học từ hơn 70.000 tín hiệu của tám phương pháp trên vàng từ 2015, với 14 đặc trưng chỉ tính từ nến đã đóng: rủi ro so với ATR, biên độ, giờ, thứ, thuận H1, thuận D1, khoảng cách tới EMA50, RSI, vị trí trong biên độ 24 giờ, quãng đi 4 giờ, hình dạng nến. Nó xếp hạng một điểm vào từ 0 tới 100 so với các tín hiệu quá khứ.',
         'Kiểm ngoài mẫu: mô hình chỉ học tới hết 2021 rồi được chấm trên 2022–2026. Nhóm 10% điểm cao nhất thắng 36,4% ở 2R và trung bình +0,03R mỗi lệnh (3.121 lệnh), so với 32,4% và −0,09R của mọi tín hiệu. Mức hơn mặt bằng này có ở cả năm năm, nhưng năm 2022 và 2023 nhóm được chọn vẫn lỗ. Nghĩa là mô hình chọn tốt hơn ngẫu nhiên một chút, chưa đủ để có lãi chắc. Cùng nhóm đó ở các mức chốt khác: 0,25R thắng 79,2%, 0,5R thắng 66,0%, 1R thắng 50,2%, 3R thắng 30,3%; trung bình mỗi lệnh nằm trong khoảng −0,04R tới +0,04R, tức quanh hòa vốn, trong khi mọi tín hiệu ở cùng quãng âm khoảng 0,1R. Mặc định trang chỉ ghi điểm này như một nhãn tham khảo. Nếu bạn bật nút Mô hình ≥ 90 trên thanh phương pháp, trang chỉ báo các điểm vào thuộc nhóm này. Trang Nhật ký có bảng Theo điểm mô hình, tách kết quả thật của nhóm điểm từ 90 và nhóm dưới 90. Mô hình chỉ học trên vàng nên mã khác không có điểm. Huấn luyện lại mỗi ngày ở nền; chạy lại phép kiểm bằng: python -X utf8 cong-cu/huan_luyen.py'),
        ('Phá vỡ và hồi về EMA',
         'Phá vỡ: vào theo chiều nến đóng vượt đỉnh hoặc thủng đáy. Hồi về EMA: trong xu hướng, vào khi giá chạm đường trung bình rồi bật lại.',
         'Khi chỉ nhìn vàng 2024–2026: phá vỡ 2.540 lệnh, trung bình −0,51 USD mỗi lệnh; hồi về EMA 1.756 lệnh, trung bình +0,53 USD mỗi lệnh nhưng nửa lãi nửa lỗ tùy chiều. Cả hai đều không ổn định.'),
        ('Liên thị trường và vĩ mô',
         'Nhìn dòng tiền giữa các thị trường: USD mạnh lên thường đè giá vàng, lãi suất và lợi suất trái phiếu quyết định hướng dài hạn. Phương pháp này không cho điểm vào chính xác.',
         'Bảng phân tích có dòng "USD hôm nay" và "USD theo D1 · H4 · H1", tính từ EURUSD, GBPUSD, USDJPY đang có trong MT5. Đây chỉ là bối cảnh. Hệ thống chưa có dữ liệu lãi suất, lợi suất trái phiếu hay chỉ số DXY.'),
        ('Số đo trên mã khác vàng (BTC, EURUSD…)',
         'Với mã khác vàng, mỗi phương pháp được chạy lại trên nến 5 phút của chính mã đó từ đầu năm, đọc từ MT5 demo. Số đo hiện trong từng thẻ phương án và trong lời báo điểm vào.',
         'Trên BTC năm 2026 (01/01 tới 21/11, ở 0,01 lot): không phương pháp nào có lãi rõ ràng. ICT quét thanh khoản 510 lệnh, 32,9% có lãi, trung bình −0,16 USD mỗi lệnh; ICT hồi về khoảng trống giá 473 lệnh, +0,20 USD; phá vỡ, Wyckoff, Price Action, Fibonacci, hồi về EMA đều lỗ từ −0,34 tới −0,47 USD mỗi lệnh. Mô hình ICT có lãi trên vàng không giữ được trên BTC. Giới hạn: MT5 chỉ giữ khoảng 69 ngày nến 1 phút nên lệnh chấm bằng nến 5 phút; đã trừ spread nhưng chưa trừ phí hoa hồng; chưa đầy một năm dữ liệu nên nửa kiểm chỉ dài khoảng ba tháng.'),
        ('Thử nhiều phương pháp thì dễ gặp may',
         'Thử tám mô hình mà vài cái có lãi thì chưa chắc chúng tốt thật: càng thử nhiều, càng dễ có một cái đẹp do trùng hợp.',
         'Vì vậy kết quả của ICT/SMC mới là một dấu hiệu đáng theo dõi, chưa phải bằng chứng. Nó cũng chỉ được đo trên vàng, trong một giai đoạn vàng biến động mạnh, và chưa từng chạy bóng với giá thật.'),
    ]),
    ('Biểu đồ chạy theo giá trực tiếp', [
        ('Thanh phương pháp và phiếu lệnh',
         'Phía trên biểu đồ có một hàng nút: Tất cả phương pháp, Luật của bạn, và từng phương pháp tùy chọn. Chấm xanh nhấp nháy là đang có điểm vào còn hiệu lực, chấm vàng là có điểm vào nhưng chỉ để tham khảo, chấm xám là chưa có. Bấm một nút thì phiếu lệnh bên dưới nêu điểm vào, dừng lỗ, hai mức chốt lời và mục tiêu theo lý thuyết của phương pháp đó, đồng thời vẽ lên biểu đồ.',
         'Mục tiêu lý thuyết lấy đúng theo sách của từng phương pháp: ICT quét thanh khoản nhắm thanh khoản đối diện (đỉnh hoặc đáy 5 giờ); ICT hồi về khoảng trống giá nhắm đỉnh hoặc đáy của nhịp bật; Wyckoff nhắm biên đối diện của vùng đi ngang; phá vỡ đo biên độ của vùng vừa bị phá; Fibonacci nhắm mức 0% của nhịp đẩy; Price Action và hồi về EMA nhắm đỉnh hoặc đáy 6 giờ gần nhất. Phần chạy lại trên dữ liệu chốt ở 2R; số đo khi chốt ở mục tiêu lý thuyết được ghi riêng trong phiếu lệnh và trong phần bằng chứng của từng thẻ. Khi số đo quá khứ của một phương án là lỗ, phiếu lệnh ghi rõ điều đó.'),
        ('Tỷ lệ thắng ở 1R và 2R, bảng xếp hạng, chế độ Kỷ luật',
         'Mỗi phương pháp được chạy lại hai lần trên cùng dữ liệu: một lần chốt lời ở 1R (lãi bằng rủi ro), một lần chốt ở 2R. Chốt ở 1R phải thắng hơn 50% số lệnh mới hòa vốn, chốt ở 2R cần hơn 33,3%; spread và phí làm ngưỡng thật cao hơn một chút. Bảng xếp hạng nằm trong bảng phân tích; phiếu lệnh ghi số đo của đúng chiều đang xét.',
         'Khi chỉ nhìn vàng 2024–2026 (0,01 lot): ICT quét thanh khoản thắng 49,5% ở 1R (+0,21 USD mỗi lệnh) và 36,1% ở 2R (+1,28); ICT hồi về khoảng trống giá 48,5% ở 1R (−0,28) và 32,5% ở 2R (−0,48); Elliott 53,8% ở 1R (+1,24) và 37,2% ở 2R (+1,46). Năm mô hình còn lại quanh hòa vốn hoặc lỗ. Trên BTC năm 2026 chỉ Elliott có tổng dương ở 2R (41,1% số lệnh) và âm ở 1R; hai mô hình ICT lỗ ở cả hai cách chốt. Không mô hình nào thắng quá 55% số lệnh. Nút Kỷ luật (mặc định bật) làm trang chỉ chấp nhận và chỉ báo điểm vào mà cả chiều lệnh của phương pháp lẫn bối cảnh giống lúc này (cùng phiên, cùng biên độ) đều có lãi ở nửa học và nửa kiểm, mỗi nửa ít nhất 30 lệnh; các điểm khác vẫn hiện mức giá nhưng ghi rõ là đứng ngoài. Với số đo từ 2015, sau khi sửa lỗi nhìn trước ở lệnh chờ, không chiều nào của tám phương pháp qua được vòng đầu; chỉ còn vài bối cảnh hẹp (một chiều trong một phiên) qua được. Từ ngày 23/11/2026, với ba luật trong sổ (đo từ 2024), Kỷ luật và dòng Bằng chứng tốt nhất còn đòi chiều lệnh đó có lãi ở các năm trước quãng này (2015–2023, ít nhất 30 lệnh): luật bot chiều MUA qua được (1.047 lệnh, +0,52 USD mỗi lệnh), luật bot chiều BÁN không (−1,14), luật ba khung chiều MUA không (−0,20), luật đỉnh/đáy không chiều nào. Kỷ luật không làm phương pháp thắng nhiều hơn; nó chỉ ngăn vào lệnh ở những chỗ số đo đã cho thấy là kém.'),
        ('Công cụ vẽ trên biểu đồ',
         'Thanh công cụ nằm ở mép trái biểu đồ: chọn và di chuyển, đoạn thẳng, mũi tên, tia kéo dài, đường ngang, đường dọc, kênh song song, vùng chữ nhật, elip, Fibonacci thoái lui, vị thế (điểm vào, dừng lỗ, chốt lời kèm tỷ lệ R:R), thước đo giá và thời gian, bút vẽ tự do, ghi chú; bên dưới là đổi màu, hoàn tác (Ctrl+Z), ẩn hoặc hiện, xóa hình đang chọn, xóa tất cả.',
         'Cách dùng: bấm công cụ rồi kéo trên biểu đồ (đường ngang và ghi chú chỉ cần bấm một lần). Với công cụ vị thế, kéo từ điểm vào tới điểm dừng lỗ: kéo xuống là MUA, kéo lên là BÁN, chốt lời tự đặt ở 2R và kéo chỉnh được. Bấm vào một hình để chọn, kéo để dời, kéo các chấm tròn để chỉnh, phím Delete để xóa, Esc để thôi. Hình được lưu theo từng mã ngay trong trình duyệt này (không lên máy chủ), nên đổi khung hay tải lại trang vẫn còn; đổi trình duyệt hoặc xóa dữ liệu trình duyệt thì mất. Với vàng, công cụ vị thế còn ghi khoản lỗ ở 0,01 lot và khối lượng theo mức rủi ro bạn đặt trong ô tính khối lượng.'),
        ('Nhật ký điểm vào',
         'Mỗi khi một luật hoặc một phương pháp có điểm vào còn hiệu lực, máy chủ ghi lại ngay lúc đó: mã, phương pháp, chiều, giá vào, dừng lỗ, các mức chốt lời, phiên và biên độ. Mức giá chốt lúc ghi và không sửa lại. Sau đó mỗi dòng được theo dõi bằng nến 5 phút: lệnh chờ có khớp không, chạm chốt lời hay dừng lỗ trước, hay hết 24 giờ. Từ ngày 22/11/2026, tám phương pháp tùy chọn được ghi theo đúng thứ tự của phép chạy lại: mỗi phương pháp mỗi lúc một lệnh; tín hiệu mới đến lúc lệnh chờ cũ chưa khớp thì dòng cũ đóng với trạng thái Tín hiệu mới thay; tín hiệu đến lúc lệnh trước đã khớp và còn mở thì không ghi. Nhờ vậy số của nhật ký so được với số đo quá khứ. Cùng ngày, máy chủ bắt đầu tự chấm các dòng còn sống mỗi phút; trước đó chúng chỉ được chấm khi có trang đang mở, nên nếu không ai mở trang thì nhật ký ghi thiếu.',
         'Trang Nhật ký ở thanh trên cùng liệt kê toàn bộ điểm vào, lọc được theo mã, phương pháp và trạng thái, có bảng tổng kết theo phương pháp và nút Xem trên biểu đồ cho từng dòng. Thẻ Nhật ký điểm vào trên trang Biểu đồ chỉ hiện sáu dòng mới nhất của mã đang xem; chấm xanh nhấp nháy là điểm vào còn sống (đang chờ khớp hoặc đang mở). Bấm một dòng để xem lại điểm vào đó trên biểu đồ, kèm vạch đánh dấu lúc ghi, lúc khớp và lúc xong. Mỗi phương pháp có một dòng tổng kết: số thắng, số thua, tổng R. Vì ghi trước khi biết kết quả, đây là bằng chứng không chỉnh cho đẹp được, khác với phần chạy lại trên quá khứ. Thắng tính ở 2R với phương pháp tùy chọn và ở TP1 với luật trong sổ; một nến chạm cả dừng lỗ lẫn chốt lời thì tính dừng lỗ. Máy chủ ghi cả khi bạn không mở trang, cho vàng và các mã trong mục nhat_ky.ma của cấu hình; máy chủ tắt thì không ghi. Tệp nằm ở du-lieu/nhat-ky-diem-vao.json. Đây là sổ theo dõi, không phải lệnh thật.'),
        ('Lệnh của tài khoản MT5 trên biểu đồ',
         'Trang Biểu đồ có thẻ Tài khoản MT5: số dư, vốn hiện có, lãi lỗ đang treo, và riêng cho mã đang xem là các lệnh đang mở, lệnh chờ, năm lệnh đã đóng gần nhất. Trên biểu đồ, lệnh đang mở là đường liền kèm lãi lỗ, dừng lỗ và chốt lời là đường gạch, lệnh chờ là đường chấm, lệnh đã đóng là hình thoi xanh (lãi) hoặc đỏ (lỗ) đặt ở giá đóng.',
         'Dữ liệu đọc từ tài khoản demo đang mở trong MT5, cập nhật cùng nhịp với giá. Trang chỉ đọc: không đặt, sửa hay đóng lệnh, không hiện đủ số tài khoản, và từ chối tài khoản không phải demo. Rê chuột vào một đường hay một hình thoi để xem chi tiết. Tắt ô Lệnh đang mở trong Chỉ báo thì các đường này ẩn đi. Mỗi lần trang chỉ đọc được một MT5 đang mở, nên tài khoản demo thứ hai không hiện ở đây.'),
        ('Báo tín hiệu qua TradingView (Pine Script)',
         'Tệp pine/harry-phuong-phap.pine trong thư mục dự án là một chỉ báo Pine Script chứa ba quy tắc của webapp: phá vỡ đỉnh/đáy 8 giờ, ICT quét thanh khoản rồi khoảng trống giá, và hồi về EMA20 theo xu hướng H1. Nó vẽ mức vào, dừng lỗ, chốt lời và có sẵn các điều kiện để đặt Alert.',
         'Cách dùng: mở TradingView, vào Pine Editor, dán toàn bộ tệp, bấm Add to chart trên khung 15 phút, rồi bấm Alert và chọn điều kiện. Khi đó TradingView báo về điện thoại ngay cả lúc máy tính và webapp đang tắt. Bản này chưa được chạy thử trên TradingView; nếu Pine Editor báo lỗi thì cần sửa theo dòng lỗi. Nến của TradingView có thể lệch nhẹ so với nến của sàn trong MT5 nên tín hiệu hai bên có thể khác nhau ở vài nến. Elliott, Wyckoff, Price Action và Fibonacci chưa có trong tệp này.'),
        ('Các công cụ mã nguồn mở đã xem xét',
         'Bốn công cụ hay được nhắc tới: Backtesting.py, VectorBT, TradingView Pine Script và QuantConnect LEAN. Đã xem giấy phép, dung lượng và các gói phụ thuộc của từng cái trước khi quyết định.',
         'Pine Script: đã làm, không cần cài gì. Backtesting.py (giấy phép AGPL-3.0, gói 186 KB, cần thêm thư viện vẽ Bokeh): đã cài bản 0.6.6 theo quyết định của chủ dự án và dùng làm bộ chấm thứ hai, độc lập, để đối chiếu phép chạy lại của webapp. Lần đối chiếu đầu trên vàng năm 2026 (năm phương pháp vào theo giá thị trường, spread và phí bằng 0 ở cả hai bên, 2.126 lệnh): cùng nến vào ở cả 2.126 lệnh, cùng điểm thoát ở 2.103 lệnh. 23 lệnh khác nhau đều rơi vào nến mở cửa sau cuối tuần hoặc sau giờ nghỉ hằng ngày, khi giá mở nhảy qua luôn mức dừng lỗ hoặc chốt lời: webapp tính thoát đúng ở mức đã đặt, Backtesting.py tính thoát ở giá mở. Ở 11 lệnh nhảy qua dừng lỗ, webapp đã tính nhẹ hơn thực tế tổng cộng 9,6R. Phép chấm của webapp đã được sửa theo đó: nến mở cửa đã nằm ngoài dừng lỗ thì thoát ở giá mở, tức lỗ hơn 1R, như lệnh dừng ngoài thực tế; nhật ký điểm vào và công cụ nghiên cứu cũng sửa như vậy. Riêng khi mở cửa nhảy qua chốt lời, webapp cố ý vẫn chỉ tính ở mức chốt lời, không cộng phần nhảy có lợi. Đối chiếu lại sau khi sửa, ba năm 2024–2026: 6.900 lệnh, cùng nến vào ở cả 6.900, cùng điểm thoát ở 6.871 (99,6%); 28 lệnh khác là nhảy qua chốt lời (khác có chủ ý), 1 lệnh hết 24 giờ rơi đúng vào một quãng tệp nến bị thiếu 78 phút (4/12/2025); không còn chỗ khác nào chưa giải thích được. Điều này chỉ xác nhận phép chấm không sai; nó không làm phương pháp nào tốt hơn. Lệnh chờ (ICT, ICT hồi về khoảng trống giá, Fibonacci) được đối chiếu ngày 22/11/2026, và lần đầu hai bộ chấm lệch nhau lớn: trên vàng 2026 không tính chi phí, webapp ra +2.027 giá cho ICT quét thanh khoản và +1.322 cho ICT hồi về khoảng trống giá, còn Backtesting.py ra +1.364 và −55. Nguyên nhân là một lỗi nhìn trước trong phép chấm của webapp: khi một tín hiệu mới đến lúc lệnh chờ cũ chưa khớp, webapp vẫn cho lệnh cũ đủ 4 giờ để khớp, và nếu về sau nó khớp thì bỏ tín hiệu mới; tức là chọn lệnh dựa trên điều lúc đó chưa ai biết được. Đã sửa: tín hiệu mới đến thì lệnh chờ cũ chưa khớp bị hủy, đúng như trang Biểu đồ chỉ hiện tín hiệu mới nhất. Cùng ngày, sửa thêm một chỗ lệch với trang Biểu đồ: tín hiệu lệnh chờ mà giá đã ở bên kia mức chờ ngay lúc tín hiệu đến thì trang báo là đã qua, còn phép chấm trước đó vẫn tính một lệnh khớp ở mức chờ (khoảng 11% số lệnh Fibonacci); nay cả phép chấm của webapp lẫn phép chấm riêng từng tín hiệu đều bỏ các tín hiệu đó. Đối chiếu lại 2024–2026 sau cả hai lần sửa: 3.235 lệnh chờ, cùng nến khớp ở cả 3.235, giống hệt ở 3.193 (98,7%); 11 lệnh có nến về sau mở cửa nhảy qua mức chờ (webapp tính khớp ở mức chờ, Backtesting.py ở giá mở tốt hơn), 20 lệnh có nến khớp chạm luôn dừng lỗ (webapp tính dừng lỗ ngay, thư viện không xét được trong nến khớp), 11 lệnh nhảy qua chốt lời; không còn chỗ nào chưa giải thích được. Sau khi sửa, số đo của hai mô hình ICT giảm rõ (xem từng mục phương pháp). Năm phương pháp vào theo giá thị trường, phần nghiên cứu chấm riêng từng tín hiệu và mô hình chấm điểm không dính lỗi nhìn trước. Lần sửa thứ hai có đổi phần nghiên cứu và mô hình (chủ yếu ở Fibonacci); cả hai đã chạy lại và các con số trong trang này là số mới. Webapp không dùng thư viện này lúc chạy; nó chỉ nằm trong công cụ đối chiếu. Giấy phép AGPL-3.0 chỉ đặt ra nghĩa vụ khi đem phần mềm phát hành hoặc cho người khác dùng qua mạng. Chạy lại: python -X utf8 cong-cu/doi_chieu_backtesting.py. VectorBT (cần thêm khoảng mười gói như matplotlib, plotly, ipywidgets): công dụng chính là thử hàng nghìn bộ tham số, đúng việc mà số đo 11 năm cho thấy dẫn tới con số đẹp nhưng không đứng vững; không khuyên dùng. QuantConnect LEAN: bộ máy viết bằng C#, chạy qua Docker nặng nhiều GB và cần dữ liệu theo định dạng riêng; quá nặng so với một webapp chạy trên máy cá nhân; không khuyên dùng.'),
        ('Nến cả năm',
         'Biểu đồ nạp 900 nến gần nhất mỗi 5 giây để nhẹ, và nạp thêm một lần toàn bộ nến từ ngày 1 tháng 1 của năm đang xem để bạn kéo lùi được.',
         'Vàng lấy từ tệp nến 1 phút của dự án; mã khác lấy từ MT5 demo đang mở. Mỗi khung tối đa 40.000 nến, nên M5 chỉ lùi được vài tháng; muốn xem cả năm hãy chọn M15 trở lên. Dòng chữ dưới biểu đồ ghi rõ nến có từ ngày nào.'),
        ('Phân tích tự chạy và báo điểm vào',
         'Từ lúc mở trang, phần phân tích tự chạy lại 15 giây một lần khi có giá trực tiếp (một phút một lần khi không). Khi một phương pháp đang bật có điểm vào còn hiệu lực, trang hiện một băng phía trên biểu đồ, một thông báo nổi, và nhắc lại mỗi 5 phút chừng nào điểm vào còn sống.',
         'Trang chỉ báo, không đặt lệnh, và chỉ báo khi tab biểu đồ của mã đó đang mở. Mỗi lần báo ghi tỷ lệ có lãi đã đo. Chưa mô hình nào trong dữ liệu đạt tỷ lệ thắng 90%: cao nhất là luật ba khung 82,4%, nhưng luật đó thắng nhỏ thua lớn nên trung bình mỗi lệnh chỉ +0,41 USD. Tỷ lệ thắng cao không đồng nghĩa với có lãi.'),
    ]),
    ('Đọc trang Tổng quan', [
        ('R',
         'Một R là số tiền bạn chấp nhận mất nếu lệnh chạm SL. Lãi lỗ tính theo R giúp so các lệnh có SL khác nhau.',
         'Sổ luật đỉnh/đáy và phần chấm điểm AI tính theo R. Bot tín hiệu đặt TP1 ở 0,5R.'),
        ('Tỷ lệ thắng hòa vốn',
         'Bằng SL chia cho tổng SL và TP. Luật chốt 5 dừng 20 cần thắng 20 ÷ 25 = 80% mới hòa vốn, chưa kể phí.',
         'Trong sổ của bạn, cách chốt ở 0,1R thắng khoảng 88% số lệnh nhưng tổng vẫn âm, vì một lệnh thua xóa khoảng mười lăm lệnh thắng.'),
        ('Lãi gộp, lỗ gộp và hệ số lợi nhuận',
         'Lãi gộp là tổng các lệnh thắng, lỗ gộp là tổng các lệnh thua. Hệ số lợi nhuận bằng lãi gộp chia lỗ gộp; dưới 1 là lỗ.',
         'Tiêu chí nghiệm thu của dự án đòi hệ số lợi nhuận từ 1,3. Khi chưa có lệnh thua, trang ghi "chưa tính được" chứ không điền số.'),
        ('Sụt vốn lớn nhất và hệ số hồi phục',
         'Sụt vốn lớn nhất là quãng tụt sâu nhất từ một đỉnh vốn. Hệ số hồi phục bằng lãi ròng chia cho sụt vốn lớn nhất.',
         'Trang tính sụt vốn trên đường vốn EA ghi ở mỗi sự kiện, gồm cả lúc đang giữ lệnh. Có nạp hoặc rút tiền demo thì chỉ tính từ lần nạp/rút gần nhất.'),
        ('Lãi lỗ đang treo',
         'Lãi lỗ của lệnh còn mở. Nó thay đổi theo giá và chưa phải tiền đã chốt.',
         'Trang tách riêng phần này: vốn demo có thể tăng trong khi lãi lỗ đã đóng vẫn âm.'),
    ]),
    ('Vốn và rủi ro', [
        ('Lot và giá trị mỗi giá',
         'Với vàng trên sàn của bạn, 1 lot là 100 ounce. Lệnh nhỏ nhất 0,01 lot lãi hoặc lỗ 1 USD cho mỗi 1 giá vàng di chuyển.',
         'SL 20 giá ở 0,01 lot là 20 USD. Với vốn 200 USD đó là 10% vốn cho một lệnh.'),
        ('Rủi ro mỗi lệnh',
         'Phần vốn mất đi nếu lệnh chạm SL. Rủi ro càng nhỏ thì tài khoản chịu được chuỗi thua càng dài.',
         'Preset demo của các EA dùng 0,25% đến 0,5% mỗi lệnh. Tài liệu của bạn ghi cần từ 1.200 USD để giữ 0,5% với SL 6 giá ở 0,01 lot.'),
        ('Vốn nhỏ và sụt vốn',
         'Khi lệnh nhỏ nhất đã vượt mức rủi ro cho phép, tài khoản không còn cách nào giảm rủi ro ngoài việc không vào lệnh.',
         'Bảng vòng 4 của bot: ở 0,01 lot cố định, sụt vốn lớn nhất của các cách chốt là 159 đến 260 USD; với vốn 200 USD, 16% đến 32% số điểm bắt đầu trong quá khứ mất quá nửa vốn trong 180 ngày.'),
    ]),
    ('Mức độ tin được của một con số', [
        ('Tin Mỹ ra thì giá vàng đi chiều nào: đo được gì, không đo được gì (ngày 25/11/2026)',
         'Trên 3.994 lần tin USD mức cao ra từ 2015 tới 11/2026, giá vàng chạy mạnh nhất sau NFP, họp báo và quyết định lãi suất của Fed, CPI: 15 phút sau tin, '
         'trung vị khoảng 4,5 đến 5,6 giá, khoảng một phần tư số lần chạy quá 10 giá. Tin dầu thô EIA và đấu giá trái phiếu gần như không làm vàng chạy. '
         'Bốn quy tắc đoán chiều trước tin (đi tiếp hay đi ngược chiều 60 phút trước tin, theo xu hướng H1) và đi theo chiều phút đầu sau tin đều đúng 48,6 đến 51,4% '
         'ở phần kiểm tra 2022–2026, tức như tung đồng xu. Chiều giá sau tin phụ thuộc vào độ bất ngờ (số thực tế so với dự báo), con số chỉ có khi tin đã ra; '
         'lịch trên máy chưa có hai con số này. Script cong-cu/mql5/XuatLichKinhTe.mq5 (chủ dự án tự chạy trong MT5) xuất chúng để đo tiếp.',
         'Trang Biểu đồ ghi tên tin USD mạnh kế tiếp và giá thường chạy bao xa sau đúng loại tin đó (số từ 2024), kèm câu "chiều không đoán được". '
         'Trước khi đo, nến vàng nhiều năm được sửa lệch giờ: từ 2015 tới 02/2024 nhãn giờ sớm 1 giờ trong mùa đông châu Âu, 02–05/2024 trễ 1 giờ '
         '(so_cong_khai/sua_gio.py); né tin, bộ lọc tin, khung giờ của luật và nến H1, H4 trước đó đã lệch 1 giờ ở các quãng này, và mọi số đo đã được chạy lại. '
         'Chạy lại: python -X utf8 cong-cu/phan_ung_tin.py'),
        ('Kiểm lại quá khứ, chạy bóng, demo, tiền thật',
         'Kiểm lại quá khứ chạy luật trên giá cũ. Chạy bóng ghi tín hiệu theo thời gian thực nhưng không đặt lệnh. Demo đặt lệnh bằng tiền ảo. Chỉ tiền thật mới có đủ trượt giá và tâm lý.',
         'Mọi con số trong webapp này thuộc ba loại đầu, và được gắn nhãn TÍN HIỆU, CHẠY BÓNG hoặc DEMO. Dự án đang ghi chỉ chạy demo.'),
        ('Dữ liệu ngoài mẫu và chọn tham số',
         'Thử nhiều tổ hợp rồi chọn cái đẹp nhất luôn cho kết quả lạc quan hơn thật. Dữ liệu ngoài mẫu là quãng giá chưa từng dùng để chọn tham số.',
         'Báo cáo của bạn ghi cách kiểm trước khi chạy, thử phí cao hơn 50% và tham số lân cận. Theo README, chưa ứng viên chiến lược nào đạt toàn bộ tiêu chí.'),
        ('Cỡ mẫu',
         'Vài chục lệnh không nói được gì: 24 lệnh thắng liên tiếp vẫn có thể là may. Hệ thống của bạn đặt mốc 300 lệnh cho luật ba khung và 30 lệnh đã đóng cho bot.',
         'Trang tự ghi "chưa đủ để nhận xét" khi dưới ngưỡng.'),
    ]),
]

CSS = """
.kt{display:grid;gap:14px;margin-top:8px}
.kt article{display:grid;grid-template-columns:230px 1fr 1fr;gap:6px 22px;padding:12px 0;border-bottom:1px solid var(--line)}.kt article:last-child{border-bottom:0}
.kt h4{margin:0;font-size:14px;font-weight:700;color:var(--ink)}.kt p{margin:0;font-size:13px;color:var(--ink2)}
.kt p.ban{color:var(--ink)}.kt p.ban::before{content:"Trong hệ thống của bạn";display:block;font-size:11.5px;font-weight:700;color:var(--mute);margin-bottom:2px}
.kt p.la::before{content:"Nghĩa là gì";display:block;font-size:11.5px;font-weight:700;color:var(--mute);margin-bottom:2px}
@media(max-width:860px){.kt article{grid-template-columns:1fr}}
.muc{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0}.muc a{font-size:12.5px;font-weight:600;color:var(--ink2);border:1px solid var(--line);border-radius:6px;padding:4px 9px;text-decoration:none;background:var(--card)}
.muc a:hover,.muc a:focus-visible{border-color:var(--series);color:var(--ink);outline:none}
"""


TEP_DU_LIEU_MOI = duong.goc_du_lieu() / 'out' / 'du-lieu-moi.json'
TEN_KET = {'chua_du': 'chưa đủ lệnh', 'co_lai': 'vẫn có lãi', 'lo_ro': 'đang lỗ rõ', 'chua_ro': 'chưa phân định'}


def du_lieu_moi_html(tep: Path | None = None) -> str:
    """Khối 'Kiểm trên dữ liệu mới' đọc từ out/du-lieu-moi.json (do cong-cu/do_lai_du_lieu_moi.py ghi); chưa có tệp thì hướng dẫn cách chạy."""
    tep = tep or TEP_DU_LIEU_MOI
    dau = '<section class="card" id="du-lieu-moi"><h2>Kiểm trên dữ liệu mới</h2>'
    try:
        kq = json.loads(tep.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return (dau + '<p class="why">Chưa chạy lần nào. Chạy <b>DO_LAI_DU_LIEU_MOI.bat</b> (hoặc <code>python -X utf8 cong-cu/do_lai_du_lieu_moi.py</code>) '
                'khoảng mỗi tháng: nó đo lại các luật đã chốt ngày 24/11/2026 chỉ trên giá từ 25/11/2026 trở đi, phần mà chưa phép đo nào nhìn thấy.</p></section>')
    so = lambda v, d=3: '—' if v is None else (f'{v:+.{d}f}' if d else f'{v:.1f}').replace('.', ',')      # noqa: E731
    luc = datetime.fromisoformat(kq['luc']).astimezone(timezone(timedelta(hours=7)))
    tu, den = datetime.fromisoformat(kq['tu']), datetime.fromisoformat(kq['den'])
    pham_vi = f'Giá từ {tu:%d/%m/%Y} đến {den:%d/%m/%Y} ({kq["so_ngay"]} ngày)' if den > tu else f'Chưa có giá mới sau mốc {tu:%d/%m/%Y} (giá trên máy tới {den:%d/%m/%Y})'
    h = [dau, f"<p class=\"why\">{pham_vi}, "
         f"đo lúc {luc:%H:%M %d/%m/%Y}. Luật và công thức giữ nguyên như ngày 24/11/2026; kết luận theo luật ghi trước: dưới 30 lệnh thì chưa kết luận, "
         'còn lại theo khoảng tin cậy 90% của lãi mỗi lệnh. "Kỳ vọng" là mức đã đo ở phần kiểm 2022–2026. Chạy lại: DO_LAI_DU_LIEU_MOI.bat.</p>',
         '<div class="wrap"><table><thead><tr><th>Nhóm</th><th>Luật</th><th class="r">Lệnh</th><th class="r">Thắng</th><th class="r">R mỗi lệnh</th>'
         '<th class="r">Kỳ vọng</th><th>Kết luận</th></tr></thead><tbody>']
    for x in kq.get('muc', []):
        ket = TEN_KET.get(x['ket'], x['ket']) + (' · kém kỳ vọng rõ' if x.get('kem_ky_vong') else '')
        lop = 'gain' if x['ket'] == 'co_lai' else 'loss' if x['ket'] == 'lo_ro' or x.get('kem_ky_vong') else ''
        h.append(f"<tr><td>{escape(x['nhom'])}</td><td>{escape(x['ten'])}</td><td class=\"r\">{x['n']}</td>"
                 f"<td class=\"r\">{so(x['thang'], 0) + '%' if x['thang'] is not None else '—'}</td><td class=\"r\">{so(x['r_tb'])}</td>"
                 f"<td class=\"r\">{so(x['ky_vong'])}</td><td class=\"{lop}\">{escape(ket)}</td></tr>")
    h.append('</tbody></table></div>')
    t = (kq.get('nhat_ky') or {}).get('Tất cả')
    if t and t['n']:
        h.append(f"<p class=\"why\">Nhật ký điểm vào (lệnh thật đã có kết quả, không tính dòng ghi trùng): {t['n']} lệnh, thắng {t['thang']} "
                 f"({so(t['thang'] / t['n'] * 100, 0)}%), tổng {so(t['tong_r'], 2)}R. Chi tiết ở trang Nhật ký.</p>")
    return '\n'.join(h) + '</section>'


_RIENG_NHOM = {'Các luật của bạn', 'Đọc trang Tổng quan'}
_RIENG = re.compile(r'\bbot\b|[Hh]ệ thống của bạn|[Ll]uật của bạn')


def muc_chia_se() -> list:
    """Các mục cho bản chia sẻ: chỉ phần giải thích chung (thuật ngữ nghĩa là gì). Bỏ nhóm luật riêng, các ghi chú nghiên cứu có ngày,
    và mọi mục nhắc tới bot hay hệ thống riêng của chủ dự án, để gói chia sẻ không mang theo chiến lược của họ."""
    out = []
    for nhom, muc in MUC:
        if nhom in _RIENG_NHOM:
            continue
        giu = [(t, a, '') for t, a, b in muc if not re.search(r'ngày \d|11 năm|mô hình', t) and not _RIENG.search(t + ' ' + a)]
        if giu:
            out.append((nhom, giu))
    return out


def trang_kien_thuc(ten: str, chia_se: bool = False) -> str:
    """Trang Kiến thức. `chia_se`: bản chia sẻ cho người khác (máy không có luật riêng): chỉ phần giải thích chung."""
    ds = muc_chia_se() if chia_se else MUC
    doc = ('<p class="note"><b>Đọc trước:</b> mỗi mục giải thích một thuật ngữ hoặc một phần của webapp. Đây là giải thích, không phải lời khuyên đầu tư.</p>'
           if chia_se else
           '<p class="note"><b>Đọc trước:</b> mỗi mục gồm hai phần: thuật ngữ nghĩa là gì, và nó đang được dùng thế nào trong hệ thống của bạn, kèm con số từ chính báo cáo của bạn. '
           'Đây là giải thích, không phải lời khuyên đầu tư.</p>')
    out = ['<!doctype html><html lang="vi" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           f'{trang.KHOI_TAO_NEN}{trang.BIEU_TUONG}<title>Kiến thức · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
           trang.thanh_dau(ten, 'kien-thuc', '<button id="theme" type="button">Nền tối</button>') + '<main>',
           f'<div class="top"><div><h1>Kiến thức</h1></div><div class="stamp">{sum(len(m) for _, m in ds)} mục' + ('' if chia_se else '<br>số liệu theo tài liệu tới 20/11/2026') + '</div></div>',
           doc,
           '<nav class="muc">' + ('' if chia_se else '<a href="#du-lieu-moi">Kiểm trên dữ liệu mới</a>') + ''.join(f'<a href="#n{i}">{escape(n)}</a>' for i, (n, _) in enumerate(ds)) + '</nav>',
           '' if chia_se else du_lieu_moi_html()]
    for i, (nhom, muc) in enumerate(ds):
        out.append(f'<section class="card" id="n{i}"><h2>{escape(nhom)}</h2><div class="kt">')
        out += [f'<article><h4>{escape(t)}</h4><p class="la">{escape(a)}</p>' + (f'<p class="ban">{escape(b)}</p>' if b else '') + '</article>' for t, a, b in muc]
        out.append('</div></section>')
    out.append('<footer>' + ('' if chia_se else 'Các con số ở trang này chép từ tài liệu và báo cáo trong hai dự án EA Promax và Tele dự báo. Khi bạn đổi luật hoặc đo lại, '
               'hãy sửa mục tương ứng trong tệp so_cong_khai/kien_thuc.py. ') + escape(trang.MIEN_TRU) + f'</footer></main><script>{trang.JS}</script></body></html>')
    return '\n'.join(out)
