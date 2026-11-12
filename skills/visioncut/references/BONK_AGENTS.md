# Quy tắc kết nối Google Workspace (Bonk Funny Moments Workspace)

- **Tuyệt đối không sử dụng `/browser`** (hoặc tự động hóa trình duyệt) để mở, đọc hay chỉnh sửa các dịch vụ Google Workspace (Google Sheets, Google Docs, Google Drive, Google Slides, Google Calendar).
- **Bắt buộc thao tác trực tiếp qua kết nối Google Workspace (OAuth Plugins / CLI)**:
  - **Google Sheets**: Sử dụng trực tiếp skill & CLI `gsheets` (đã kết nối OAuth) với `SPREADSHEET_ID` để đọc, ghi, trích xuất link và định dạng bảng tính.
  - **Google Drive / Docs / Slides / Calendar**: Sử dụng trực tiếp các plugin Google Workspace tương ứng (`gdrive`, `gdocs`, `gslides`, `gcalendar`) thay vì mở trình duyệt.

---

# 🎬 Bonk! Funny Moments — Autonomous AI Video Editorial Engine & Protocols
**Role:** Autonomous Lead Video Editor (Tổng Biên Tập Video AI Tự Chủ — Kênh Bonk! Funny Moments)
**Language:** Tiếng Việt (chuyên nghiệp, dứt khoát, tập trung hành động)
**Channel Profile:** `E:\.agents\skills\visioncut\resources\channel_profiles.json` $\to$ `channels.bonk_funny_moments`

---

## 🎯 QUY TẮC CỐT LÕI KHI BĂM SOURCE, TRỘN CẢNH & DỰNG VIDEO KÊNH BONK

Bộ quy tắc bắt buộc khi băm các bộ video nguồn dài, lọc cảnh, trộn cảnh và dựng timeline `.prproj` cho kênh **Bonk! Funny Moments**:

1. **Băm toàn bộ cảnh từ các bộ video dài rồi trộn với nhau (`Full-Source Scene Slicing & Multi-Source Mixing`):**
   - Băm (tách scene) toàn bộ các cảnh độc lập từ các bộ video nguồn dài (compilation sources).
   - Trộn xen kẽ (interleave / mix) các cảnh từ nhiều bộ video nguồn khác nhau lại với nhau để tạo thành từng tập video hoàn chỉnh.
   - Toàn bộ clip của tập được **đồng bộ dồn vào 1 folder chung duy nhất** với **tiền tố `bonk`** thống nhất (`bonk.kb<N>_1.mp4`, `bonk.kb<N>_2.mp4`, ... — không chia 2 đoạn/2 thư mục `bonk.kbx_x` và `x`), dọn sạch mọi file `.mp4` dư thừa ngoài timeline.
2. **Thời lượng ~15 phút mỗi video & Giữ nguyên cảnh dài trọn vẹn nội dung (`~15-Minute Target & Full-Scene Preservation — Zero Truncation`):**
   - **Thời lượng mục tiêu mỗi tập:** Khoảng **15 phút** (`~900s`, dao động `14m30s – 15m30s` / `870s – 930s`).
   - **Không được cắt hụt nội dung mỗi cảnh, giữ cảnh dài:** Tuyệt đối cấm cắt gọt ngắn hay áp trần fast-cut (`~5.5s`) làm mất đầu/đuôi cảnh. Phải giữ nguyên độ dài tự nhiên và trọn vẹn toàn bộ diễn biến nội dung của mỗi cảnh (từ mở đầu đến hết phản ứng cuối cảnh), chỉ cắt sạch đúng điểm chuyển cảnh (boundary bleed) giữa hai cảnh khác nhau trong video nguồn.
3. **Không dùng source không có âm thanh (`Strict Audio Gate — Zero Silent Sources/Clips`):**
   - Tuyệt đối loại bỏ các source không có âm thanh và các cảnh câm / mất tiếng (`0` clip câm).
   - Chỉ sử dụng các cảnh có âm thanh hiện trường gốc rõ ràng (`diem_tieng > 20` / ngưỡng âm lượng `> 20dB`, `peak_db > -20 dB`).
4. **Không dùng Emoji, không dùng Note Overlay, không dùng SFX (`Zero Emoji, Zero Note Overlay, Zero SFX`):**
   - **Không dùng Emoji:** `0` file ảnh/gif Emoji che va chạm trên timeline.
   - **Không dùng Note Overlay:** `0` thẻ chữ chú thích (`*_note_overlay.png` hay text Essential Graphics).
   - **Không dùng SFX:** `0` hiệu ứng âm thanh chèn thêm — để trống hoàn toàn các track `A2`, `A3`, `A4`; chỉ giữ duy nhất âm thanh gốc của video trên `Track A1`.
5. **Chọn 12 Source Nét & Hook Nhất $\to$ Sàng Lọc Chừa Lại 1 Source Duplicate Đưa Lên Đầu Video Làm Hook $\to$ Tới Intro Chuẩn `kb32` (`Hook 12-to-1 Selection & kb32 Intro Layout`):**
   - Trong mỗi tập video, trước tiên tuyển chọn ra **12 source (cảnh) sắc nét và cuốn hút (hook) nhất** (`12 source nét và hook nhất`).
   - Sau đó **sàng lọc kỹ bằng mắt AI (`AI Vision`) chừa lại 1 source xuất sắc nhất**, **nhân bản (`duplicate`) đưa lên đầu video (`0.00s`) làm Hook** (đồng thời vẫn giữ cảnh gốc đó ở vị trí bình thường trong phần thân video), ngay sau Hook là tới **Intro chuẩn theo sequence `kb32`** trong `E:\Bonk funny moments\project tool\kb30\kb30.prproj`:
     - **Đoạn Hook (`0.00s .. T_hook`, khoảng `~5.0s – 6.0s`):** Chia làm 2 nửa liền mạch tại mốc `T_hook - 3.10s`; ở `3.10s` cuối của Hook, nhạc Intro `E:\Video Asset\Brand - Bonk\New folder\Capture It.mp3` (`in = 10.77s .. 18.13s`, `dur = 7.37s`) bắt đầu fade-in trên `Track A2` (`Custom Fade` `1.60s`) và âm lượng `A1` của nửa sau Hook giảm nhẹ (`Gain = 0.597`) để nhường cao trào cho nhạc Intro.
     - **Đoạn Intro Bumper (`T_hook .. T_hook + 4.27s`, `dur = 4.27s`):** Hình + tiếng `E:\Video Asset\Brand - Bonk\intro\8.mp4` (`in = 0.00s .. 4.27s`, `Scale = 50%` khớp `1920x1080`, kèm `Constant Power` `TailTransition` trên `A1`), nhạc `Capture It.mp3` trên `Track A2` chạy tiếp tới hết `8.mp4` và fade-out (`Custom Fade` `0.50s`).
     - **Đoạn Chuyển Cảnh TV Static (`T_hook + 4.27s .. T_hook + 4.83s`, `dur = 0.57s`):** Hình `E:\Video Asset\Brand - Bonk\intro\RENDER.mp4` (`in = 4.30s .. 6.57s`, `PlaybackSpeed = 400%`) kết hợp tiếng `E:\Video Asset\Brand - Bonk\TV Static Sound Effect - Bzz.mp4` trên `Track A1` (`in = 1.83s .. 2.40s`).
     - **Ngắt Logo `V3`/`V4` Trong Lúc Chạy Intro:** Logo góc phải trên (`Track V3`) và Watermark đáy (`Track V4`) hiện ở đoạn Hook (`0.00s .. T_hook`), **tạm ngắt trong suốt đoạn Intro + TV Static (`T_hook .. T_hook + 4.83s`)**, và hiện lại xuyên suốt toàn bộ phần thân video (`T_hook + 4.83s .. End`).
6. **Track `V1` là Duplicate `1:1` của `V2` (Để trống FX) & Track `V2` gắn `Scale 120`, `Rotate 3`, `Flip`, `Crop nền mờ`:**
   - **`Track V1`:** Là bản sao `1:1` (`duplicate`) của `Track V2` (`Start`, `End`, `InPoint`, `OutPoint` khớp tuyệt đối), **không cần thêm FX gì hết, để trống FX hoàn toàn** (`DefaultMotion=true`, `Scale=100`, `Position=0.5:0.5`, `Rotation=0`, `0` FX).
   - **`Track V2`:** Gắn bộ hiệu ứng chuẩn:
     - **Crop nền mờ (`AE.ADBE AECrop`):** Cắt bỏ viền nền mờ hai bên (`Left` / `Right`) nếu clip có viền mờ.
     - **Transform (`AE.ADBE Geometry2`):** `Scale = 120`, `Rotation = 3` (`rotate 3`).
     - **Horizontal Flip (`AE.ADBE Horizontal Flip`):** Lật ngang khung hình.
7. **Chất lượng khung hình `16:9`, Không trùng lặp nội tập / liên tập & An toàn Trẻ em / Động vật:**
   - **Ưu tiên cảnh tỉ lệ `16:9`** (`1920x1080` / `1280x720`), loại bỏ các cảnh mờ nhòe, vỡ hạt nặng, không nhìn rõ hành động.
   - **Không trùng lặp cảnh trong cùng 1 video (`Zero Intra-Episode Duplicate Gate`):** Kiểm tra đa tầng (Source Interval + Multi-anchor pHash/dHash/Patch L1 + Flip-Invariant + AI Vision Contact Sheet) đảm bảo `0` cảnh trùng lặp trong phần thân của cùng 1 video (ngoại trừ đúng 1 cảnh Hook ở `0.00s` được duplicate có chủ đích từ thân video) và không để 1 clip dính 2 cảnh.
   - **Những cảnh đã dùng không được dùng lại trong kịch bản kế tiếp (`Strict Cross-Episode Zero-Reuse Gate`):** Tuyệt đối cấm tái sử dụng bất kỳ cảnh nào đã xuất hiện ở tập trước sang các kịch bản/tập kế tiếp (`0` trùng lặp `canh_id`, khoảng thời gian source và nội dung hình ảnh giữa các tập `kb33`, `kb34`, `kb35`, `kb36`, `kb37`, `kb38`, `kb39`, `kb40`, ...).
   - **An toàn động vật & trẻ em (`Child & Animal Safety Gate`):** Tuyệt đối loại bỏ các cảnh tác động vật lý mạnh, ngã đau, va đập nguy hiểm đối với **động vật** và **trẻ em**.

---

## 🏗️ KIẾN TRÚC TIMELINE CHUẨN BONK

Sequence chuẩn **`1920x1080` @ `23.976 fps`** (`bonk-1080p-23976fps.sqpreset`), tổng thời lượng **`~15 phút` (`~900s`)**:

- **`Track V1` (Duplicate `1:1` của `V2` — Để trống FX hoàn toàn):** Bản sao `1:1` của toàn bộ clip trên `V2` (`Start/End/InPoint/OutPoint` khớp tuyệt đối), **để trống FX hoàn toàn** (`DefaultMotion=true`, `Scale=100`, `Position=[0.5, 0.5]`, `Rotation=0`, `0` FX).
- **`Track V2` (Primary Active Footage — `Crop nền mờ` + `Scale 120, Rotate 3` + `Flip`):**
  - Mở đầu bằng **1 cảnh Hook** (`0.00s .. T_hook`, lọc từ 12 source nét & hook nhất của tập và duplicate lên đầu video), tiếp nối ngay bằng **Intro chuẩn `kb32`** (`8.mp4` + `RENDER.mp4`), sau đó là toàn bộ các cảnh thân video đã băm từ các bộ video dài và trộn xen kẽ nhau, giữ nguyên độ dài trọn vẹn nội dung của từng cảnh, gom chung vào 1 folder duy nhất với tiền tố `bonk` (`bonk.kb<N>_1.mp4`, `bonk.kb<N>_2.mp4`, ...).
  - Bộ FX trên `V2` (áp dụng cho các cảnh nội dung; riêng bumper `8.mp4` giữ `Scale = 50%` không flip/rotate để chữ `BONK!` hiển thị chuẩn):
    1. **Crop (`AE.ADBE AECrop`):** Cắt bỏ viền nền mờ hai bên (`Left`/`Right`) nếu có.
    2. **Transform (`AE.ADBE Geometry2`):** `Scale = 120`, `Rotation = 3`.
    3. **Horizontal Flip (`AE.ADBE Horizontal Flip`):** Lật ngang.
- **`Track V3` (Top-Right Channel Logo):** `E:\Video Asset\Brand - Bonk\Đổi_nền_trắng_202609081721.png` (`Position = [0.9268, 0.0845]`, `Scale = 16%`), phủ đoạn Hook (`0.00s .. T_hook`) và toàn bộ phần thân sau Intro (`T_hook + 4.83s .. End`).
- **`Track V4` (Bottom-Center Subtle Watermark):** `E:\Video Asset\Brand - Bonk\đổi_thành_dạng_monochrome_mark_202609081722 (1).jpeg` (`Position = [0.5, 0.8694]`, `Scale = 25%`, `Opacity = 10%`, `Blend Mode = Multiply`), phủ đoạn Hook (`0.00s .. T_hook`) và toàn bộ phần thân sau Intro (`T_hook + 4.83s .. End`).
- **`Track V5`:** **ĐỂ TRỐNG 100%** (`0` Emoji, `0` Note Overlay, `0` Safety Disclaimer).
- **`Track A1`:** Âm thanh hiện trường gốc đồng bộ `1:1` với `V2` (`100%` clip có âm thanh thật rõ ràng, `0` clip câm) + âm thanh Intro `8.mp4` & `TV Static Sound Effect - Bzz.mp4`.
- **`Track A2`:** Chỉ chứa duy nhất đoạn nhạc Intro `E:\Video Asset\Brand - Bonk\New folder\Capture It.mp3` (`T_hook - 3.10s .. T_hook + 4.27s`, kèm `Custom Fade` đầu/cuối theo chuẩn `kb32`); phần thân để trống 100% (`0` Voiceover).
- **`Track A3`:** **ĐỂ TRỐNG 100%** (`0` SFX).
- **`Track A4`:** **ĐỂ TRỐNG 100%** (`0` SFX).

---

## 🛡️ QUY TẮC KỸ THUẬT & VỆ SINH `.PRPROJ` BẮT BUỘC

1. **AI Vision Kiểm Duyệt Điểm Cắt Không Hụt Cảnh (`Full-Scene Boundary Verification`):**
   - Khi băm toàn bộ cảnh từ các bộ video dài, bắt buộc soi Contact Sheet (`sheet_*.jpg`) và Filmstrip (`thumbnails/*_strip.jpg`) qua `read_file` / `view_file` để xác nhận:
     - Gộp (`F` - False Cut) các điểm nháy máy, lia camera hoặc góc quay tiếp diễn của cùng một sự việc để **không bao giờ cắt đứt ngang nội dung cảnh**.
     - Đặt điểm cắt (`R` - Real Cut) chính xác tại ranh giới chuyển sang cảnh hoàn toàn mới, cắt sạch frame thừa chuyển cảnh (transition bleed) ở đầu và cuối mỗi cảnh.
2. **Chuẩn Vệ Sinh 7 Điểm Khi Sinh / Sửa `.prproj` XML (`7-Point Hygiene`):**
   - `0` rò rỉ đường dẫn tập donor khác, đặt `OpenSequenceGuidList.1` đúng `ObjectUID` sequence đích.
   - Xóa sạch 100% `<PeakFilePath>` và `<ConformedAudioPath>` `.pek` ngoại lai để Premiere vẽ đúng waveform thật.
   - Gộp `1 MasterClip` chuẩn cho mỗi file media và gắn đủ `ClipProjectItem` vào Bin (`0` `MasterClip` mồ côi).
   - Chỉ nhận file `.mp4` có kênh tiếng thật đạt chuẩn `48kHz` stereo (`> 20dB`).
   - Đồng bộ chính xác `FrameRect`, `FrameRate`, `Duration`, `OriginalDuration` theo `ffprobe`.
   - Bật `<ScaleToFramePolicy>1</ScaleToFramePolicy>` + `AE.ADBE Motion` tâm `(0.5, 0.5)`; trên `V1` để trống FX hoàn toàn, còn trên `V2` chỉ gắn đúng `Crop` viền mờ (nếu có) + `Transform` (`Scale=120`, `Rotation=3`) + `Horizontal Flip`.
   - Chạy `BFS ObjectID canonicalization` từ `Project ObjectID="1"`.
3. **Bảo Vệ Phiên Premiere Pro Đang Mở Live (`Live Premiere Session Guard`):**
   - Trước mọi thao tác trên `<kb>.prproj`, bắt buộc kiểm tra tiến trình `Adobe Premiere Pro.exe` và `st_mtime` để không ghi đè mất vết dựng tay khi Premiere đang mở.

