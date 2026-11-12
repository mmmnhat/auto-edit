# 🐾 Animal Whoops — Quy Tắc Dựng Video & Chuẩn Kỹ Thuật Premiere Pro

Tài liệu này quy định bộ quy tắc bắt buộc khi băm source, tuyển chọn cảnh và dựng timeline `.prproj` cho kênh **Animal Whoops** (`E:\Animal Whoops\aw*`).

---

## 1. Quy Tắc Tuyển Chọn Nội Dung & Băm Source

1. **Không dùng cảnh kém chất lượng, không nhìn rõ (`Quality & Clarity Gate`):**
   - Loại bỏ toàn bộ các cảnh bị mờ nhòe (blurry / độ nét thấp), vỡ hạt nặng, thiếu sáng/chói sáng hoặc chủ thể động vật quá nhỏ, bị che khuất không nhìn rõ hành động.
2. **Không dùng cảnh không có âm thanh, âm thanh `> 20dB` (`Strict Audio Gate`):**
   - Tuyệt đối không dùng cảnh câm (`0` clip câm, không dựng đoạn Silent Montage đè nhạc BGM ở cuối video).
   - Chỉ sử dụng các cảnh có âm thanh gốc rõ ràng (`diem_tieng > 20` / ngưỡng âm lượng `> 20dB`, `peak_db > -20 dB`).
3. **Không trùng lặp các cảnh trong cùng một video (`Intra-Episode Zero Duplicate Gate`):**
   - Kiểm tra đa tầng (Source Interval `(vcode, start, end)` + Multi-anchor Active-Core pHash/dHash/Patch L1 + Flip-Invariant + AI Vision Contact Sheet) đảm bảo **0 cảnh trùng lặp** trong cùng một tập.
   - Cắt bỏ triệt để frame thừa chuyển cảnh (boundary bleed) và không để 1 clip chứa 2 cảnh (hard-cut nội bộ).
4. **Những cảnh đã dùng không được dùng lại trong kịch bản kế tiếp (`Cross-Episode Zero Reuse Gate`):**
   - Tuyệt đối **không tái sử dụng bất kỳ cảnh nào đã xuất hiện ở các kịch bản/tập trước đó** sang kịch bản kế tiếp (xuyên suốt chuỗi kịch bản `aw1_1` $\to$ `aw1_2` $\to$ ... $\to$ `aw4_4` và các batch tiếp theo).
   - Duy trì bộ lọc toàn cục (`global_used_scenes`) kiểm tra đồng thời khoảng thời gian gốc `(vcode, start, end)` và đặc trưng thị giác (`Multi-frame dHash/Patch Correlation` bất biến lật ngang) để khóa vĩnh viễn mọi cảnh đã dùng.
5. **Đồng bộ vào 1 folder chung với tiền tố `awx` (`Single-Folder & Prefix Rule`):**
   - Khi băm source và dựng **KHÔNG chia làm 2 đoạn / 2 thư mục** (`bonk.awx_x` trong `source/` và `x_fxxx` trong `Bonk-script-xx/`).
   - Toàn bộ clip của tập được **dồn đồng bộ vào 1 folder chung duy nhất** với **tiền tố `awx`** (ví dụ: `aw1_1.1_f307.mp4`, `aw1_1.2_f158.mp4`, ...).
   - Dọn sạch mọi file `.mp4` dư thừa không nằm trên timeline.
6. **Loại bỏ những cảnh tác động mạnh động vật (`Animal Welfare & Safety Gate`):**
   - Tuyệt đối loại bỏ các cảnh động vật bị va đập mạnh, ngã đau nguy hiểm, bị đánh/tác động vật lý mạnh hoặc gây phản cảm. Chỉ giữ lại các tình huống hài hước, ngộ nghĩnh, vụng về nhẹ nhàng và an toàn.

---

## 2. Cấu Trúc Timeline Premiere Pro (`V1` – `V5` & `A1` – `A3`)

- **Độ phân giải & Khung hình:** `1920x1080` (`23.976 fps`, `10594584000` ticks/frame).
- **Mở đầu (Hook + Intro):**
  - **Hook (`0` $\to$ `hook_end_ticks`):** Sàn lọc **15 source** ứng viên hài hước/cao trào nhất từ phần thân video, chọn ra **3 source** xuất sắc nhất **duplicate** đưa lên đầu video làm Hook (gắn đầy đủ V3 FX + V1 OG + V2 Adjustment Layer + V4 Logo + V5 Watermark + A1 Audio `Speed = 106%` Optical Flow).
  - **Intro (`hook_end_ticks` $\to$ `hook_end_ticks + 1525620096000` ticks = `6.006s`):** Đặt `"E:\Video Asset\Animal Whoops\intro.mp4"` ngay sau 3 cảnh Hook trên **Track V3** (`Scale = 50%`, `Position = 960:540`) và **Track A1** (`PlaybackSpeed = 1.1`, `OutPoint = 1678182105600`).
  - **Thân bài (`hook_end_ticks + 1525620096000` $\to$ hết sequence):** Toàn bộ phần thân video (`V1`, `V2`, `V3`, `V4`, `V5`, `A1`) nối tiếp ngay sau `intro.mp4` đến hết sequence.

| Track | Thành phần | Đường dẫn Asset / Nguồn | Thông số Kỹ thuật & Hiệu ứng (FX) |
| :--- | :--- | :--- | :--- |
| **V5** | **Watermark** | `"E:\Video Asset\Animal Whoops\wtm.jpg"` | Kéo dài toàn bộ thân video. `Position = 960:940` (`0.5 : 0.870370388`), `Scale = 30`, `Opacity = 10%`, `Blend Mode = Screen` (`17`). |
| **V4** | **Logo Kênh** | `"E:\Video Asset\Animal Whoops\Logo Animal Whoops.png"` | Kéo dài toàn bộ thân video. `Position = 1820:100` (`0.9479166865 : 0.0925925895`), `Scale = 12`. |
| **V3** | **Video Chính** | Các clip `awx` đã băm | - **Speed:** `106%` (`PlaybackSpeed = 1.06`) với **Optical Flow** (`TimeInterpolationType = 2`).<br>- **Crop (`AE.ADBE AECrop`):** Cắt sạch nền mờ 2 bên (`Left/Right = crop_lr_pct`) nếu là video dọc/vuông.<br>- **Transform (`AE.ADBE Geometry2`):** **Zoom (Scale) = `120`**, **Rotate = `3`** (`3.0°`).<br>- **Flip (`AE.ADBE Horizontal Flip`):** Lật ngang.<br>- **Lumetri (`AE.ADBE Lumetri`):** Chỉnh màu sáng rõ (`Temp=30, Tint=-2, Exposure=0.2, Contrast=10, Highlights=-10, Saturation=105`). |
| **V2** | **Adjustment Layer** | `Adjustment Layer` nội bộ | Kéo dài toàn bộ thân video. Gắn **Lumetri Color (`AE.ADBE Lumetri`)** với **Exposure = `-5`** (`-5.0`). |
| **V1** | **Video Nền (OG)** | Duplicate 1:1 từ **Track V3** | Nhân bản toàn bộ các clip thân bài từ **V3** xuống **V1** (giữ nguyên vị trí timeline và `Speed = 106%` Optical Flow), **không gắn FX (`không fx, og`)** — giữ nguyên `AE.ADBE Motion` mặc định (`Scale = 100%`, `Position = 960:540`, `Rotation = 0`). |
| **A1** | **Audio Gốc** | Audio của `intro.mp4` + các clip `awx` | Đồng bộ 1:1 với **Track V3** (`PlaybackSpeed = 1.06`, `MaintainAudioPitch = true`). |
| **A2 / A3** | **SFX** | `"E:\Video Asset\SFX"` | Điểm xuyết SFX hài hước nhẹ nhàng đúng cao trào, không lấn át âm thanh gốc. |
