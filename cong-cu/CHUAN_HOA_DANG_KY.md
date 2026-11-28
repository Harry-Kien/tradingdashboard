# Chuẩn hóa phương pháp theo sách: luật và cổng ghi TRƯỚC khi đo

Ngày ghi: 24/11/2026, trước khi chạy `cong-cu/chuan_hoa.py` lần đầu. Chủ dự án chọn hướng "Chuẩn hóa theo sách" cùng ngày.
Mục đích: điểm vào của các phương pháp đúng định nghĩa chuẩn hơn. KHÔNG phải tìm bản có lãi nhất; không thử thêm biến thể nào ngoài các bản ghi dưới đây.

Cách đo, dùng chung cho mọi bản: vàng 2015–11/2026, nến M15 và M1 của webapp, đúng phép chấm của webapp (`phuong_phap.quet` + `phuong_phap.cham`:
mỗi lúc một lệnh, chốt 2R, giữ tối đa 24 giờ, spread và phí của cấu hình). Hai nửa: HỌC trước 1/5/2023, KIỂM từ 1/5/2023 (mốc webapp đang dùng cho các
phương pháp). Số báo: số lệnh, tỷ lệ thắng, R trung bình mỗi lệnh, tổng R, cho cả quãng và từng nửa.

## Thay đổi 1 — khoảng trống giá đúng định nghĩa (áp cho `ict`, `ict_fvg` và bản đồ ICT)

Hiện tại: khoảng trống tăng khi đáy nến thứ ba cao hơn đỉnh nến thứ nhất (rộng ít nhất 0,1 ATR); chiều giảm ngược lại. Không xét nến giữa.
Chuẩn (ICT, và thư viện smartmoneyconcepts): nến giữa phải là nến đẩy cùng chiều, tức đóng cao hơn mở với khoảng trống tăng, đóng thấp hơn mở với
khoảng trống giảm. Đối chiếu ngày 24/11/2026 cho thấy khoảng 1% tín hiệu ICT của webapp không thỏa điều này.

Bản mới: thêm đúng điều kiện đó (`FVG_NEN_GIUA = True`). Không đổi gì khác.

Cổng: KHÔNG có cổng lãi lỗ. Đây là sửa định nghĩa, nên được áp dụng dù kết quả đo tốt hơn hay xấu hơn; kết quả trước và sau được báo nguyên.
Điều kiện duy nhất để áp: sau khi sửa, phép đối chiếu `cong-cu/doi_chieu_fvg.py` phải cho 0 chỗ khác định nghĩa ở tín hiệu của hai phương pháp.

## Thay đổi 2 — lệnh ICT đòi đủ năm điều kiện hợp lưu (`ICT_HOP_LUU = True`)

Bảng điều kiện ICT trên trang Biểu đồ có năm dòng; lệnh hiện chỉ đòi một phần:
1. thuận xu hướng H1 (EMA20 so với EMA50 của nến H1 đã đóng);
2. lần phá cấu trúc M15 gần nhất (BOS hoặc CHoCH, tính tới nến tín hiệu) cùng chiều lệnh;
3. giá vào (giữa khoảng trống) nằm ở nửa có lợi của biên độ 24 giờ tính tới nến tín hiệu: mua ở nửa dưới (discount), bán ở nửa trên (premium);
4. có lần quét thanh khoản rồi đóng ngược lại;
5. có khoảng trống giá.

- `ict` (quét thanh khoản rồi khoảng trống giá) hiện đòi 4 và 5. Bản mới đòi thêm 1, 2, 3.
- `ict_fvg` (hồi về khoảng trống giá sau khi phá cấu trúc) hiện đòi 1 và 5. Bản mới đòi thêm 2, 3. (Điều kiện 4 không thuộc mô hình này.)
Cả hai bản mới đo trên nền đã có thay đổi 1.

Cổng, xét riêng cho từng phương pháp, so bản mới với bản chỉ có thay đổi 1:
- (a) mỗi nửa HỌC và KIỂM còn ít nhất 200 lệnh; và
- (b) R trung bình mỗi lệnh của bản mới cao hơn bản cũ ở CẢ hai nửa.
Qua cổng: bản mới thay bản cũ làm luật của phương pháp. Không qua: giữ bản cũ; năm điều kiện vẫn chỉ là bảng tham khảo như hiện nay.
Hai phương pháp là hai phép so, nên một bản qua cổng nhờ may rủi không phải là hiếm; qua cổng nghĩa là "đúng sách hơn và không kém đi trên dữ liệu cũ",
không phải bằng chứng có lãi.

## Thay đổi 3 — Wyckoff có xác nhận bằng khối lượng: KHÔNG làm được với dữ liệu hiện có

Kiểm ngày 24/11/2026: tệp nến nhiều năm chỉ có khối lượng thật cho 2015–2017 (từ 2018 bằng 0) và khối lượng tick chỉ có từ giữa 2025; kho nến của
webapp (từ 8/2026) không có cột khối lượng. Không đo được trên 11 năm và không chạy được lúc sống một cách nhất quán. Phần này để nguyên.

## Sau khi áp

Tăng `hoc.PHIEN_BAN` để bỏ kết quả đã lưu. Tín hiệu của `ict` và `ict_fvg` trong nhật ký điểm vào trước ngày áp là của luật cũ. Mô hình chấm điểm
(thử nghiệm) được huấn luyện trên tín hiệu cũ; nếu luật đổi thì ghi rõ điều đó, không âm thầm dùng tiếp.

---

# Điểm vào lệnh: biến thể và cổng ghi TRƯỚC khi đo

Ngày ghi: 24/11/2026, trước khi chạy `cong-cu/diem_vao.py` lần đầu. Chủ dự án giao: "làm sao xịn và tốt nhất là được", tức duyệt kế hoạch ở
`DIEM_VAO_HIEN_TRANG.md` với ba đề xuất mặc định (phạm vi tám phương pháp; spread thật của từng nến; chỉnh 2015–2021, kiểm tra 2022–11/2026).
Không thử thêm biến thể nào ngoài các bản dưới đây. Tổng số phép so được đếm và ghi vào báo cáo cuối.

## Phép mô phỏng (dùng chung)

- Nến 1 phút giá Bid. Mua khớp và bán thoát theo Ask = Bid + spread của CHÍNH nến đó (cột spread của tệp nến nhiều năm; phần sau ngày cuối của tệp
  dùng spread cấu hình 0,17). Dừng lỗ, chốt lời xét theo đúng bên giá.
- Vào ngay: khớp ở giá mở nến 1 phút đầu tiên sau khi nến tín hiệu đóng (trễ quá 5 phút thì bỏ).
- Lệnh chờ giới hạn: khớp khi Ask (mua) hoặc Bid (bán) chạm mức; lúc tín hiệu đến mà giá đã ở bên kia mức thì bỏ. Lệnh chờ dừng: khớp khi Ask (mua)
  hoặc Bid (bán) vượt mức; nến mở cửa đã vượt thì khớp ở giá mở (xấu hơn). Mọi lệnh chờ sống 4 giờ và bị hủy nếu giá chạm dừng lỗ trước khi khớp.
- Ở nến khớp của lệnh chờ chỉ xét phần đi ngược (dừng lỗ), không tính chốt lời. Dừng lỗ và chốt lời cùng trong một nến 1 phút: tính thua. Nến mở
  cửa đã ngoài dừng lỗ: thoát ở giá mở. Giữ tối đa 24 giờ, hết giờ thoát ở giá đóng.
- Chi phí: phí và trượt giá thường 0,18 mỗi lệnh (như hiện nay); cộng 0,25 cho mỗi lần khớp kiểu thị trường (vào ngay, lệnh chờ dừng, dừng lỗ, hết
  giờ) rơi trong 15 phút quanh một tin USD mức cao; phí qua đêm −0,0181% (mua) / +0,0066% (bán) giá trị lệnh cho mỗi đêm theo giờ Athens, đêm thứ Tư
  nhân ba (mức phí hiện tại của sàn, áp cho cả quá khứ: là giả định).
- Mỗi tín hiệu được chấm RIÊNG (không bỏ tín hiệu vì lệnh trước còn mở), để mọi biến thể được so trên đúng cùng một bộ tín hiệu và lệnh bị lỡ
  cũng có kết quả. Tín hiệu có khoảng dừng lỗ tính từ giá khớp thật nằm ngoài 0,5–3 ATR thì bỏ, như luật hiện tại.
- Đơn vị: R (bội số khoảng dừng lỗ ban đầu của chính lệnh đó), sau chi phí. Số báo: số tín hiệu, tỷ lệ khớp, số lệnh, tỷ lệ thắng, R mỗi lệnh,
  tổng R, hệ số lợi nhuận, sụt giảm lớn nhất (R, cộng dồn theo giờ thoát).

## Cổng chung

Với mỗi phương pháp và mỗi câu hỏi: trên phần CHỈNH chọn bản có R mỗi lệnh cao nhất (kể cả bản hiện tại). Nếu bản được chọn khác bản hiện tại thì
trên phần KIỂM TRA nó phải có ít nhất 100 lệnh VÀ R mỗi lệnh cao hơn bản hiện tại VÀ tổng R không thấp hơn bản hiện tại. Đạt: áp dụng. Không đạt:
giữ bản hiện tại. Dưới 100 lệnh ở phần kiểm tra: ghi "mẫu nhỏ, chưa đủ tin", không áp dụng. Các câu hỏi đi theo thứ tự C → D1 → D2 → E; câu sau dùng
bản đã qua cổng của câu trước.

## C. Kiểu vào

Năm phương pháp đang vào ngay (`pha_vo`, `elliott`, `wyckoff`, `price_action`, `ema_hoi`). Hiện tại V0: vào ngay khi nến tín hiệu đóng.
- V1 chờ hồi: lệnh chờ giới hạn ở giữa thân-và-râu nến tín hiệu (trung điểm đỉnh và đáy nến).
- V2 chờ phá: lệnh chờ dừng ở đỉnh (mua) hoặc đáy (bán) nến tín hiệu.
- V3 xác nhận khung nhỏ: trong 60 phút sau tín hiệu, nến M5 đầu tiên đóng cùng chiều lệnh (đóng trên mở với lệnh mua) thì vào ngay ở nến 1 phút kế tiếp.

Hai phương pháp ICT (`ict`, `ict_fvg`). Hiện tại V0: lệnh chờ giới hạn ở giữa khoảng trống giá.
- V1 mép gần: lệnh chờ giới hạn ở mép khoảng trống mà giá chạm trước. V2 mép xa: ở mép còn lại.
- V3 vào ngay khi nến tín hiệu đóng.
- V4 xác nhận khung nhỏ: sau khi giá chạm mép gần, nến M5 đầu tiên đóng cùng chiều lệnh thì vào ngay; hết 4 giờ thì thôi.

`fib`. Hiện tại V0: lệnh chờ giới hạn ở mức hồi 61,8%.
- V1 mức 50%. V2 mức 78,6%. V3 vào ngay khi nến tín hiệu đóng. V4 xác nhận khung nhỏ sau khi giá chạm mức 50%, như trên.

Dừng lỗ giữ nguyên mức của phương pháp; chốt 2R tính từ giá khớp thật. Với lệnh chờ, báo thêm tỷ lệ không khớp và kết quả mà các tín hiệu KHÔNG khớp
sẽ có nếu vào ngay (để thấy lệnh chờ bỏ lỡ lệnh loại nào).

## D1. Dừng lỗ (trên kiểu vào đã qua cổng ở C)

Hiện tại S0: mức của phương pháp (mục 1 của DIEM_VAO_HIEN_TRANG.md).
- S1 theo ATR: cách giá khớp 1,5 ATR M15. (Riêng `pha_vo` đang dùng đúng cách này, nên S1 của nó là theo cấu trúc: sau đỉnh/đáy nến tín hiệu lùi 0,1 ATR.)
- S2 thêm đệm spread: mức S0 lùi thêm đúng spread của nến lúc tín hiệu.
- S3 nới rộng: mức S0 lùi thêm 0,5 ATR.

## D2. Chốt lời (trên kiểu vào và dừng lỗ đã qua cổng)

Hiện tại T0: chốt hết ở 2R.
- T1 chốt hết ở 1R.
- T2 chốt hết ở mục tiêu lý thuyết của phương pháp (thanh khoản đối diện, biên vùng, đỉnh nhịp…); tín hiệu không có mục tiêu hợp lệ thì bỏ.
- T3 chốt một nửa ở 1R, từ nến kế tiếp dời dừng lỗ của nửa còn lại về giá vào, nửa còn lại chốt ở 2R.

## E. Bối cảnh (trên bản đã qua cổng). Mỗi bộ lọc xét riêng, là "bỏ tín hiệu khi…":

- L1 trong 60 phút trước hoặc sau một tin USD mức cao.
- L2 spread của nến lúc tín hiệu lớn hơn 2 lần trung vị spread của 1.440 nến 1 phút trước đó.
- L3 từ giá vào tới đỉnh 24 giờ (lệnh mua) hoặc đáy 24 giờ (lệnh bán) ngắn hơn 1 lần khoảng dừng lỗ: không đủ chỗ cho 1R trước kháng cự/hỗ trợ.
- L4 ngược xu hướng H4 (EMA20 so với EMA50 của nến H4 đã đóng).
Một bộ lọc được giữ khi qua cổng chung (so "có lọc" với "không lọc"). Phiên và biên độ đã đo trước đây nên không đo lại.

## F. Điểm chất lượng

Điểm = số điều kiện đạt trong bốn điều kiện L1–L4 (0–4, đạt nghĩa là KHÔNG bị bộ lọc đó bỏ). Trên phần kiểm tra, R mỗi lệnh phải tăng dần theo điểm
(4 > 3 > 2 > nhóm thấp hơn), mỗi nhóm ít nhất 100 lệnh, tính gộp tám phương pháp. Không đạt thì KHÔNG hiện điểm số, chỉ hiện từng điều kiện đạt/chưa đạt.

## B. Đi ngược, đi thuận

Không có cổng. Với mỗi lệnh của bản hiện tại (V0, S0, T0): độ đi ngược tối đa và đi thuận tối đa tính bằng R từ lúc khớp tới lúc thoát, tách lệnh thắng
và lệnh thua; thêm một lần chạy không đặt chốt lời (giữ tới dừng lỗ hoặc 24 giờ) để biết giá đi thuận được tới đâu.

---

# Điểm vào của luật bot tín hiệu: biến thể và cổng ghi TRƯỚC khi đo

Ngày ghi: 24/11/2026, trước khi chạy `cong-cu/diem_vao_bot.py` lần đầu. Chủ dự án đồng ý: "Có, đo đi". Chỉ ĐO và báo lại; mã của bot
(`D:\Tele dự báo\tinhieu`) không bị sửa. Không thử thêm biến thể nào ngoài các bản dưới đây.

Bộ tín hiệu: đúng các lệnh mà bộ kiểm của bot đã vào trên vàng 2015–11/2026 với cấu hình webapp đang dùng (khung M5 và M15, tối đa ba lệnh mở,
lệnh mới sau khi lệnh trước đạt TP1), lấy nguyên từ `tinhieu.backtest.simulate`. Mỗi lệnh được chấm RIÊNG bằng phép mô phỏng của
`cong-cu/diem_vao.py` (spread của từng nến, phí 0,18, trượt giá lúc tin, phí qua đêm; giữ tối đa 24 giờ như bot). Chia dữ liệu và cổng chung như
phần "Điểm vào lệnh" ở trên: chọn trên 2015–2021, xác nhận trên 2022–11/2026, ít nhất 100 lệnh ở phần kiểm tra, R mỗi lệnh cao hơn và tổng R không
thấp hơn bản đang giữ. Thứ tự C → D1 → D2 → E.

Khác với phép chấm của chính bot ở hai chỗ, áp cho MỌI bản kể cả bản hiện tại: các mức chốt lấy đúng bội số R (bot làm tròn thành số nguyên); và
khoảng dừng lỗ tính từ giá khớp thật được nhận trong 10–35 giá (bot: 17–28), để một kiểu vào dời giá vài giá không bị loại chỉ vì quy tắc 17–28.

## C. Kiểu vào
- V0 (hiện tại): vào ngay ở giá mở nến 1 phút đầu tiên sau khi nến tín hiệu đóng.
- V1 chờ hồi: lệnh chờ giới hạn ở giữa nến tín hiệu (trung điểm đỉnh và đáy), sống 4 giờ.
- V2 chờ phá: lệnh chờ dừng ở đỉnh (mua) hoặc đáy (bán) nến tín hiệu, sống 4 giờ.
- V3 xác nhận khung nhỏ: trong 60 phút, nến M5 đầu tiên đóng cùng chiều lệnh thì vào ngay.
Dừng lỗ giữ ở mức bot đã đặt; các mức chốt tính lại theo R từ giá khớp thật.

## D1. Dừng lỗ
- S0 (hiện tại): mức của bot (ngoài hỗ trợ/kháng cự 1 giá, hoặc khoảng cách dự phòng).
- S2: lùi thêm đúng spread của nến lúc tín hiệu.
- S3: lùi thêm 3 giá.

## D2. Chốt lời
- TL (hiện tại): sáu phần bằng nhau ở 0,5R · 1R · 1,5R · 2R · 2,5R · 3R; dừng lỗ giữ nguyên.
- T1: chốt hết ở 1R. T0: chốt hết ở 2R.
- TLB: thang sáu mức như hiện tại, nhưng sau khi phần đầu chốt thì dừng lỗ của phần còn lại dời về giá vào (từ nến kế tiếp).

## E. Bối cảnh (mỗi bộ lọc xét riêng)
- L1 bỏ khi trong 60 phút quanh tin USD mức cao. L2 bỏ khi spread lớn hơn 2 lần trung vị một ngày.
(Bộ lọc xu hướng H4 không xét: luật bot vốn đã đòi H1, H4 và D1 cùng chiều.)

## Đi ngược, đi thuận
Không có cổng: độ đi ngược tối đa của lệnh có lãi và đi thuận tối đa của lệnh lỗ (R), và tỷ lệ lệnh từng đạt 0,5R · 1R · 2R · 3R khi không đặt chốt lời.

---

# Tỷ lệ thắng theo năm và mức chốt lời: cách đo ghi TRƯỚC khi đo

Ngày ghi: 24/11/2026, trước khi chạy `cong-cu/ty_le_thang_nam.py` lần đầu. Chủ dự án hỏi có làm được hệ thống thắng 75–90% mọi năm không, rồi
đồng ý đo: "Có, đo đi". Đây là phép đo MÔ TẢ: không chọn biến thể, không có cổng, không đổi công thức nào của webapp hay của bot.

Câu hỏi: khi chỉ đổi mức chốt lời (giữ nguyên kiểu vào, dừng lỗ và bộ lọc), tỷ lệ lệnh thắng và lãi mỗi lệnh đổi ra sao, theo từng năm 2015–2026.

- Hai bộ lệnh:
  1. Tám phương pháp gộp lại, mỗi phương pháp theo đúng công thức phiếu đang dùng (`so_cong_khai/phieu.py`, CONG_THUC: kiểu vào, dừng lỗ, bộ lọc).
  2. Luật bot tín hiệu: đúng 2.452 lệnh bộ kiểm của bot đã vào, vào ngay, dừng lỗ của bot (như `cong-cu/diem_vao_bot.py`).
- Mức chốt lời (chốt hết một lần): 0,25R · 0,5R · 1R · 2R. Với luật bot thêm thang sáu mức hiện tại. Không thử mức nào khác.
- Phép mô phỏng chung của `cong-cu/diem_vao.py`: spread từng nến, phí 0,18, trượt giá lúc tin, phí qua đêm, giữ tối đa 24 giờ; dừng lỗ và chốt lời
  cùng một nến 1 phút thì tính dừng lỗ.
- Mỗi năm, mỗi mức: số lệnh, tỷ lệ lệnh thắng (R > 0 sau chi phí), R mỗi lệnh, tổng R. Thêm: số năm có tỷ lệ thắng từ 75% trở lên, số năm có tổng R
  dương, và tỷ lệ thắng hòa vốn của mức đó trước chi phí (1 / (1 + mức chốt)).
- Kiểm tra trước khi đọc số: với mức 2R, số của bộ 1 phải trùng số "bản cuối" đã ghi ở `out/diem-vao.json`, và số của bộ 2 với thang sáu mức phải
  trùng bản hiện tại (mục A, chi phí mới) ở `out/diem-vao-bot.json`. Không trùng thì dừng, tìm lỗi trước.

---

# Lọc lệnh luật bot bằng mô hình (meta-labeling): cách đo và cổng ghi TRƯỚC khi đo

Ngày ghi: 24/11/2026, trước khi chạy `cong-cu/loc_lenh_bot.py` lần đầu. Chủ dự án đồng ý: "Có, đo đi". Chỉ ĐO trong webapp; bot Telegram và EA không
bị sửa. Phương pháp theo López de Prado (2018), *Advances in Financial Machine Learning*: meta-labeling (mô hình phụ học xem lệnh nào của một luật có
sẵn nên bỏ, chứ không đoán chiều giá) và kiểm định chéo có tách khoảng (purged k-fold với embargo) để không rò thông tin tương lai.

- **Lệnh:** đúng các lệnh của luật bot như ở `cong-cu/diem_vao_bot.py` (vào ngay, dừng lỗ của bot, thang sáu mức 0,5R–3R; phép mô phỏng chung của
  `cong-cu/diem_vao.py`). Nhãn: 1 nếu lệnh có lãi sau chi phí (R > 0), 0 nếu không.
- **Đặc trưng** (chỉ dùng nến M15 đã đóng trước lúc vào và thông tin có lúc vào): các cột của `mo_hinh.bang_nen` (khoảng cách tới EMA50, RSI, vị trí
  trong biên 24 giờ, đà 4 giờ, thân và biên nến, đều tính theo ATR và đổi dấu theo chiều lệnh); ATR so với trung bình 5 ngày; dừng lỗ tính theo ATR;
  giờ trong ngày (sin, cos); thứ trong tuần; khung M5 hay M15; chiều lệnh; spread lúc vào so với trung vị một ngày; có trong 60 phút quanh tin USD.
- **Chia dữ liệu:** học 2015–2021; kiểm 2022–11/2026 (mô hình không thấy phần này). Mọi lựa chọn làm trên phần học.
- **Bốn biến thể, không thêm:** hai mô hình × hai mức giữ.
  - Mô hình: hồi quy logistic (chuẩn hóa, C = 1); cây tăng cường (HistGradientBoosting: max_depth 3, learning_rate 0,05, max_iter 200,
    min_samples_leaf 50, l2 1,0, không dừng sớm, random_state 0). Tham số cố định, không dò.
  - Mức giữ: 50% hoặc 30% lệnh có xác suất thắng dự báo cao nhất. Ngưỡng xác suất lấy từ dự báo ngoài mẫu trên phần học, rồi giữ nguyên con số đó
    khi áp cho phần kiểm.
- **Chọn trên phần học:** kiểm định chéo 5 khối liên tiếp theo thời gian; khi một khối làm phần kiểm thì bỏ khỏi phần học mọi lệnh có thời gian mở
  chạm khoảng của khối đó, nới thêm 1 ngày mỗi bên (embargo). Chọn biến thể có R mỗi lệnh ngoài mẫu cao nhất trong số các biến thể giữ ít nhất 100 lệnh.
- **Cổng trên phần kiểm** (biến thể đã chọn, mô hình học lại trên toàn bộ 2015–2021): giữ ít nhất 100 lệnh; R mỗi lệnh VÀ tỷ lệ thắng đều cao hơn
  khi không lọc; và hơn hẳn lọc ngẫu nhiên: trong 2.000 lần chọn ngẫu nhiên cùng số lệnh từ phần kiểm, tỷ lệ lần có R mỗi lệnh từ mức của mô hình trở
  lên phải dưới 5%. Không qua cổng thì kết luận "mô hình không lọc được", và không đưa vào webapp.
- **Báo thêm, không dùng để chọn:** số đo cả bốn biến thể trên phần kiểm, theo từng năm, tổng R và sụt giảm.

---

# Đo lại trên dữ liệu mới: cách đo và cách kết luận ghi TRƯỚC

Ngày ghi: 24/11/2026, trước khi có dữ liệu mới. Chủ dự án đồng ý: "có, làm tiếp". Công cụ: `cong-cu/do_lai_du_lieu_moi.py` (chạy tay, hoặc
`DO_LAI_DU_LIEU_MOI.bat`); nên chạy khoảng mỗi tháng. Mục đích: xem các luật và công thức đã chọn tới ngày 24/11/2026 có giữ được kết quả trên
giá mà không phép đo nào đã nhìn thấy hay không.

- **Dữ liệu mới:** mọi tín hiệu từ 00:00 UTC ngày 25/11/2026 trở đi. Phần trước mốc này chỉ dùng để tính chỉ báo, không được tính vào kết quả.
- **Những gì được đo lại, giữ NGUYÊN như đã chốt ngày 24/11/2026 (không chỉnh gì):**
  1. Tám công thức phiếu (`so_cong_khai/phieu.py`, CONG_THUC).
  2. Luật bot tín hiệu bản hiện tại (vào ngay, dừng lỗ của bot, thang sáu mức), và bản đã qua cổng "chờ phá đỉnh/đáy nến tín hiệu".
  3. Bốn biến thể lọc lệnh bằng mô hình của `cong-cu/loc_lenh_bot.py`, mô hình học trên 2015–2021 với đúng tham số đã ghi, ngưỡng giữ nguyên. Kể cả
     hai biến thể cây tăng cường không được nhận: đây là chỗ kiểm xem số đẹp của chúng ở 2022–2026 có thật không.
  4. Nhật ký điểm vào (kết quả ghi lúc chạy thật): chỉ tóm tắt, không kết luận.
- **Cách kết luận cho mỗi mục** (R mỗi lệnh sau chi phí, phép mô phỏng chung của `cong-cu/diem_vao.py`):
  - Dưới 30 lệnh mới: "chưa đủ lệnh", không kết luận gì.
  - Từ 30 lệnh: khoảng tin cậy 90% của R mỗi lệnh bằng bootstrap (2.000 lần, hạt giống 0). Cận dưới trên 0: "vẫn có lãi". Cận trên dưới 0:
    "đang lỗ rõ". Còn lại: "chưa phân định".
  - Ghi thêm "kém kỳ vọng rõ" nếu cận trên thấp hơn R mỗi lệnh đã đo ở phần kiểm 2022–2026.
- **Không chỉnh theo dữ liệu mới.** Kết quả ở đây chỉ để xác nhận hoặc bác bỏ. Muốn đổi luật vì nó thì phải ghi một mục đăng ký mới trước.
- **Tự kiểm công cụ:** chạy với `--doi-chieu` thì lấy mốc 01/01/2022 và phải ra đúng số của phần kiểm đã ghi ở `out/diem-vao.json`,
  `out/diem-vao-bot.json` và `out/loc-lenh-bot.json`; lệch thì dừng.

---

# Đo lại các phép đo của luật bot sau khi mã bot đổi (24/11/2026, 23:42)

Mã bot (`D:\Tele dự báo\tinhieu`: rules.py, service.py, stats.py, chat.py, fmt.py) được sửa lúc 23:42–23:43 ngày 24/11/2026, ngoài phiên đo này;
`do_lai_du_lieu_moi.py --doi-chieu` phát hiện số lệnh 2022–2026 đổi từ 1.239 thành 1.332. Chủ dự án xác nhận và đồng ý đo lại: "Tôi biết, đo lại bot".
Chạy lại NGUYÊN các công cụ và luật đã đăng ký ở trên (`diem_vao_bot.py`, `ty_le_thang_nam.py`, `loc_lenh_bot.py`), không thêm biến thể, không đổi
cổng. Kết quả cũ (bot trước 23:42) giữ ở `out/luu/bot-truoc-2342-24-11-2026/`. Vì bot vừa được chỉnh khi đã nhìn dữ liệu tới nay, số của phần
2022–2026 càng không phải phép kiểm ngoài mẫu thật; chỉ dữ liệu từ 25/11/2026 mới là phép kiểm đó.

---

# Điểm vào của luật ba khung và luật đỉnh/đáy: biến thể và cổng ghi TRƯỚC khi đo

Ngày ghi: 25/11/2026 (0 giờ 30), trước khi chạy `cong-cu/diem_vao_luat_so.py` lần đầu. Chủ dự án yêu cầu làm tiếp các phần chưa xong ("làm đến khi
xịn, tốt, toàn diện"); đây là phần "chưa đo theo cách này" đã ghi ở DIEM_VAO_BAO_CAO.md. Chỉ ĐO: mã của EA Promax (ai.rule_trend, ai.rule_fade,
tools.ai_trend_*) không bị sửa. Không thử biến thể nào ngoài các bản dưới đây.

- **Bộ tín hiệu:** đúng các lệnh mà bộ kiểm của từng luật đã vào trên vàng 2015–11/2026, lấy từ `so_cong_khai.kiem_chung._ba_khung` và
  `_dinh_day` (cấu hình webapp đang dùng, có né tin). Nến tín hiệu là nến M15 đóng ngay trước lúc vào.
- **Phép mô phỏng chung** của `cong-cu/diem_vao.py` (spread từng nến, phí 0,18, trượt giá lúc tin, phí qua đêm, giữ tối đa 24 giờ; dừng lỗ và chốt lời
  cùng một nến 1 phút thì tính dừng lỗ). Khác với bộ chấm riêng của hai luật ở ba chỗ, áp cho MỌI bản kể cả bản hiện tại: luật ba khung giữ tới khi chạm
  dừng lỗ hay chốt lời (ở đây tối đa 24 giờ); luật đỉnh/đáy có dời hòa vốn và đóng chiều Thứ Sáu (ở đây không); chi phí tính theo phép mô phỏng chung.
- **Luật ba khung** (hiện tại: vào ngay, dừng lỗ cách giá vào 20, chốt cách 5, tức 0,25R):
  - C. Kiểu vào: V0 vào ngay (hiện tại) · V1 chờ hồi về giữa nến tín hiệu · V2 chờ phá đỉnh/đáy nến tín hiệu · V3 xác nhận nến M5. Dừng lỗ luôn
    cách giá khớp 20.
  - D. Chốt lời (chốt hết): 0,25R = 5 giá (hiện tại) · 0,5R = 10 · 1R = 20 · 2R = 40.
- **Luật đỉnh/đáy** (hiện tại: vào ngay, dừng lỗ ngoài đỉnh/đáy vừa quét, chốt ở 1,5R):
  - C. Kiểu vào: V0 · V1 · V2 · V3 như trên. Dừng lỗ giữ ở mức luật đã đặt; khoảng rủi ro tính lại từ giá khớp.
  - D. Chốt lời: 1,5R (hiện tại) · 0,5R · 1R · 2R.
- **Chia dữ liệu và cổng** như phần "Điểm vào lệnh" ở trên: chọn trên 2015–2021, xác nhận trên 2022–11/2026, ít nhất 100 lệnh ở phần kiểm tra; một
  biến thể chỉ được nhận khi R mỗi lệnh ở phần kiểm tra cao hơn và tổng R không thấp hơn bản đang giữ. Thứ tự C → D.

---

# Lọc lệnh luật bot bằng mô hình, bản 2: thêm thông tin liên thị trường (ghi TRƯỚC khi đo)

Ngày ghi: 25/11/2026, trước khi chạy `cong-cu/loc_lenh_bot_v2.py` lần đầu. Chủ dự án yêu cầu "tiếp tục training". Bản 1 (chỉ dùng giá vàng) không qua
cổng; huấn luyện thêm trên cùng dữ liệu giá chỉ làm mô hình học thuộc quá khứ, nên bản 2 chỉ thêm thông tin MỚI mà bản 1 không có. Chỉ ĐO; bot không bị sửa.

- **Giữ nguyên mọi thứ của bản 1:** cùng lệnh của luật bot (bản bot hiện tại), cùng nhãn, cùng 15 đặc trưng giá vàng, cùng hai mô hình và tham số, cùng
  hai mức giữ, cùng kiểm định chéo có tách khoảng, cùng chia học 2015–2021 / kiểm 2022–2026, cùng cổng (≥ 100 lệnh, R mỗi lệnh và tỷ lệ thắng cao hơn
  không lọc, hơn lọc ngẫu nhiên với p < 0,05).
- **Thêm 7 đặc trưng**, chỉ dùng nến/bản tin đã có TRƯỚC lúc vào lệnh (dữ liệu thô MT5 ở `D:\EA Promax\data\raw`, cùng mốc giờ với nến vàng, đã kiểm
  lệch 0 giờ), đổi dấu theo chiều lệnh khi có chiều:
  1. Đà 4 giờ của bạc (XAGUSD H1). 2. Vàng và bạc cùng chiều đà 4 giờ (1/0). 3. Tỷ lệ vàng/bạc so với trung bình 60 ngày (điểm z).
  4. Đà 24 giờ của dầu Brent (H1). 5. Đà 5 ngày của S&P 500 (D1).
  6. Vị thế ròng của quỹ đầu cơ (managed money) trên hợp đồng vàng tương lai, tính theo phần trăm tổng hợp đồng mở (báo cáo COT, `du-lieu/cot-vang.json`).
  7. Thay đổi một tuần của số đó. COT chỉ dùng từ 00:00 thứ Bảy sau ngày chốt số liệu (bản tin ra chiều thứ Sáu).
  Thiếu dữ liệu (ví dụ trước khi có COT) thì đặt 0, không bỏ lệnh, để bộ lệnh trùng hẳn bản 1.
- **Báo thêm, không dùng để chọn:** AUC của bản 2 so với bản 1 trên cùng lệnh.

---

# Xác suất khớp quá mức (PBO) và rủi ro theo Monte Carlo: cách đo ghi TRƯỚC

Ngày ghi: 25/11/2026, trước khi chạy `cong-cu/kiem_pbo.py` và `cong-cu/rui_ro_monte_carlo.py` lần đầu. Chủ dự án yêu cầu kiểm hệ thống đã chuẩn chưa
và tham khảo các hệ thống cùng loại. Hai phép này là chuẩn của giới nghiên cứu định lượng mà hệ thống chưa có. Chỉ ĐO; không chọn, không đổi luật nào.

**1. PBO (Bailey, Borwein, López de Prado, Zhu 2015; kiểm định chéo đối xứng tổ hợp, CSCV).**
- Dữ liệu: bảng lãi lỗ theo tuần của `cong-cu/kiem_dinh_spa.py` (`out/spa-bang-tuan.csv`, chạy lại với bot hiện tại). Hai tập như SPA: 33 chiến lược
  (tập 1) và toàn bộ bảng.
- Chia các tuần thành 16 khối liên tiếp. Với mỗi cách chọn 8 khối làm phần trong mẫu (12.870 cách, duyệt hết): chọn chiến lược có tỷ số lãi trung
  bình / độ lệch chuẩn cao nhất trong mẫu, rồi xem thứ hạng của nó ở 8 khối còn lại. PBO = tỷ lệ số cách mà chiến lược tốt nhất trong mẫu rơi xuống
  nửa dưới ngoài mẫu. Báo thêm: tỷ lệ số cách mà chiến lược được chọn lỗ ngoài mẫu.
- Cách đọc ghi trước: PBO dưới 0,2 là ít dấu hiệu khớp quá mức; 0,2–0,5 là đáng ngờ; từ 0,5 trở lên là chọn theo quá khứ không hơn chọn bừa.

**2. Rủi ro theo Monte Carlo.**
- Chuỗi R mỗi lệnh (sau chi phí, phép mô phỏng chung của `cong-cu/diem_vao.py`) của: luật bot bản hiện tại; luật ba khung bản hiện tại (chốt 0,25R);
  luật ba khung chốt 2R (bản qua cổng). Mỗi luật tính riêng hai giai đoạn 2015–2021 và 2022–2026.
- Giả lập 10.000 năm giao dịch: số lệnh mỗi năm bằng trung bình của giai đoạn đó; lấy mẫu lại theo khối (stationary bootstrap, khối trung bình 10
  lệnh) để giữ các chuỗi thắng thua liền nhau; hạt giống 0.
- Báo: tổng R một năm (trung vị, phân vị 5%), sụt giảm lớn nhất (trung vị, phân vị 95%), chuỗi thua dài nhất (phân vị 95%), và xác suất vốn có lúc
  giảm từ 50% trở xuống khi mỗi lệnh rủi ro 0,5% · 1% · 2% · 5% · 10% · 25% vốn hiện có (lãi kép). Đây là phép tính cho các mức cho trước, không
  phải khuyến nghị mức rủi ro.

---

# Phản ứng của giá vàng khi tin Mỹ ra: cách đo và cổng ghi TRƯỚC

Ngày ghi: 25/11/2026, sau khi sửa lệch giờ của nến nhiều năm (`so_cong_khai/sua_gio.py`) và trước khi chạy `cong-cu/phan_ung_tin.py` lần đầu. Chủ dự
án yêu cầu dự đoán MUA/BÁN khi tin ra, "tỷ lệ chính xác cao nhất lên tới 90%", rồi chọn "Sửa rồi đo". Chỉ ĐO; không đổi luật nào.

- **Tin:** mọi tin USD mức cao (importance 3) trong lịch MT5 của EA (giờ UTC, đã kiểm khớp nến sau khi sửa) từ 2015 tới 11/2026. Các tin ra cùng một
  phút gộp thành một lần ra tin, đặt tên theo tin quan trọng nhất trong danh sách ưu tiên (NFP, CPI, quyết định lãi suất Fed, PCE, bán lẻ, PPI, GDP,
  ISM, đơn xin trợ cấp thất nghiệp…). Chỉ tính các loại có từ 40 lần ra tin trở lên.
- **Mô tả (không có cổng):** với mỗi loại tin, giá đóng của nến 1 phút ngay trước giờ tin là mốc; đo độ dịch chuyển sau 1, 15, 60 phút (trung vị và
  phân vị 90 của trị tuyệt đối, theo giá), tỷ lệ lần đi xa hơn 10 giá trong 15 phút, và spread lớn nhất trong 5 phút đầu so với trung vị một ngày trước
  (khi tệp có cột spread).
- **Đoán chiều trước khi tin ra, bốn quy tắc, không thêm:** (a) đi tiếp chiều của 60 phút trước tin; (b) đi ngược chiều đó; (c) theo chiều EMA20 so
  với EMA50 của H1 lúc trước tin; (d) đi tiếp chiều của phút đầu tiên sau tin (không phải đoán trước, nhưng là thứ người xem có thể làm sớm nhất), tính
  từ giá đóng của phút đầu tới 60 phút sau tin.
  - Chỉ số: tỷ lệ đoán đúng chiều của dịch chuyển (15 phút với a, b, c; từ phút 1 tới phút 60 với d), gộp mọi loại tin.
  - Chọn quy tắc tốt nhất trên 2015–2021; nhận khi trên 2022–11/2026 có từ 100 lần ra tin, tỷ lệ đúng từ 55% trở lên và kiểm định nhị thức một
    phía so với 50% cho p < 0,05. Không qua thì kết luận "chiều giá sau tin không đoán được bằng các quy tắc này".
- **Không làm ở đây:** đoán theo độ bất ngờ (số thực tế so với dự báo), vì lịch trên máy không có hai con số này. Phần đó cần tệp lịch có số thực tế và
  dự báo (script MQL5 `cong-cu/mql5/XuatLichKinhTe.mq5`, chủ dự án tự chạy trong MT5), và sẽ ghi cách đo riêng trước khi đo.

---

# Theo dõi bản 2 của mô hình lọc lệnh trên dữ liệu mới (ghi TRƯỚC)

Ngày ghi: 25/11/2026, sau lần chạy thứ ba của `cong-cu/loc_lenh_bot_v2.py` (lần đầu trên nến đã sửa lệch giờ). Lần này biến thể được chọn trên phần học
(cây tăng cường, giữ 30%) qua cổng ở phần kiểm (+0,242R so với +0,177R không lọc; p = 0,04 so với lọc ngẫu nhiên). KHÔNG đưa vào webapp vì: đây là lần
nhìn thứ ba của cùng một phép kiểm (điều chỉnh cho ba lần nhìn thì không còn ý nghĩa ở mức 5%); trên phần học nó không hơn không lọc (−0,002R cả hai);
ở 2022 và 2023 nó làm kém hơn, phần hơn chỉ ở 2025–2026; sụt giảm lớn hơn (31,5R so với 20,8R); AUC quanh 0,5.

Việc làm: `cong-cu/do_lai_du_lieu_moi.py` đo thêm bốn biến thể của bản 2 (học trên 2015–2021, tham số và ngưỡng như đã đăng ký) trên dữ liệu từ
25/11/2026, cùng luật kết luận đã ghi ở phần "Đo lại trên dữ liệu mới". Chỉ khi biến thể cây giữ 30% của bản 2 "vẫn có lãi" và hơn rõ luật bot không lọc
trên dữ liệu mới thì mới xét đưa vào webapp, bằng một mục đăng ký mới.

---

# Lọc theo xu hướng nhiều khung cho tám phương pháp (ghi TRƯỚC khi đo)

Ngày ghi: 25/11/2026 (khoảng 23 giờ 15), trước khi chạy `cong-cu/loc_xu_huong.py` lần đầu. Chủ dự án yêu cầu "nâng cấp các phương thức lên xịn hơn
để hoạt động chuẩn chỉnh, đạt hiệu quả cao nhất". Lý do chọn câu hỏi này: luật bot là luật duy nhất có lãi ở mọi mức chốt từ 0,5R (DIEM_VAO_BAO_CAO.md),
và điều kiện cốt lõi của nó là xu hướng D1, H4, H1 cùng chiều; tám phương pháp mới chỉ được thử lọc theo H4 (L4). Câu hỏi: điểm vào của tám phương
pháp có giá trị khi thuận xu hướng lớn không. Chỉ ĐO; luật gốc không đổi. Không thử biến thể nào ngoài hai bộ lọc dưới đây.

- **Bản nền:** công thức trên phiếu của từng phương pháp (`so_cong_khai/phieu.py`, CONG_THUC: kiểu vào, dừng lỗ, chốt lời và các bộ lọc đã qua cổng),
  chấm bằng phép mô phỏng chung của `cong-cu/diem_vao.py`, mỗi tín hiệu chấm riêng.
- **Hai bộ lọc, xét riêng, mỗi cái thêm vào bản nền** ("bỏ tín hiệu khi…"). Xu hướng của một khung = dấu của EMA20 trừ EMA50 trên giá đóng của các nến
  khung đó ĐÃ ĐÓNG trước lúc tín hiệu:
  - L5: ngược xu hướng D1.
  - L6: D1, H4 và H1 không cùng chiều lệnh (chỉ giữ khi cả ba khung thuận chiều lệnh).
- **Chia dữ liệu và cổng chung** như phần "Điểm vào lệnh": chọn trên 2015–2021 bản có R mỗi lệnh cao nhất trong {bản nền, L5, L6} (ít nhất 100 lệnh);
  khác bản nền thì trên 2022–11/2026 phải có ít nhất 100 lệnh, R mỗi lệnh cao hơn và tổng R không thấp hơn bản nền. Đạt thì phiếu dùng thêm bộ lọc đó.
- **Điều kiện để được gọi là "có lãi ổn định"** (không dùng để chọn, chỉ để gọi tên): R mỗi lệnh dương ở CẢ hai phần dữ liệu VÀ ít nhất 7 trong 12 năm
  có tổng R dương (năm có ít nhất 10 lệnh). Qua cổng mà không đạt điều kiện này thì trang vẫn ghi phương pháp chưa có lợi thế.
- **Báo thêm:** số năm có tổng R dương, R mỗi lệnh từng năm. 16 phép so (8 phương pháp × 2 bộ lọc), cộng vào 107 phép so trước đó; cách đọc phải tính
  tới số phép so đã làm.

---

# Gợi ý giữ lệnh "sau TP1 dời dừng lỗ về giá vào" cho tín hiệu luật bot (ghi TRƯỚC khi áp)

Ngày ghi: 25/11/2026 (khoảng 23 giờ 40). Chủ dự án muốn tỷ lệ thắng cao hơn và chọn: "Có, thêm vào". KHÔNG có phép đo mới, không biến thể mới: số lấy
nguyên từ bản TLB của mục D2 trong "Điểm vào của luật bot tín hiệu" (`out/diem-vao-bot.json`), so với bản TL đang dùng, ở phần kiểm 2022–11/2026:
thắng 67,2% so với 52,7%, sụt giảm lớn nhất 17,7R so với 22,6R, lời mỗi lệnh +0,143R so với +0,181R (1.850 lệnh). TLB KHÔNG qua cổng (lời mỗi lệnh
thấp hơn), nên:
- Không đổi luật bot, EA, nhật ký điểm vào hay cách chấm thắng thua; tín hiệu vẫn ghi đúng mức của bot.
- Chỉ hiện một GỢI Ý kèm đủ hai mặt (thắng nhiều hơn, sụt ít hơn; lời mỗi lệnh ít hơn) cạnh phương án luật bot ở nút Phân tích và trên tín hiệu luật bot
  ở kênh Telegram; khi lệnh chạm TP1, tin kết quả nhắc dời dừng lỗ phần còn lại về giá vào. Có ô tắt trên trang /telegram.
- Số luôn đọc từ tệp đo (`so_cong_khai/giu_lenh.py`); đo lại thì số trên gợi ý đổi theo, không chép tay.

---

# Theo dõi bộ lọc L6 trên dữ liệu mới (ghi TRƯỚC)

Ngày ghi: 26/11/2026 (khoảng 12 giờ), trước khi đo phần này lần nào. Bộ lọc L6 (D1, H4, H1 cùng chiều lệnh) qua cổng đêm 25/11/2026 ở Phá vỡ, ICT quét
thanh khoản, Wyckoff và Hồi về EMA, và phiếu của bốn phương pháp đó đã dùng nó. Phép đo đó đã nhìn giá tới chiều 25/11/2026.

- `cong-cu/do_lai_du_lieu_moi.py` giữ nguyên mục "Công thức phiếu" là tám công thức chốt ngày 24/11/2026 (không có L6), đúng như phần "Đo lại trên
  dữ liệu mới" ở trên.
- Thêm nhóm "Công thức phiếu có L6": bốn phương pháp trên, công thức trên phiếu kèm L6, chỉ tính tín hiệu từ 00:00 UTC ngày 26/11/2026. Kỳ vọng là R mỗi
  lệnh của bản L6 ở phần kiểm 2022–2026 (`out/loc-xu-huong.json`). Cách kết luận y như phần "Đo lại trên dữ liệu mới" (dưới 30 lệnh chưa kết luận;
  khoảng tin cậy 90%; "kém kỳ vọng rõ"). Với `--doi-chieu`, mốc 01/01/2022 phải ra đúng số phần kiểm của bản L6.
- Webapp tự chạy công cụ này mỗi tháng một lần (lần đầu trong tháng mới), đúng nhịp đã ghi; không đo dày hơn để tránh nhìn nhiều lần vào cùng một phép
  kiểm. Người dùng vẫn bấm đo lại được. Không chỉnh luật theo số này.


# Chỉ báo "Khối lượng đột biến" (tick volume của MT5): cách đo ghi TRƯỚC

Ngày ghi: 26/11/2026 (khoảng 20 giờ), trước khi viết chỉ báo và trước khi nhìn bất kỳ số khối lượng nào. Người dùng muốn biết "khi nào cá mập vào để
đánh theo xu hướng".

Giới hạn ghi rõ: vàng CFD trên MT5 không có khối lượng giao dịch thật (real_volume của sàn bằng 0). Chỉ có tick volume: số lần giá đổi trong nến. Nó đo độ
sôi động, không đo ai vào lệnh hay lệnh to cỡ nào. Chỉ báo và mọi chữ trên trang phải nói đúng như vậy, không gọi là "lệnh cá mập".

Định nghĩa (cố định, không thử biến thể khác):
- rel = tick volume của nến ÷ trung bình tick volume của 20 nến ĐÃ ĐÓNG ngay trước (không tính chính nến đó).
- Nến đột biến: rel ≥ 2, thân nến ≥ 50% biên độ (cao − thấp). Chiều = chiều thân nến (đóng > mở là mua).
- "Thuận xu hướng": mua khi giá đóng trên EMA50 của giá đóng, bán khi dưới.

Cách đo (`cong-cu/do_khoi_luong.py`): đọc nến vàng M5, M15, H1 kèm tick volume qua webapp đang chạy (`/api/gia`, chỉ đọc). Với mỗi nến đột biến thuận xu
hướng, xét 4 nến tiếp theo: "đi tiếp" nếu giá đóng nến thứ 4 sau nó vượt giá đóng nến đột biến theo đúng chiều; kèm biến động có dấu tính bằng ATR14.
Mốc so sánh: mọi nến thuận xu hướng có thân ≥ 50% nhưng rel < 2, cùng cách tính. Báo số lần, tỷ lệ đi tiếp, biến động trung bình (ATR) cho từng khung, và
khoảng tin cậy 90% của chênh lệch tỷ lệ.

Kết luận: dưới 30 nến đột biến ở một khung thì "chưa đủ dữ liệu". Khoảng tin cậy 90% của chênh lệch nằm trọn trên 0 thì "có lợi thế trên mẫu này"; còn lại
"chưa thấy lợi thế". MT5 chỉ trả vài trăm tới khoảng nghìn nến mỗi khung (vài ngày tới vài tháng), nên kết quả nào cũng chỉ là sơ bộ. Không chỉnh ngưỡng 2
hay 50% theo số đo.

Kết quả lần đo đầu (26/11/2026, khoảng 20 giờ, `out/khoi-luong-dot-bien.json`): M5 (23–26/11) 3 nến đột biến; M15 (12–26/11) 14 nến, đi tiếp 57%
so với mốc 51%, khoảng tin cậy 90% của chênh lệch [−16%, +28%]; H1 (28/9–26/11) 23 nến, đi tiếp 57% so với 47%, [−9%, +27%]. Cả ba khung: chưa đủ dữ liệu
(dưới 30 nến). Chưa có bằng chứng chỉ báo này giúp đánh theo xu hướng. Đo lại khi đã gom thêm nến; không đổi ngưỡng.

Bổ sung (ghi TRƯỚC khi đo, 26/11/2026, khoảng 21 giờ): mẫu mở rộng cho cùng phép đo khối lượng đột biến. Lần đo đầu chỉ có 900–1.000 nến mỗi khung nên
không kết luận được. Lần này `cong-cu/do_khoi_luong.py --mau-lon` lấy tick volume tới 60.000 nến MT5 còn giữ (`/api/khoi-luong`) và ghép với nến của
`/api/gia-cu` (kho nến 1 phút, từ 1/1/2026), theo đúng giờ mở nến; nến không có tick volume thì bỏ. Định nghĩa, ngưỡng (2 lần, thân 50%, EMA50, 4 nến
sau), mốc so sánh và cách kết luận giữ nguyên, không thử biến thể khác. Vì đã nhìn kết quả 900 nến cuối, báo thêm riêng phần mẫu KHÔNG trùng với lần đo
đầu (các nến trước nến đầu tiên của lần đo đầu); kết luận chính lấy theo phần không trùng này. Báo số nến ghép được và số nến bị bỏ.

Kết quả mẫu lớn (26/11/2026, khoảng 21 giờ, `out/khoi-luong-dot-bien-mau-lon.json`; nến vàng 2026, ghép đủ, không nến nào bị bỏ). Phần KHÔNG trùng lần đo
đầu (kết luận chính): M5 268 nến đột biến, đi tiếp 49,6% so với mốc 48,3%, khoảng tin cậy 90% của chênh lệch [−3,8%, +6,4%]; M15 197 nến, 45,2% so với
48,9%, [−9,6%, +2,2%], biến động trung bình 4 nến sau −0,09 ATR; H1 36 nến, 38,9% so với 49,3%, [−24%, +3,2%], −0,29 ATR. Cả ba khung: CHƯA THẤY LỢI THẾ.
Nến tick volume đột biến thuận EMA50 không đi tiếp tốt hơn nến thường trên vàng 2026; ở M15 và H1 còn hơi nghiêng về đảo chiều (chưa đủ chắc). Chỉ báo
giữ lại để xem độ sôi động, không dùng làm tín hiệu; mô tả trên trang ghi rõ kết quả này. Không đổi ngưỡng.


# Hợp lưu giữa các phương pháp (ghi TRƯỚC khi đo)

Ngày ghi: 26/11/2026 (khoảng 23 giờ), trước khi chạy `cong-cu/hop_luu.py` lần đầu và trước khi nhìn bất kỳ số hợp lưu nào. Chủ dự án yêu cầu "các phương
thức xịn nhất để nâng tỷ lệ thắng". Đã biết từ phần D2 (`out/diem-vao.json`): chốt hết ở 1R, hoặc nửa ở 1R rồi dời về hòa vốn, nâng tỷ lệ thắng khoảng
14 điểm phần trăm ở cả tám phương pháp nhưng làm R mỗi lệnh thấp hơn ở 7/8, nên không áp. Câu hỏi chưa đo: một tín hiệu có tốt hơn khi phương pháp KHÁC
cũng báo cùng chiều trong cùng khoảng thời gian không. Chỉ ĐO; luật gốc không đổi. Không thử biến thể nào ngoài hai bộ lọc dưới đây.

- **Bản nền:** công thức đang dùng trên phiếu (`phieu.CONG_THUC`, gồm các bộ lọc đã qua cổng, kể cả L6), chấm bằng phép mô phỏng chung của
  `cong-cu/diem_vao.py`, mỗi tín hiệu chấm riêng.
- **Tín hiệu của phương pháp khác:** tín hiệu thô của bảy phương pháp còn lại (`diem_vao.tin_hieu`, trước mọi bộ lọc), cùng chiều lệnh, có giờ tín hiệu
  trong 60 phút tính tới giờ tín hiệu đang xét (gồm cả cùng nến M15). Chỉ dùng tín hiệu đã có tới lúc đó, không nhìn trước.
- **Hai bộ lọc, xét riêng, mỗi cái thêm vào bản nền** ("bỏ tín hiệu khi…"):
  - H1: không có phương pháp khác nào cùng chiều trong 60 phút đó.
  - H2: có ít hơn hai phương pháp khác cùng chiều trong 60 phút đó.
- **Chia dữ liệu, cổng và điều kiện "có lãi ổn định":** y như phần "Lọc theo xu hướng nhiều khung" (chọn trên 2015–2021; khác bản nền thì trên
  2022–11/2026 phải có ít nhất 100 lệnh, R mỗi lệnh cao hơn và tổng R không thấp hơn bản nền). Tỷ lệ thắng KHÔNG dùng để chọn; chỉ báo kèm.
- **Báo thêm:** tỷ lệ thắng, số lệnh còn lại, số năm có lãi. 16 phép so (8 phương pháp × 2 bộ lọc), cộng vào 123 phép so trước đó.
- Qua cổng thì phiếu và nhóm Telegram dùng thêm bộ lọc đó; không qua thì ghi kết quả, không áp.

Kết quả (26/11/2026, khoảng 23 giờ 20, `out/hop-luu.json`): chỉ Sóng Elliott qua cổng với H2 (chọn H2 trên phần chỉnh; phần kiểm 249 lệnh, thắng 38,2%,
R mỗi lệnh +0,067 so với +0,012 của bản nền, tổng +16,7R so với +8,1R, sụt giảm 13,8R so với 40,9R) và đạt điều kiện "có lãi ổn định". Bảy phương pháp
còn lại giữ bản nền (Phá vỡ, ICT hồi về khoảng trống, Price Action: H2 tốt nhất trên phần chỉnh nhưng không qua cổng ở phần kiểm; ICT quét, Wyckoff,
Fibonacci, Hồi về EMA: bản nền tốt nhất trên phần chỉnh). Đã áp: `phieu.CONG_THUC['elliott']['loc'] = ('H2',)`. 139 phép so tính tới nay: một biến thể
qua cổng vẫn có thể do may; theo dõi dưới đây.

# Theo dõi Elliott có hợp lưu H2 trên dữ liệu mới (ghi TRƯỚC)

Ngày ghi: 26/11/2026 (khoảng 23 giờ 30), trước khi đo phần này lần nào. `cong-cu/do_lai_du_lieu_moi.py` thêm nhóm "Công thức phiếu có hợp lưu H2": chỉ
tín hiệu từ 00:00 UTC ngày 27/11/2026; kỳ vọng là R mỗi lệnh của bản H2 ở phần kiểm 2022–2026 (`out/hop-luu.json`). Cách kết luận y như phần "Đo lại
trên dữ liệu mới" (dưới 30 lệnh chưa kết luận; khoảng tin cậy 90%; "kém kỳ vọng rõ"). Với `--doi-chieu`, mốc 01/01/2022 phải ra đúng số phần kiểm của
bản H2. Chạy cùng nhịp hằng tháng; không chỉnh luật theo số này. Elliott có khoảng 50 lệnh mỗi năm sau bộ lọc, nên cần khoảng 7–8 tháng mới đủ 30 lệnh.


# Đồng bộ quy tắc hủy lệnh chờ khi giá chạy tới 2R trước khi khớp (ghi TRƯỚC)

Ngày ghi: 28/11/2026, trước khi đo lần nào. Lý do: bản chạy trực tiếp (`phuong_phap.hien_tai`) bỏ lệnh chờ khi giá đã chạy tới mục tiêu 2R trước
khi về mức chờ, nhưng phép chấm đã đo (`phuong_phap.cham`) KHÔNG có quy tắc này; bản trực tiếp lại chỉ xét nến M15 đã đóng nên áp không đều
(phát hiện 27/11: ICT còn "hiệu lực" khi bid 3650,9 đã qua 2R 3642,42). Hai bên phải cùng một quy tắc.

Áp cho ba phương pháp lệnh chờ: `ict`, `ict_fvg`, `fib`. Không đổi gì khác (cách vào, SL, TP 2R, giữ 24 giờ, spread và phí của cấu hình).
- A: phép chấm hiện tại (không hủy ở 2R).
- B: như A, thêm: trước nến khớp, nếu giá chạm mức vào ± 2 × |vào − SL| về phía có lãi (MUA: đỉnh M1 ≥ mức đó; BÁN: đáy M1 + spread ≤ mức đó)
  thì lệnh chờ bị hủy (thứ tự trong cùng một nến: coi là chạm 2R trước, như bản trực tiếp).

Cách đo: như "Chuẩn hóa theo sách" ở trên (vàng từ 2015, M1 + M15 của webapp, `quet` + phép chấm, mỗi lúc một lệnh). Hai nửa HỌC trước 1/5/2023,
KIỂM từ 1/5/2023. Báo: số lệnh, thắng, R mỗi lệnh, tổng R, số lệnh bị hủy thêm, cho từng phương pháp và từng nửa.

Quyết định, theo từng phương pháp, không xem lại sau khi có số:
- Giữ B (bản trực tiếp tính cả giá tick, phép chấm thêm quy tắc 2R) nếu R mỗi lệnh của B cao hơn A ở CẢ HAI nửa.
- Còn lại: bỏ quy tắc hủy 2R khỏi bản trực tiếp để khớp với số đã đo (A).
Đây là đồng bộ định nghĩa, không phải tìm bản có lãi: cả hai nhánh đều làm bản trực tiếp khớp phép đo. Một biến thể tốt hơn ở cả hai nửa vẫn có thể do may.

Kết quả (28/11/2026, `cong-cu/do_huy_2r.py`, `out/huy-2r.json`; bản chép khi tắt quy tắc mới khớp từng lệnh với `phuong_phap.cham`):
- ict: A 4575 lệnh, R mỗi lệnh −0,093 (HỌC −0,1205, KIỂM −0,0323); B hủy thêm 119, R −0,090 (HỌC −0,1140, KIỂM −0,0376). Không cao hơn ở nửa KIỂM → theo A.
- ict_fvg: A 4581 lệnh, −0,1496 (HỌC −0,1859, KIỂM −0,0710); B hủy thêm 352, −0,1539 (HỌC −0,1908, KIỂM −0,0754). Kém hơn cả hai nửa → theo A.
- fib: A 3700 lệnh, −0,1011 (HỌC −0,1132, KIỂM −0,0725); B hủy thêm 134, −0,1024 (HỌC −0,1162, KIỂM −0,0691). Không cao hơn ở nửa HỌC → theo A.
Đã áp: bỏ quy tắc hủy 2R khỏi `phuong_phap.hien_tai`; bản trực tiếp giờ đúng định nghĩa đã đo. Ghi chú: ở định nghĩa gốc cả ba phương pháp có R mỗi
lệnh âm ở cả hai nửa; đây không phải bằng chứng có lợi thế.
