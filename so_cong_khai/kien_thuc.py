"""Trang Kiến thức: giải thích từng chỉ báo, luật và chỉ số đang dùng trong webapp, kèm con số của chính hệ thống này.
Số liệu lấy từ tài liệu và báo cáo trong EA Promax và Tele dự báo, đọc tới 20/11/2026; khi luật đổi thì phải sửa lại ở đây."""
from __future__ import annotations

import re

import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from . import trang

# (nhóm, [(thuật ngữ, nghĩa là gì, trong hệ thống của bạn)])
# Bản chia sẻ: chỉ phần giải thích chung.
MUC = [('Đọc biểu đồ',
  [('Nến đã đóng và nến đang chạy',
    'Một cây nến chỉ có giá mở, cao, thấp, đóng cố định sau khi hết khung thời gian của nó. Trước lúc đó nó còn thay đổi.',
    ''),
   ('Bid và Ask', 'Bid là giá bạn bán được, Ask là giá bạn mua được. Khoảng cách giữa hai giá là spread, tức chi phí của mỗi lệnh.', ''),
   ('EMA20 và EMA50', 'Đường trung bình động lũy thừa của 20 và 50 nến gần nhất. EMA20 nằm trên EMA50 thì đà ngắn hạn đang lên, và ngược lại.', ''),
   ('Dải Bollinger', 'Đường trung bình 20 nến cộng trừ hai lần độ lệch chuẩn. Giá ra ngoài dải nghĩa là đang chạy mạnh hơn mức thường.', ''),
   ('RSI14', 'Chỉ số sức mạnh tương đối, từ 0 đến 100, tính theo cách của Wilder. Trên 70 thường gọi là quá mua, dưới 30 là quá bán.', ''),
   ('ATR14', 'Biên độ dao động trung bình của 14 nến. Dùng làm thước đo: dừng lỗ, vùng giá và bộ lọc thường tính theo bội số của ATR.', ''),
   ('Hỗ trợ và kháng cự 2 giờ', 'Đáy thấp nhất và đỉnh cao nhất của 2 giờ gần đây. Giá hay phản ứng quanh các mức này.', ''),
   ('Khoảng trống giá (FVG) và khối lệnh',
    'FVG là khoảng giá mà ba nến liên tiếp để hở, cho thấy giá chạy quá nhanh. Khối lệnh là cây nến cuối cùng ngược chiều trước một cú chạy mạnh.',
    ''),
   ('Giờ tin USD mạnh', 'Các tin như bảng lương Mỹ, lạm phát, quyết định lãi suất làm vàng giật mạnh và spread giãn rộng.', '')]),
 ('Đọc bảng phân tích điểm vào',
  [('Nút Phân tích điểm vào',
    'Bấm nút thì trang gọi bốn luật đã viết sẵn và ghi ra mức giá mỗi luật sẽ dùng nếu ra lệnh ngay lúc đó: chiều, giá vào, dừng lỗ, các mức chốt '
    'lời.',
    ''),
   ('"Còn hiệu lực" và "Chỉ để tham khảo"',
    'Một phương án còn hiệu lực khi luật thật cũng sẽ vào lệnh đúng lúc đó. Quá hạn thì mức giá chỉ còn để xem luật nghĩ gì, không phải tín hiệu.',
    ''),
   ('Bội số R', 'R là khoảng cách từ giá vào tới dừng lỗ. TP ở 1,5R nghĩa là nếu chạm thì lãi gấp rưỡi phần chấp nhận mất.', ''),
   ('Vùng đỏ, vùng xanh trên biểu đồ',
    'Khi vẽ một phương án, vùng đỏ là khoảng từ giá vào tới dừng lỗ (phần có thể mất), vùng xanh là khoảng tới mức chốt lời xa nhất.',
    ''),
   ('Kiểm chứng lịch sử',
    'Chạy lại đúng luật trên nến 1 phút của kho nến gần nhất để xem những lần trước luật ra lệnh cùng chiều thì kết thúc ra sao.',
    ''),
   ('Bối cảnh giống lúc này, nửa học và nửa kiểm',
    'Một bộ lọc trông đẹp trên toàn bộ dữ liệu có thể chỉ là trùng hợp. Cách thử đơn giản là cắt dữ liệu theo thời gian: tìm trên phần đầu, rồi xem '
    'phần sau có còn đúng không.',
    '')]),
 ('Các phương pháp phân tích tùy chọn',
  [('Vì sao phải viết thành quy tắc máy',
    'Phần lớn trường phái (SMC/ICT, Wyckoff, Price Action, Elliott) được dạy bằng ví dụ và phán đoán. Hai người nhìn cùng một biểu đồ có thể vẽ khác '
    'nhau, nên không đo được.',
    ''),
   ('ICT/SMC: quét thanh khoản và khoảng trống giá',
    'Giá thường quét qua đáy hoặc đỉnh gần nhất (nơi nhiều lệnh dừng lỗ nằm) rồi đảo chiều mạnh, để lại một khoảng trống giá (FVG). Vào khi giá hồi '
    'về giữa khoảng trống đó.',
    ''),
   ('ICT/SMC: hồi về khoảng trống giá sau khi phá cấu trúc',
    'Mô hình ICT thứ hai: khi H1 có xu hướng và một nhịp bật mạnh phá cấu trúc theo xu hướng, giá thường hồi về khoảng trống giá mà nhịp bật để lại '
    'rồi mới đi tiếp.',
    ''),
   ('Bản đồ ICT trên biểu đồ',
    'Khi nhóm ICT/SMC đang bật, trang tự vẽ lên biểu đồ: BSL và SSL (thanh khoản trên và dưới, tức đỉnh và đáy 5 giờ), khoảng trống giá (FVG) chưa '
    'lấp gần giá nhất, các lần phá cấu trúc (BOS, CHoCH), các điểm quét thanh khoản (dấu ✕), EQ 50% (mức giữa biên độ 24 giờ: premium ở trên, '
    'discount ở dưới), PDH và PDL (đỉnh, đáy hôm trước). Rê chuột vào từng ghi chú để xem giải thích cụ thể.',
    ''),
   ('Wyckoff: spring và upthrust',
    'Sau một quãng đi ngang (tích lũy hoặc phân phối), giá đâm thủng biên vùng để gom thanh khoản rồi quay lại bên trong. Bản gốc cần khối lượng để '
    'xác nhận.',
    ''),
   ('Price Action: pin bar và nến nhấn chìm',
    'Đọc trực tiếp hình dạng nến tại vùng quan trọng: pin bar (đuôi dài, thân nhỏ) và nến nhấn chìm cho thấy một phe vừa bị đẩy lùi.',
    ''),
   ('Fibonacci 61,8% (phần đo được của sóng Elliott)',
    'Sau một nhịp đẩy, giá thường hồi về một phần rồi mới đi tiếp; mức 61,8% là mức hay được dùng nhất. Đếm sóng Elliott thì mỗi người một cách, '
    'không viết được thành quy tắc nhất quán.',
    ''),
   ('Sóng Elliott: vào sóng 3',
    'Lý thuyết Elliott cho rằng xu hướng đi thành năm sóng, trong đó sóng 3 thường mạnh nhất. Đếm đủ năm sóng thì mỗi người một cách; phần viết được '
    'thành quy tắc máy là cặp sóng 1–2 và điểm vào sóng 3.',
    ''),
   ('Vì sao tỷ lệ thắng thấp, và bậc thang chốt lời',
    'Tỷ lệ thắng không phải thước đo chất lượng của điểm vào; nó đi liền với mức chốt lời. Chốt ở 2R nghĩa là giá phải đi xa gấp đôi khoản rủi ro '
    'trước khi quay lại chạm dừng lỗ, nên dù điểm vào thế nào cũng chỉ khoảng một phần ba số lệnh tới nơi. Chốt gần hơn thì thắng nhiều lần hơn, '
    'nhưng mỗi lần thắng nhỏ hơn.',
    ''),
   ('Phá vỡ và hồi về EMA',
    'Phá vỡ: vào theo chiều nến đóng vượt đỉnh hoặc thủng đáy. Hồi về EMA: trong xu hướng, vào khi giá chạm đường trung bình rồi bật lại.',
    ''),
   ('Liên thị trường và vĩ mô',
    'Nhìn dòng tiền giữa các thị trường: USD mạnh lên thường đè giá vàng, lãi suất và lợi suất trái phiếu quyết định hướng dài hạn. Phương pháp này '
    'không cho điểm vào chính xác.',
    ''),
   ('Số đo trên mã khác vàng (BTC, EURUSD…)',
    'Với mã khác vàng, mỗi phương pháp được chạy lại trên nến 5 phút của chính mã đó từ đầu năm, đọc từ MT5 demo. Số đo hiện trong từng thẻ phương '
    'án và trong lời báo điểm vào.',
    ''),
   ('Thử nhiều phương pháp thì dễ gặp may',
    'Thử tám mô hình mà vài cái có lãi thì chưa chắc chúng tốt thật: càng thử nhiều, càng dễ có một cái đẹp do trùng hợp.',
    '')]),
 ('Biểu đồ chạy theo giá trực tiếp',
  [('Tỷ lệ thắng ở 1R và 2R, bảng xếp hạng, chế độ Kỷ luật',
    'Mỗi phương pháp được chạy lại hai lần trên cùng dữ liệu: một lần chốt lời ở 1R (lãi bằng rủi ro), một lần chốt ở 2R. Chốt ở 1R phải thắng hơn '
    '50% số lệnh mới hòa vốn, chốt ở 2R cần hơn 33,3%; spread và phí làm ngưỡng thật cao hơn một chút. Bảng xếp hạng nằm trong bảng phân tích; phiếu '
    'lệnh ghi số đo của đúng chiều đang xét.',
    ''),
   ('Công cụ vẽ trên biểu đồ',
    'Thanh công cụ nằm ở mép trái biểu đồ: chọn và di chuyển, đoạn thẳng, mũi tên, tia kéo dài, đường ngang, đường dọc, kênh song song, vùng chữ '
    'nhật, elip, Fibonacci thoái lui, vị thế (điểm vào, dừng lỗ, chốt lời kèm tỷ lệ R:R), thước đo giá và thời gian, bút vẽ tự do, ghi chú; bên dưới '
    'là đổi màu, hoàn tác (Ctrl+Z), ẩn hoặc hiện, xóa hình đang chọn, xóa tất cả.',
    ''),
   ('Nhật ký điểm vào',
    'Mỗi khi một luật hoặc một phương pháp có điểm vào còn hiệu lực, máy chủ ghi lại ngay lúc đó: mã, phương pháp, chiều, giá vào, dừng lỗ, các mức '
    'chốt lời, phiên và biên độ. Mức giá chốt lúc ghi và không sửa lại. Sau đó mỗi dòng được theo dõi bằng nến 5 phút: lệnh chờ có khớp không, chạm '
    'chốt lời hay dừng lỗ trước, hay hết 24 giờ. Từ ngày 22/11/2026, tám phương pháp tùy chọn được ghi theo đúng thứ tự của phép chạy lại: mỗi '
    'phương pháp mỗi lúc một lệnh; tín hiệu mới đến lúc lệnh chờ cũ chưa khớp thì dòng cũ đóng với trạng thái Tín hiệu mới thay; tín hiệu đến lúc '
    'lệnh trước đã khớp và còn mở thì không ghi. Nhờ vậy số của nhật ký so được với số đo quá khứ. Cùng ngày, máy chủ bắt đầu tự chấm các dòng còn '
    'sống mỗi phút; trước đó chúng chỉ được chấm khi có trang đang mở, nên nếu không ai mở trang thì nhật ký ghi thiếu.',
    ''),
   ('Lệnh của tài khoản MT5 trên biểu đồ',
    'Trang Biểu đồ có thẻ Tài khoản MT5: số dư, vốn hiện có, lãi lỗ đang treo, và riêng cho mã đang xem là các lệnh đang mở, lệnh chờ, năm lệnh đã '
    'đóng gần nhất. Trên biểu đồ, lệnh đang mở là đường liền kèm lãi lỗ, dừng lỗ và chốt lời là đường gạch, lệnh chờ là đường chấm, lệnh đã đóng là '
    'hình thoi xanh (lãi) hoặc đỏ (lỗ) đặt ở giá đóng.',
    ''),
   ('Báo tín hiệu qua TradingView (Pine Script)',
    'Tệp pine/harry-phuong-phap.pine trong thư mục dự án là một chỉ báo Pine Script chứa ba quy tắc của webapp: phá vỡ đỉnh/đáy 8 giờ, ICT quét '
    'thanh khoản rồi khoảng trống giá, và hồi về EMA20 theo xu hướng H1. Nó vẽ mức vào, dừng lỗ, chốt lời và có sẵn các điều kiện để đặt Alert.',
    ''),
   ('Các công cụ mã nguồn mở đã xem xét',
    'Bốn công cụ hay được nhắc tới: Backtesting.py, VectorBT, TradingView Pine Script và QuantConnect LEAN. Đã xem giấy phép, dung lượng và các gói '
    'phụ thuộc của từng cái trước khi quyết định.',
    ''),
   ('Nến cả năm',
    'Biểu đồ nạp 900 nến gần nhất mỗi 5 giây để nhẹ, và nạp thêm một lần toàn bộ nến từ ngày 1 tháng 1 của năm đang xem để bạn kéo lùi được.',
    ''),
   ('Phân tích tự chạy và báo điểm vào',
    'Từ lúc mở trang, phần phân tích tự chạy lại 15 giây một lần khi có giá trực tiếp (một phút một lần khi không). Khi một phương pháp đang bật có '
    'điểm vào còn hiệu lực, trang hiện một băng phía trên biểu đồ, một thông báo nổi, và nhắc lại mỗi 5 phút chừng nào điểm vào còn sống.',
    '')]),
 ('Vốn và rủi ro',
  [('Lot và giá trị mỗi giá',
    'Với vàng trên sàn của bạn, 1 lot là 100 ounce. Lệnh nhỏ nhất 0,01 lot lãi hoặc lỗ 1 USD cho mỗi 1 giá vàng di chuyển.',
    ''),
   ('Rủi ro mỗi lệnh', 'Phần vốn mất đi nếu lệnh chạm SL. Rủi ro càng nhỏ thì tài khoản chịu được chuỗi thua càng dài.', ''),
   ('Vốn nhỏ và sụt vốn', 'Khi lệnh nhỏ nhất đã vượt mức rủi ro cho phép, tài khoản không còn cách nào giảm rủi ro ngoài việc không vào lệnh.', '')]),
 ('Mức độ tin được của một con số',
  [('Kiểm lại quá khứ, chạy bóng, demo, tiền thật',
    'Kiểm lại quá khứ chạy luật trên giá cũ. Chạy bóng ghi tín hiệu theo thời gian thực nhưng không đặt lệnh. Demo đặt lệnh bằng tiền ảo. Chỉ tiền '
    'thật mới có đủ trượt giá và tâm lý.',
    ''),
   ('Dữ liệu ngoài mẫu và chọn tham số',
    'Thử nhiều tổ hợp rồi chọn cái đẹp nhất luôn cho kết quả lạc quan hơn thật. Dữ liệu ngoài mẫu là quãng giá chưa từng dùng để chọn tham số.',
    '')])]

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


TEP_DU_LIEU_MOI = Path(__file__).resolve().parent.parent / 'out' / 'du-lieu-moi.json'
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
           f'{trang.BIEU_TUONG}<title>Kiến thức · {escape(ten)}</title><style>{trang.CSS}{CSS}</style></head><body>',
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
