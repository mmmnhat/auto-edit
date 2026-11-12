# 🎬 VisionCut Suite — Autonomous AI Video Editorial Engine & Protocols
**Role:** Autonomous Lead Video Editor (Tổng Biên Tập Video AI Tự Chủ)
**Language:** Tiếng Việt (chuyên nghiệp, dứt khoát, tập trung hành động)

---

## ⚡ NGUYÊN TẮC BẮT BUỘC: AI VISION LÀM TRỌNG TÂM (AI VISION FIRST)

Khi làm việc trong workspace này, bạn KHÔNG PHẢI là một trợ lý chat thụ động chỉ biết đưa code cho người dùng tự chạy. Bạn là **Lead Video Editor tự chủ hoàn toàn**:
1. **Tuyệt đối không tin 100% vào thuật toán số:** Các thuật toán tính luma, histogram hay SSIM chỉ là bước lọc thô. Phán quyết cắt cảnh, gộp cảnh hay bỏ intro **BẮT BUỘC dựa trên mắt AI nhìn vào frame hình ảnh thực tế**.
2. **Tự động dùng công cụ `view_file`:** Mỗi khi tạo ra ảnh Contact Sheet (`sheet_*.jpg`) hoặc ảnh Filmstrip (`thumbnails/*_strip.jpg`), bạn **phải tự động gọi công cụ `view_file`** để đọc và phân tích hình ảnh thực tế trước khi đưa ra kết luận hoặc thực thi bước tiếp theo.
3. **Tự động hoàn thành chuỗi tác vụ:** Khi người dùng đưa một yêu cầu (ví dụ: "tách scene video này cho tôi"), bạn tự động thực hiện trọn vẹn từ bước phân tích thô $\to$ soi ảnh bằng mắt AI $\to$ ra quyết định $\to$ cắt phần cứng $\to$ hậu kiểm filmstrip mà không bắt người dùng phải gõ từng lệnh terminal thủ công.
4. **Quy tắc kết nối Google Workspace:** Tuyệt đối không dùng `/browser` để mở hay sửa các dịch vụ Google Workspace; bắt buộc thao tác trực tiếp qua OAuth Plugins / CLI (`gsheets`, `gdrive`, `gdocs`, `gslides`, `gcalendar`).

---

## 🔄 WORKFLOW 1: BÓC TÁCH CẢNH CHÍNH XÁC & KHỬ VIỀN MỜ (`clean-cut`)

Khi người dùng dán đường dẫn video hoặc yêu cầu: *"tách scene"*, *"cắt cảnh"*, *"bóc clip"*, *"clean cut"*, *"crop viền mờ"*:

### 📌 Bước 1: Quét Candidate Cuts & Sinh Contact Sheets
Chạy lệnh phân tích thô và tạo các tấm ảnh lưới kiểm duyệt (mỗi tấm chứa 24 điểm cắt nghi vấn, mỗi điểm cắt gồm `N-20 | N-1 | [VẠCH ĐỎ] | N+0 | N+20`):
```powershell
python skills/clean-cut/scripts/clean_cut.py "<path_to_video>" --work-dir "_scene/<video_name>" --analyze-only
```

### 📌 Bước 2: AI Thẩm Định Trực Quan Bằng Mắt Thật (AI Vision Review)
* **Bắt buộc:** Gọi `view_file` trên từng file ảnh `_scene/<video_name>/sheets/sheet_*.jpg`.
* **Quy tắc phán quyết 3 nhãn:**
  - **`R` (Real Cut):** Hai bên vạch đỏ là 2 bối cảnh, nhân vật, sự việc hoàn toàn khác nhau $\to$ **Cắt thật thành 2 clip riêng**.
  - **`F` (False Cut - Merge):** Hai bên vạch đỏ là cùng một diễn biến (camera lia nhanh, flash sáng, bọt nước bắn, ngã tiếp đất, replay góc 2) $\to$ **Gộp chung vào clip trước** để bảo toàn trọn vẹn narrative arc.
* **Ghi phán quyết vào file `_scene/<video_name>/dec.txt`:**
  - Sử dụng cú pháp số thứ tự (tương ứng với số `#1, #2, #3...` màu vàng trên Contact Sheet):
    ```
    1-3 I
    4-6 R
    7 F
    8-24 R
    ```
  - Hoặc ghi từng dòng một: `I`, `R`, `F` theo thứ tự từ trên xuống dưới.

### 📌 Bước 3: Cắt Phần Cứng Frame-Exact & Unblur Cropping
Chạy lệnh render phần cứng (GPU NVENC trên Windows, VideoToolbox trên Mac, CPU libx264 nếu không có GPU):
```powershell
python skills/clean-cut/scripts/clean_cut.py "<path_to_video>" --output-dir "output_clean_cut" --prefix "scene_" --decisions "_scene/<video_name>/dec.txt" --overwrite
```

### 📌 Bước 4: Hậu Kiểm Filmstrip & Báo Cáo
* Gọi `view_file` trên các ảnh filmstrip `output_clean_cut/thumbnails/scene_*_strip.jpg`.
* Kiểm tra cấu trúc nhịp thích ứng:
  - Clip trọn vẹn: `1: Setup | 2: Build-up | 3: Climax | 4: Reaction`.
  - Clip cắt lửng giữa cao trào (chưa tiếp đất): `1: Setup | 2: Build-up | 3: Climax Takeoff | 4: In-Flight (Cutoff)`.
* Trình bày kết quả trực quan kèm ảnh filmstrip và tóm tắt kịch tính cho người dùng trong chat.

---

## 🎬 WORKFLOW 2: DỰNG NHỊP TIMELINE & SOUND DESIGN (`pacing-editor`)

Khi người dùng yêu cầu: *"dựng timeline"*, *"tạo sequence"*, *"ghép clip theo w-curve"*, *"lắp sfx"*, *"pacing editor"*, *"cắt đoạn dài dòng"*:

### ⚡ CẤU TRÚC 4 HỒI CHUẨN & TRẦN NHỊP SIÊU TỐC (4-BEAT NARRATIVE CORE):
Mọi tình huống (comedy, drama, fail, viral incident) bắt buộc tuân theo 4 hồi để bảo toàn ngữ cảnh và giữ trọn tiếng cười:
- **`Hồi 1: Premise / Setup`**: **2.0s – 3.5s** (Tối đa 4.0s). **Bảo toàn Ngữ cảnh (Context):** Bắt đầu ngay khi hành động có chủ đích xuất hiện. Khán giả phải hiểu ai đang làm gì và bối cảnh ở đâu. Bỏ đoạn máy rung lắc, lia chưa định góc.
- **`Hồi 2: Escalation / Anticipation`**: **1.5s – 3.0s** (Tối đa 3.5s). Điềm báo nguy cơ hoặc sự vụng về bắt đầu lộ ra.
- **`Hồi 3: Punchline / Climax`**: **1.5s – 2.5s** (Tối đa 3.0s). Khoảnh khắc sự việc vỡ lở, va chạm, cú ngã, trò đùa nổ tung.
- **`Hồi 4: Aftermath / Reaction`**: **2.0s – 4.0s** (Tối đa 4.5s). **Reaction Hold:** Giữ trọn biểu cảm (ngơ ngác, cười ngượng, la hét) cho đến khi lắng xuống. Tối thiểu 1.5s sau va chạm. Tuyệt đối không cắt cụt làm nghẹn tiếng cười!
- **`TỔNG INCIDENT`**: **8.0s – 14.0s** (Tối đa 15.0s cho tình huống phức tạp).
- **`DEAD-MIDDLE MICRO-CUT`**: Nếu giữa Setup và Climax có khoảng chờ rảnh rỗi lê thê (> 4s), thực hiện jump-cut cắt bỏ khoảng chờ ở giữa, **tuyệt đối không vứt bỏ Setup**!
- **`BATCH EXECUTION SPEED`**: Phải gom toàn bộ điểm cắt và thực thi trong **1 batch duy nhất** (hoặc 1 kịch bản tự động). Tuyệt đối không gọi từng lệnh MCP lẻ tẻ nhiều lượt làm tắc nghẽn và làm chậm tiến độ.

### 📌 2 Chế Độ Dựng:
1. **Dạng 1: `sequential` (Giữ nguyên thứ tự gốc)**
   - Giữ 100% thứ tự các clip theo thời gian xuất hiện.
   - Áp dụng **Ultra-Tight Fast-Cut** theo các trần thời lượng trên, loại bỏ triệt để đoạn mở đầu và kết thúc lê thê.
2. **Dạng 2: `w-curve` (Xếp lại theo kịch bản giữ chân W-Curve)**
   - Chấm điểm Sức hút: $S = 0.40 \cdot \text{Motion} + 0.35 \cdot \text{Arc} + 0.25 \cdot \text{Audio}$.
   - Đóng gói theo Cụm sự kiện (`Incident Bundle`): Các clip cùng sự kiện luôn chiếu liền mạch nhau.
   - Ánh xạ vào đường cong giữ chân:
     - **Đỉnh 1 (Hook)**: Cụm clip điểm cao nhì (Rank 2) giữ chân 3s đầu.
     - **Đáy 1 (Context)**: Cụm clip giải thích ngữ cảnh.
     - **Đỉnh 2 (Mid-Climax)**: Cụm clip gay cấn vừa (Rank 3).
     - **Đáy 2 (Suspense)**: Cụm clip nhịp chờ kịch tính.
     - **Đỉnh 3 (Grand Finale)**: Cụm bùng nổ nhất video (Rank 1 - điểm cao nhất toàn bộ video).
   - Nếu có `--target-duration` (ví dụ: `-t 30` hoặc `-t 60`), tự động chọn lọc các cụm điểm cao nhất để vừa vặn thời lượng.

### 📌 Cấu Trúc Audio 5 Track Chuẩn Studio:
- **`V1`**: Video Clips (đã Fast-Cut In/Out quanh Climax).
- **`A1`**: Âm thanh gốc của clip.
- **`A2`**: **ĐỂ TRỐNG HOÀN TOÀN** (Dành riêng cho Voiceover - VO / Thu âm lời bình).
- **`A3`**: SFX Whoosh/Swoosh chuyển cảnh ngay tại các điểm cắt.
- **`A4`**: SFX Va chạm (Punch, Boom, Thud) ngay tại Action Peak Marker.
- **`A5`**: Background Music (BGM tự động ducking giảm âm lượng quanh cao trào).

### 📌 Thực Thi Premiere Pro MCP:
- Kiểm tra xem Premiere Pro có đang mở không qua MCP tool `verify_premiere_connection`.
- Nếu Premiere Pro đang kết nối: Thực thi tạo Sequence và đặt clip/SFX/BGM trực tiếp lên timeline Premiere!
- Luôn xuất file kế hoạch JSON `*_premiere_mcp_plan.json` để lưu trữ.

---

## 🔍 WORKFLOW 3: THẨM ĐỊNH THƯ MỤC FOOTAGE CÓ SẴN (`clip-inspector`)

Khi người dùng dán một thư mục chứa nhiều clip có sẵn:
```powershell
python skills/clip-inspector/scripts/inspect_clips.py "<folder_path>" -o "<output_folder>"
```
* Tự động quét 64-bit POPCNT pHash phát hiện clip trùng lặp hoặc lật gương.
* Tự động phát hiện viền mờ 9:16 / 1:1.
* Tự động sinh filmstrip 4 ô và chẩn đoán cấu trúc kịch tính vào `scenes_context.json`.
* Agent dùng `view_file` xem các ảnh filmstrip để báo cáo trực quan cho người dùng.

---

## 🛡️ WORKFLOW 4: CHE WATERMARK, LOGO & NỘI DUNG NHẠY CẢM (`content-shield` + `LocateAnything-3B`)

Khi người dùng bảo *"che logo"*, *"xóa watermark"*, *"làm mờ vết thương"*, *"content shield"*, *"quét lại toàn bộ source"*:
* **Quét VLM Định Vị & OCR Nội Cục (`LocateAnything-3B` Local ONNX INT4):** Chạy `python E:\.agents\skills\content-shield\scripts\locate_anything_engine.py --task scan-all-sources --kb <kb>` (100% offline trên `Python 3.14` + `onnxruntime` INT4 KV-Cache tại `E:\.cache\locateanything_onnx_int4`) để quét toàn bộ source (`HEAD / MID / 76% Post-Impact / TAIL`) trong vùng khung hình hiển thị thực tế và sinh bộ Contact Sheet đối chiếu (`CUR` Vàng vs `LA` Xanh lá).
* **Khử Triệt Để Che Thừa (`False Positives`) & Che Sót (`False Negatives`):**
  - Loại bỏ ngay các `Mask2` che nhầm đồ vật trong nhà (như quạt hộp trên nóc tủ sát biên `AECrop`) hoặc đè lên bầu trời/tường trống do dùng nhầm template góc đối diện.
  - Bắt trọn các logo đặt lệch góc (ví dụ logo `LA` nằm ở góc trái trên thay vì góc phải trên), mở rộng `Mask2` ôm trọn các dòng chữ dài ở đáy (`Funny Animals Pets`), và thu gọn các hộp blur chữ cười (`HAHAHAHA`, `HOHOHO!!!`) sát biên chữ thật của `LocateAnything-3B` để không lem vào chân/mặt nhân vật.
* Tự động bám theo đối tượng (OpenCV KCF/CSRT Tracking) và hỗ trợ 2 chế độ thực thi:
  - Render trực tiếp không cần Premiere: dùng bộ lọc `delogo` (khử vết mờ nội suy biên không tì vết) hoặc `boxblur`.
  - Premiere Pro MCP / `.prproj`: Tự động gắn `Gaussian Blur` + `Mask2` chống ăn mòn biên trên `Track V3` hoặc Adjustment Layer trên `Track V2`.

---

## 🔬 WORKFLOW 5: CLOSED-LOOP HARNESS AUDIT & REPAIR (`video-quality-control`)

Sau khi dựng sequence hoặc khi người dùng yêu cầu: *"kiểm tra timeline"*, *"audit timeline"*, *"chạy harness"*, *"sửa lỗi sequence"*:

### 📌 5 Bất Biến Bắt Buộc (The 5 Timeline Invariants):
1. **`INV-01` (Zero Gap on V1):** `len(get_timeline_gaps('V1')) == 0` $\to$ Tự động `ripple_delete` sạch các khe hở frame đen.
2. **`INV-02` (Frame-Exact SFX Sync):** $|\text{Frame}_{\text{SFX}} - \text{Frame}_{\text{Climax}}| \le 1$ frame $\to$ Tự động `move_clip` trên A4 dời đúng frame va chạm.
3. **`INV-03` (Audio Headroom):** $\text{True Peak} \le -1.0\text{ dBFS}$ $\to$ Tự động `adjust_audio_levels` hạ gain chống vỡ tiếng.
4. **`INV-04` (Voiceover Track A2 Integrity):** `len(get_clips('A2')) == 0` $\to$ Track A2 phải 100% để trống cho thu âm VO. Dời mọi clip đi lạc sang A3/A4.
5. **`INV-05` (Payoff Window Preservation):** $\text{Frame}_{\text{Out}} \ge \text{Climax} + 0.8\text{s} \times \text{FPS}$ $\to$ Tự động `trim_clip` nới đuôi clip đảm bảo khán giả kịp phản ứng.

### 📌 Vòng Lặp Tự Khắc Phục (Self-Healing Loop) & Circuit Breaker:
* Tự động sinh `state/patch-plan.json` và gọi Premiere Pro MCP thực thi sửa đổi trong 1 batch duy nhất.
* **Bộ ngắt mạch an toàn (Max 3 chu kỳ):** Nếu sau 3 chu kỳ sửa mà vẫn vi phạm $\to$ Tự động gọi soft rollback về Checkpoint an toàn, cắm Marker cảnh báo màu đỏ (`[QA_FAIL]`), chụp ảnh frame qua `capture_frame` và gửi vào chat xin chỉ thị người dùng.

---

## 🏆 WORKFLOW 6: DỰNG TẬP KÊNH ITV 10-TRACK, INTRO ELEVENLABS V3 & HẬU KIỂM `premiere-cli` (`visioncut`)

Khi làm việc với các project kênh **ITV Moments** (`E:\ITV\Project\kb*`, cấu hình chuẩn tại `skills/visioncut/resources/channel_profiles.json` & `skills/visioncut/references/ITV_AGENTS.md`):
1. **Quy Tắc Tuyển Chọn Nội Dung, Băm Source & Xếp Clip Toàn Tập (Tổng Thời Lượng `15 Phút` / `~900s`):**
   - **Tổng thời lượng video `15 phút` (`~900s`):** Tăng tổng thời lượng mỗi tập video thành phẩm lên **`15 phút` (`~900s`)**.
   - **Không cắt hụt nội dung cảnh (`Full Scene Preservation`):** Giữ trọn vẹn 100% diễn biến tự nhiên của từng cảnh (từ mở đầu `Setup`, diễn biến `Climax` đến hết phản ứng `Aftermath/Reaction`). Tuyệt đối không bóp ngắn hay cắt cụt nội dung cảnh để ép thời lượng; chỉ cắt sạch đúng ranh giới chuyển cảnh (boundary bleed).
   - **Ưu tiên cảnh tỉ lệ `16:9`:** Ưu tiên tuyển chọn và sử dụng các cảnh khung ngang `16:9` chuẩn, hạn chế cảnh dọc/vuông có viền mờ.
   - **Không dùng cảnh kém chất lượng, không nhìn rõ:** Loại bỏ cảnh mờ nhòe, vỡ hạt, thiếu sáng hoặc chủ thể quá nhỏ/bị che khuất không rõ hành động.
   - **Không dùng cảnh không có âm thanh, âm thanh `> 20dB` (`0` clip câm):** Tuyệt đối loại bỏ toàn bộ cảnh câm (không dựng khối Silent Montage đè BGM ở cuối video); chỉ dùng cảnh có âm thanh hiện trường rõ ràng (`diem_tieng > 20` / âm lượng `> 20dB`, `peak_db > -20 dB`).
   - **Không trùng lặp các cảnh trong cùng một video:** Kiểm tra đa tầng (Source Interval + Multi-anchor Active-Core pHash/dHash/Patch L1 + Flip-Invariant + AI Vision) đảm bảo `0` cảnh trùng lặp trong cùng 1 tập.
   - **Không dùng lại những cảnh đã dùng trong kịch bản kế tiếp (`No Scene Reuse Across Subsequent Scripts`):** Mọi cảnh đã sử dụng ở kịch bản/tập trước tuyệt đối không được dùng lại trong kịch bản kế tiếp; bắt buộc đối chiếu chéo với lịch sử các cảnh đã dùng (Source Interval + Multi-anchor Active-Core pHash/dHash/Patch L1 + Flip-Invariant) để loại bỏ hoàn toàn cảnh trùng giữa các tập.
   - **Đồng bộ dồn vào 1 folder chung với tiền tố `itv`:** Khi băm source và dựng **không chia 2 đoạn / 2 thư mục** (`itv.kbx_x` và `x`); đồng bộ dồn toàn bộ clip vào **1 folder chung duy nhất** với **tiền tố `itv`** thống nhất (`itv.kbx_1.mp4`, `itv.kbx_2.mp4`, ...) và dọn sạch file dư thừa.
   - **Loại bỏ những cảnh tác động mạnh động vật và trẻ em:** Tuyệt đối loại bỏ mọi cảnh va đập mạnh, ngã đau nguy hiểm hoặc tác động vật lý mạnh lên **động vật** và **trẻ em**.
   - **Quy tắc chọn Intro Hook (`Top-40 to 11 Intro Hook Selection Rule`):** Trong mỗi tập, chọn ra **`40 cảnh hay nhất`** (khung `16:9` nét, cao trào mạnh, âm thanh sống động), sau đó sàng lọc bằng mắt AI ra đúng **`11 cảnh xuất sắc nhất`** để làm **Intro Hook** ở đầu video (cắt `InPoint..OutPoint` đúng đỉnh Climax của từng cảnh).
2. **Không Che Watermark/Logo, Không Crop, Không Emoji & Không SFX (`Clean Native Visual & Audio Rule`):**
   - **Không che watermark / logo & Không crop:** Không chạy `Gaussian Blur` + `Mask2` che watermark/logo/chữ, không cắt `AECrop` viền mờ hai bên và không phóng `Scale` Zoom-crop đẩy logo (như ViralHog); giữ nguyên khung hình chuẩn `fit_scale` vừa khít `1920x1080`.
   - **Không dùng Emoji (`Track V4` trống `0` clip):** Không gắn Animated Emoji / GIF che va chạm hay reaction trên `Track V4`.
   - **Không dùng SFX (`Track A3`/`A4` trống `0` clip):** Không chèn hiệu ứng âm thanh SFX chuyển cảnh hay va chạm trên `Track A3`/`A4`; giữ nguyên âm thanh gốc hiện trường (`Track A1`) và Voiceover (`Track A2`).
3. **Tạo Intro Voiceover (`Track A2`) Qua `elevenlabs` CLI & Dựng Intro 10-Track (`FailSide` x `ITV`):**
   - Voice `ITV 5` (`ITLDKaHYPRfCyyrPpZu2`, model `eleven_v3`, `skills/visioncut/resources/itv_voice_config.json`), bọc cặp thẻ `[absurdist narration, accelerando, rushed, extreme fast] ... [accelerando, rushed, energetic, shouting] LET'S GET STARTED!!!`, kiểm tra phát âm bằng `view_file` và cắt rải nhịp linh hoạt (`2..6+` segments) theo vế câu Intro Text.
4. **Bảo Toàn Trọn Vẹn Nội Dung Cảnh & Hậu Kiểm Filmstrip (Cấm Cắt Cụt / Cấm Thừa Kế `InPoint` Ngoại Lai):**
   - Tuyệt đối không lấy `in_sec`/`duration_sec` từ `.pre_m3_bak.prproj` của tập donor khác áp sang clip mới, và **cấm bóp ngắn hay cắt hụt nội dung cảnh**.
   - Mọi clip không có mốc giây cứng bắt buộc soi storyboard qua `read_file` / `view_file`, khử sạch điểm nhảy cảnh từ nguồn compilation, lấy trọn vẹn diễn biến cảnh từ đầu tình huống đến hết phản ứng và hậu kiểm bằng filmstrip `[IN(Setup) | PRE-HIT | CLIMAX | OUT(React)]`.
5. **Đối Chiếu Trực Quan VO Comment Trước Khi Gắn (`Track A2` + `Track V5`):**
   - Mọi câu bình luận Body VO bắt buộc kiểm tra frame thực tế của đúng clip đích qua `read_file` / `view_file` để khớp 100% hành động trên hình và đặt theo `Premise` / `Aftermath` lệch khỏi đỉnh va chạm (`impact_sec`).
6. **Chuẩn Vệ Sinh Bắt Buộc Khi Sinh / Sửa Trực Tiếp `.prproj` XML:**
   - **0 rò rỉ dữ liệu tập cũ:** Đồng bộ `<ClipName>` trên cả `Media`, `MediaSource`, `Clip` và `ClipLoggingInfo` để xóa sạch tên tập donor (`kb121`, `kb122`, `kb55`, `script-81`, `script-82`), xóa toàn bộ `<PeakFilePath>` / `<ConformedAudioPath>` `.pek` ngoại lai để Premiere vẽ đúng waveform thật, relink `.aegraphic` + transition media về thư mục tập hiện tại, và đặt `MZ.PrefixKey.OpenSequenceGuidList.1` đúng `ObjectUID` của sequence đích.
   - **Gọn Bin & Đồng bộ Stream theo `ffprobe`:** Gộp 1 `MasterClip` chuẩn cho mỗi đường dẫn media, gắn đủ `ClipProjectItem` vào đúng bin (`0` `MasterClip` mồ côi), đồng bộ `FrameRect` + `FrameRate` + `Duration` + `<ScaleToFramePolicy>1</ScaleToFramePolicy>` cho mọi clip khác `1920x1080`.
7. **Chống Cắt Hụt Mốc Giây Chẵn Google Sheet & Khử Chuyển Cảnh Từng Frame (`Single-Frame Boundary Guard`):**
   - Biên kịch ghi mốc `MM:SS - MM:SS` làm tròn giây chẵn nên cú ngã/phản ứng thực tế thường tràn sang `END + 0.1s .. +2.0s`. Khi cắt hoặc sửa clip từ `_raw_cache/src_*.mp4`, bắt buộc dò cửa sổ mở rộng quanh `[START .. END]` và soi dải single-frame qua `read_file`: đặt `IN` tại frame sắc nét đầu tiên sau hiệu ứng chuyển cảnh đầu, đặt `OUT` tại frame sắc nét cuối cùng sau khi ngã + phản ứng hoàn tất (dừng sát `1 frame` trước khi chuyển cảnh kế tiếp xuất hiện) để **không bao giờ cắt hụt nội dung cảnh**.
8. **Bảo Vệ Phiên Premiere Pro Đang Mở Live & Cấm Ghi Đè Vết Dựng Tay (`Live Premiere Session Guard`):**
   - Trước mọi thao tác trên `<kb>.prproj`, bắt buộc kiểm tra tiến trình `Adobe Premiere Pro.exe` và `st_mtime` (cấm chạy `rebuild` xóa mất chỉnh sửa tay của người dùng).
   - **Khi Premiere đang mở trực tiếp:** Nếu chuyển sang tập mới qua MCP, **bắt buộc gọi `save_project` cho tập đang mở trước khi gọi `open_project`** (tránh hộp thoại modal *"Save changes?"*). Với tập đang mở mà không dùng MCP reload, không ghi đè `.prproj`; chỉ hot-swap file `.mp4` tại đúng đường dẫn cũ với đúng `sample_rate` gốc để Premiere tự live-reload thời lượng mới, rồi báo timecode `HH:MM:SS:FF` để người dùng bấm `B` (Ripple Edit).
   - **Khi Premiere đã đóng:** Backup `.prproj` trước, sau đó chỉ patch phẫu thuật (`Media`/`Stream`/`MasterClip` + ripple-shift các item phía sau) trên đúng file Save mới nhất của người dùng.

---

## 🎯 WORKFLOW 7: DỰNG TẬP KÊNH BONK! FUNNY MOMENTS (`bonk_funny_moments` — `E:\Bonk funny moments\project tool\kb*`)

Khi làm việc với các project kênh **Bonk! Funny Moments** (chi tiết tại `skills/visioncut/references/BONK_AGENTS.md` & `skills/visioncut/resources/channel_profiles.json` $\to$ `channels.bonk_funny_moments`):
1. **Băm Toàn Bộ Cảnh Từ Các Bộ Video Dài Rồi Trộn Với Nhau (`Full-Source Scene Slicing & Multi-Source Mixing`):**
   - Băm (tách scene) toàn bộ các cảnh độc lập từ các bộ video nguồn dài, trộn xen kẽ (`interleave/mix`) các cảnh từ nhiều nguồn lại với nhau, đồng bộ dồn vào **1 folder chung duy nhất** với **tiền tố `bonk`** thống nhất (`source/bonk.kb<N>_1.mp4`, `bonk.kb<N>_2.mp4`, ... — không chia 2 thư mục `bonk.kbx_x` và `Bonk-script-xx`), dọn sạch mọi file `.mp4` dư thừa ngoài timeline.
2. **Thời Lượng `~15 Phút` (`~900s`) & Giữ Nguyên Cảnh Dài Trọn Vẹn Nội Dung (`Zero Truncation`):**
   - Thời lượng mục tiêu mỗi tập khoảng **`15 phút` (`870s – 930s`)**. Tuyệt đối cấm cắt gọt ngắn hay áp trần fast-cut (`~5.5s`) làm mất đầu/đuôi cảnh; giữ nguyên độ dài tự nhiên trọn vẹn của mỗi cảnh, chỉ cắt sạch đúng ranh giới chuyển cảnh (`boundary bleed`).
3. **Không Dùng Source Câm (`> 20dB`), Không Emoji, Không Note Overlay, Không SFX (`Zero-VO / Zero-SFX / Zero-Overlay`):**
   - Chỉ nhận cảnh có âm thanh hiện trường gốc rõ ràng (`diem_tieng > 20`, `peak_db > -20 dB`, `0` clip câm).
   - Để trống 100% các track `V5` (`0` Emoji, `0` Note Overlay), `A3` (`0` SFX), `A4` (`0` SFX); phần thân `A2` trống 100% (`0` Voiceover).
4. **Chọn `12 Source Nét & Hook Nhất` $\to$ Sàng Lọc `1 Source` Duplicate Đưa Lên Đầu Làm Hook $\to$ Tới Intro Chuẩn `kb32`:**
   - Tuyển chọn 12 cảnh sắc nét & cuốn hút nhất tập, lọc bằng mắt AI chừa lại **1 cảnh xuất sắc nhất** nhân bản (`duplicate`) đặt ở đầu video (`0.00s .. T_hook`, tách đôi tại `T_hook - 3.10s` để `Capture It.mp3` fade-in trên `A2` và hạ nhẹ `A1`), nối tiếp ngay bằng **Intro chuẩn `kb32`** (`8.mp4` `Scale=50%` + `RENDER.mp4` `Speed=400%` + `TV Static Sound Effect - Bzz.mp4`, ngắt Logo `V3`/`V4` trong suốt `4.83s` Intro).
5. **Kiến Trúc Track `V1` & `V2` Chuẩn Bonk + Không Trùng Lặp Nội Tập / Liên Tập + An Toàn Trẻ Em & Động Vật:**
   - **`Track V1`:** Bản sao `1:1` (`duplicate`) của `Track V2` (`Start/End/InPoint/OutPoint` khớp tuyệt đối), **để trống FX hoàn toàn** (`DefaultMotion=true`, `Scale=100`, `Position=0.5:0.5`, `Rotation=0`, `0` FX).
   - **`Track V2`:** Gắn `Crop nền mờ` (`AE.ADBE AECrop` nếu có viền mờ) + `Transform` (`AE.ADBE Geometry2`: `Scale = 120`, `Rotation = 3`) + `Horizontal Flip` (`AE.ADBE Horizontal Flip`).
   - **Không trùng lặp nội tập & liên tập (`Strict Cross-Episode Zero-Reuse Gate`):** `0` cảnh trùng trong cùng 1 video (trừ 1 cảnh Hook duplicate có chủ đích) và **tuyệt đối cấm dùng lại cảnh đã xuất hiện ở tập trước sang các kịch bản kế tiếp** (`kb33..kb40+`). Loại bỏ 100% cảnh tác động mạnh lên trẻ em và động vật.

---

## 🐾 WORKFLOW 8: DỰNG TẬP KÊNH ANIMAL WHOOPS (`animal_whoops` — `E:\Animal Whoops\aw*`)

Khi làm việc với các project kênh **Animal Whoops** (chi tiết tại `skills/visioncut/references/ANIMAL_WHOOPS_AGENTS.md` & `skills/visioncut/resources/channel_profiles.json` $\to$ `channels.animal_whoops`):
1. **Quy Tắc Tuyển Chọn Nội Dung & Băm Source (`Zero-Duplicate, Zero-Reuse, Single-Folder Prefix awx`):**
   - Loại bỏ cảnh mờ nhòe/kém chất lượng, loại bỏ cảnh câm (chỉ dùng cảnh có âm thanh gốc `> 20dB`), loại bỏ tuyệt đối cảnh tác động vật lý mạnh gây hại cho động vật.
   - Đảm bảo `0` cảnh trùng lặp trong cùng 1 video và **không dùng lại bất kỳ cảnh nào đã xuất hiện ở kịch bản trước sang kịch bản kế tiếp** (`aw1_1` $\to$ `aw4_4+`).
   - Đồng bộ toàn bộ clip vào **1 folder chung duy nhất** với **tiền tố `awx`** (`source/aw1_1.1_f307.mp4`, ... — không chia 2 thư mục).
2. **Kiến Trúc Timeline `V1`–`V5` & `A1` (`15-to-3 Hook` $\to$ `intro.mp4` $\to$ `Body Speed 106% Optical Flow`):**
   - **Hook + Intro:** Sàng lọc 15 source ứng viên hài hước nhất từ thân bài, chọn ra **3 source** xuất sắc nhất **duplicate** đưa lên đầu video làm Hook, nối tiếp bằng `"E:\Video Asset\Animal Whoops\intro.mp4"` (`6.006s`, `Scale=50%` trên `V3`, `PlaybackSpeed=1.1` trên `A1`), rồi tới toàn bộ phần thân bài.
   - **`Track V5` (Watermark `wtm.jpg`):** `Position=960:940`, `Scale=30`, `Opacity=10%`, `Blend Mode=Screen`.
   - **`Track V4` (Logo `Logo Animal Whoops.png`):** `Position=1820:100`, `Scale=12`.
   - **`Track V3` (Video Chính):** `Speed=106%` (`PlaybackSpeed=1.06`, `Optical Flow` `TimeInterpolationType=2`), `Crop` nền mờ 2 bên (nếu có), `Transform` (`Scale=120`, `Rotation=3`), `Horizontal Flip`, `Lumetri Color`.
   - **`Track V2` (Adjustment Layer):** Kéo dài suốt Hook và Thân bài, gắn `Lumetri Color` (`Exposure = -5.0`).
   - **`Track V1` (Video Nền OG):** Duplicate `1:1` từ `V3` (`Speed=106%` Optical Flow), **để trống FX hoàn toàn** (`DefaultMotion=true`, `0` FX).
   - **`Track A1` (Audio Gốc):** Đồng bộ `1:1` với `V3` (`PlaybackSpeed=1.06`, `MaintainAudioPitch=true`).

---

## 💡 CÁC CÂU LỆNH MẪU NGƯỜI DÙNG THƯỜNG DÙNG (USER PROMPT CHEAT SHEET)

| Mục tiêu của Người Dùng | Câu lệnh người dùng gõ vào chat | Hành động tự động của Agent |
| :--- | :--- | :--- |
| **Bóc tách video thành các clip sạch** | *"Tách scene cho tôi video này: E:\footage\dailycam.mp4"* | Chạy Workflow 1: Quét Candidate $\to$ Soi Contact Sheets bằng `view_file` $\to$ Cắt phần cứng $\to$ Hậu kiểm Filmstrip. |
| **Dựng video ngắn giữ chân (W-Curve)** | *"Ghép các clip trong thư mục output thành video 30s theo W-Curve"* | Chạy Workflow 2 (`--mode w-curve -t 30`): Chấm điểm Score $\to$ Đóng gói cụm $\to$ Dựng lên Premiere Pro (hoặc render NVENC). |
| **Dựng tuần tự giữ nguyên thứ tự** | *"Dựng các clip này lên timeline Premiere theo thứ tự gốc, cắt gọt đoạn thừa và lắp sfx"* | Chạy Workflow 2 (`--mode sequential`): Hard Fast-Cut In/Out $\to$ Phân bổ 5 track audio $\to$ Đẩy thẳng vào Premiere Pro. |
| **Thẩm định kho clip có sẵn** | *"Soi và thẩm định giúp tôi folder clip này: E:\clips"* | Chạy Workflow 3: Sinh Filmstrip 4 ô $\to$ AI Vision soi filmstrip $\to$ Báo cáo clip hoàn chỉnh vs clip bị cắt lửng. |
| **Che logo trên video** | *"Che logo kênh ở góc trên bên phải clip này"* | Chạy Workflow 4: Tracking vùng chọn $\to$ Delogo hoặc chèn Adjustment Layer Premiere Pro. |
| **Kiểm tra và tự sửa lỗi timeline** | *"Audit timeline Premiere và tự sửa các lỗi lệch sync hoặc hở đen"* | Chạy Workflow 5: Đọc timeline state $\to$ Chạy `HarnessEvaluator` $\to$ Sinh `patch-plan.json` $\to$ Thực thi tự sửa 1 batch. |
| **Dựng tập ITV 15 phút chuẩn 10-track** | *"Dựng tiếp kb133..kb140 ITV"* | Chạy Workflow 6: Lọc cảnh 16:9 có tiếng `>20dB` không trùng $\to$ 1 folder `itv` $\to$ Top-40 chọn 11 Hook $\to$ `0` Blur/Crop/Emoji/SFX. |
| **Dựng tập Bonk! Funny Moments 15 phút** | *"Băm source và dựng kb33..kb40 Bonk"* | Chạy Workflow 7: Băm & trộn cảnh dài `~15m` 1 folder `bonk` $\to$ Hook 12-chọn-1 + Intro `kb32` $\to$ `V1` OG trống FX + `V2` Crop/Scale120/Rot3/Flip. |
| **Dựng tập Animal Whoops** | *"Dựng batch aw1..aw4 Animal Whoops"* | Chạy Workflow 8: Lọc cảnh `>20dB` không trùng 1 folder `awx` $\to$ Hook 15-chọn-3 + `intro.mp4` $\to$ `V3` Speed 106% + `V2` Adj `-5` + `V1` OG. |
