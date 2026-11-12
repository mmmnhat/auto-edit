# Quy tắc kết nối Google Workspace (ITV Workspace)

- **Tuyệt đối không sử dụng `/browser`** (hoặc tự động hóa trình duyệt) để mở, đọc hay chỉnh sửa các dịch vụ Google Workspace (Google Sheets, Google Docs, Google Drive, Google Slides, Google Calendar).
- **Bắt buộc thao tác trực tiếp qua kết nối Google Workspace (OAuth Plugins / CLI)**:
  - **Google Sheets**: Sử dụng trực tiếp skill & CLI `gsheets` (đã kết nối OAuth) với `SPREADSHEET_ID` để đọc, ghi, trích xuất link và định dạng bảng tính.
  - **Google Drive / Docs / Slides / Calendar**: Sử dụng trực tiếp các plugin Google Workspace tương ứng (`gdrive`, `gdocs`, `gslides`, `gcalendar`) thay vì mở trình duyệt.

---

# 🎬 ITV Moments — Quy Tắc Tuyển Chọn Nội Dung, Băm Source & Dựng Video (`e:\ITV`)

Bộ quy tắc bắt buộc khi băm source, lọc cảnh và dựng timeline `.prproj` cho kênh **ITV Moments**:

1. **Tổng thời lượng video `15 phút` (`15-Minute Target Duration`):**
   - Tổng thời lượng thành phẩm của mỗi tập video tăng lên **`15 phút` (`~900s`)**.
2. **Không cắt hụt nội dung cảnh (`Full Scene Preservation — Zero Truncation`):**
   - Giữ trọn vẹn 100% diễn biến tự nhiên của từng cảnh (từ mở đầu tình huống `Setup`, diễn biến `Climax` cho đến hết phản ứng `Aftermath/Reaction`).
   - Tuyệt đối không bóp ngắn hay cắt cụt nội dung cảnh để ép thời lượng; chỉ cắt sạch đúng ranh giới chuyển cảnh (boundary bleed) và không để 1 clip chứa 2 cảnh (hard-cut nội bộ).
3. **Không che watermark/logo, không crop, không Emoji, không SFX (`Clean Native Visual & Audio Rule`):**
   - **Không che watermark / logo & Không crop:** Không gắn `Gaussian Blur` / `Mask2` che logo/chữ, không cắt `AECrop` viền và không phóng `Scale` Zoom-crop đẩy logo (giữ nguyên khung hình chuẩn `fit_scale` trên `1920x1080`).
   - **Không dùng Emoji:** Không đặt Animated Emoji / GIF trên `Track V4` (`0` Emoji).
   - **Không dùng SFX:** Không chèn hiệu ứng âm thanh SFX trên `Track A3` / `Track A4` (`0` SFX, giữ nguyên âm thanh gốc hiện trường trên `Track A1`).
4. **Ưu tiên cảnh có tỉ lệ `16:9` (`16:9 Aspect Ratio Priority Gate`):**
   - Ưu tiên tuyển chọn và sử dụng các cảnh quay khung ngang chuẩn `16:9` (`1920x1080` / `1280x720`), hạn chế tối đa các cảnh dọc `9:16` hoặc vuông `1:1` bị viền mờ hai bên.
5. **Không dùng những cảnh kém chất lượng, không nhìn rõ (`Quality & Clarity Gate`):**
   - Loại bỏ toàn bộ các cảnh bị mờ nhòe (blurry / độ nét thấp), vỡ hạt nặng, rung lắc mất nét, thiếu sáng/chói sáng hoặc chủ thể quá nhỏ, bị che khuất không nhìn rõ hành động và tình huống.
6. **Không dùng những cảnh không có âm thanh, âm thanh `> 20dB` (`Strict Audio Gate — Zero Silent Clips`):**
   - Tuyệt đối không dùng các cảnh câm / không có âm thanh gốc (`0` clip câm, xóa bỏ hoàn toàn đoạn Silent Montage đè nhạc BGM ở cuối video).
   - Chỉ sử dụng các cảnh có âm thanh hiện trường gốc rõ ràng (`diem_tieng > 20` / ngưỡng âm lượng `> 20dB`, `peak_db > -20 dB`).
7. **Không trùng lặp các cảnh trong cùng một video & giữa các kịch bản (`Zero Intra-Episode & Cross-Episode Duplicate Scene Gate`):**
   - Kiểm tra đa tầng (Source Interval `(vcode, start, end)` + Multi-anchor Active-Core pHash/dHash/Patch L1 + Flip-Invariant + AI Vision Contact Sheet) đảm bảo **0 cảnh trùng lặp** trong cùng một tập video cũng như không trùng với các tập đã dựng.
8. **Đồng bộ dồn vào 1 folder chung với tiền tố `itv` (`Unified Single-Folder & Prefix Rule`):**
   - Khi băm source và dựng **KHÔNG chia làm 2 đoạn / 2 thư mục** (`itv.kbx_x` trong `source/` và `x` trong `ITV-Moments-script-xx/`).
   - Toàn bộ clip của tập được **đồng bộ dồn vào 1 folder chung duy nhất** với **tiền tố `itv`** thống nhất (ví dụ: `itv.kbx_1.mp4`, `itv.kbx_2.mp4`, ...).
   - Dọn sạch mọi file `.mp4` dư thừa không nằm trên timeline.
9. **Loại bỏ những cảnh tác động mạnh động vật và trẻ em (`Child & Animal Safety Gate`):**
   - Tuyệt đối loại bỏ các cảnh có tác động vật lý mạnh, ngã đau, va đập nguy hiểm hoặc gây tổn thương/phản cảm đối với **động vật** và **trẻ em** (tuân thủ nghiêm ngặt chính sách an toàn trẻ em & phúc lợi động vật của YouTube). Chỉ giữ lại các tình huống hài hước người lớn hoặc khoảnh khắc an toàn, vô hại.
10. **Quy tắc chọn Intro Hook (`Top-40 to 11 Intro Hook Selection Rule`):**
    - Trong mỗi tập video, trước tiên lọc ra **`40 cảnh hay nhất` (Top 40 Best Scenes)** của tập (ưu tiên khung ngang `16:9` sắc nét, chuyển động cao trào mạnh, âm thanh hiện trường sống động).
    - Sau đó, từ 40 cảnh hay nhất này (kết hợp kiểm duyệt trực quan bằng mắt AI trên Contact Sheet), **sàng lọc ra đúng `11 cảnh xuất sắc nhất` (11 Intro Hook Scenes)** có khoảnh khắc Climax trực diện, bùng nổ nhất để dựng phần **Intro Hook** ở đầu video (cắt `InPoint..OutPoint` trúng ngay đỉnh va chạm/cao trào của từng cảnh).
11. **Không dùng lại những cảnh đã dùng trong kịch bản kế tiếp (`No Scene Reuse Across Subsequent Scripts`):**
    - Mọi cảnh đã được tuyển chọn và sử dụng trong một kịch bản/tập video **tuyệt đối không được dùng lại** trong kịch bản kế tiếp (và các kịch bản về sau).
    - Bắt buộc lưu vết và đối chiếu chéo toàn bộ cảnh mới với kho lịch sử các cảnh đã dùng của các tập trước (so khớp `Source Video ID + Time Interval` và `Multi-anchor Active-Core pHash/dHash/Patch L1 + Flip-Invariant`) để loại bỏ ngay lập tức mọi cảnh đã từng xuất hiện.

---

@[VisionCut Shared E-Drive Rules](E:/AGENTS.md)
