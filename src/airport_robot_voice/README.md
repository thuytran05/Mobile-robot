# airport_robot_voice

Trợ lý giọng nói cho mobile robot sân bay chạy ROS 2 — **không dùng LLM**, chạy offline hoàn toàn.

```
Micro ──► stt_node ──/voice/text──► intent_node ──/voice/say──► tts_node ──► Loa
        (Vosk STT)                (rule + fuzzy)  │
                                                  └──/voice/intent──► nav_command_node ──► Nav2
```

## 1. Cài đặt

### 1.1 Thư viện Python

```bash
sudo apt update
sudo apt install -y python3-pip portaudio19-dev alsa-utils espeak-ng ffmpeg
pip3 install vosk sounddevice
```

> Phần hiểu ý định (NLU) không cần cài thêm thư viện gì — tự viết thuần Python,
> chạy giống hệt nhau trên mọi máy (xem mục 8 bên dưới về lý do).

### 1.2 Model nhận dạng giọng nói (Vosk, tiếng Việt, ~50 MB)

```bash
sudo mkdir -p /opt/vosk && cd /opt/vosk
sudo wget https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip
sudo unzip vosk-model-small-vn-0.4.zip
```

Danh sách model: https://alphacephei.com/vosk/models

### 1.3 Giọng nói TTS (Piper, tiếng Việt, ~60 MB)

```bash
pip3 install piper-tts
sudo mkdir -p /opt/piper && cd /opt/piper
# Tải giọng vi_VN từ: https://huggingface.co/rhasspy/piper-voices/tree/main/vi/vi_VN
sudo wget <link file .onnx>
sudo wget <link file .onnx.json>
```

Không có internet để tải Piper? Dùng tạm `engine:=espeak` (giọng máy nhưng chạy ngay).

### 1.4 Build package

```bash
cd ~/ros2_ws/src
cp -r /đường/dẫn/airport_robot_voice .
cd ~/ros2_ws
colcon build --packages-select airport_robot_voice --symlink-install
source install/setup.bash
```

## 2. Chạy

**Test lõi NLU trước, không cần ROS, không cần micro:**

```bash
cd airport_robot_voice
python3 scripts/test_nlu.py       # chạy bộ test tự động
python3 scripts/test_nlu.py -i    # chat thử bằng bàn phím
```

**Chạy toàn hệ thống:**

```bash
# Chế độ gõ phím (chưa có micro / đang debug)
ros2 launch airport_robot_voice voice_assistant.launch.py mode:=keyboard tts_engine:=espeak use_nav:=false

# Chế độ thật, có micro + Nav2
ros2 launch airport_robot_voice voice_assistant.launch.py mode:=mic tts_engine:=piper use_nav:=true
```

**Test thủ công từng topic:**

```bash
ros2 topic pub --once /voice/text std_msgs/String "{data: 'cổng B2 ở đâu'}"
ros2 topic echo /voice/say
ros2 topic echo /voice/intent
```

## 3. Cách hệ thống "hiểu" mà không cần LLM

Với câu `"em ơi cho hỏi cổng bê hai ở đâu ạ"`:

1. **Chuẩn hoá** → `em oi cho hoi cong be hai o dau a` (bỏ dấu, bỏ ký tự thừa).
   Bỏ dấu rất quan trọng vì STT hay nhận sai thanh điệu.
2. **Trích slot** bằng regex: chuyển chữ số sang số (`be hai` → `b 2`), bắt được `gate = B2`,
   suy ra `place_key = gate_b2`.
3. **So khớp mờ** câu đã chuẩn hoá với từng câu ví dụ trong `intents.json`,
   lấy điểm cao nhất. Từ khoá "chốt hạ" (`boost_keywords`) được cộng thêm 30 điểm.
   Trong nhóm vượt ngưỡng, intent có `priority` cao hơn (lệnh dẫn đường, dừng) thắng
   intent hỏi thông tin — nhờ vậy "dẫn tôi đến nhà vệ sinh" ra `guide_me` chứ không phải `ask_toilet`.
4. **Sinh câu trả lời**: lấy template của intent, thay `{gate}`, `{place_desc}`… bằng dữ liệu
   trong `places.json`. Nếu điểm < ngưỡng → câu fallback.

Toàn bộ mất **dưới 5 ms**, không cần GPU.

## 4. Tuỳ biến

### Thêm câu hỏi mới → chỉ sửa `config/intents.json`, KHÔNG sửa code

```json
{
  "name": "ask_smoking_area",
  "examples": ["khu hút thuốc ở đâu", "chỗ nào hút thuốc được", "phòng hút thuốc"],
  "boost_keywords": ["hút thuốc"],
  "responses": ["Khu vực hút thuốc ở {place_desc}."],
  "place": "smoking",
  "action": null
}
```

Rồi thêm `"smoking"` vào `places` trong `places.json`.

### Lấy toạ độ cho `places.json`

1. Chạy Nav2 + RViz với bản đồ của bạn.
2. Dùng teleop đẩy robot tới đúng vị trí cần lưu.
3. `ros2 topic echo /amcl_pose --once` → lấy `position.x`, `position.y`.
4. Đổi quaternion sang yaw: `yaw = 2 * atan2(z, w)`.

### Chỉnh độ "khó tính"

`"threshold": 62` trong `intents.json`. Tăng lên (70–75) nếu robot hay hiểu nhầm;
giảm xuống (55) nếu robot hay nói "tôi chưa hiểu".

### Wake word

Đặt `wake_word` trong launch (ví dụ `'ro bot'`) để robot chỉ phản hồi khi được gọi tên —
rất hữu ích ở sân bay ồn ào.

## 5. Xử lý sự cố

| Triệu chứng | Nguyên nhân / cách sửa |
|---|---|
| STT không ra chữ nào | Sai micro. Chạy `python3 -c "import sounddevice; print(sounddevice.query_devices())"` rồi set tham số `device` |
| Robot tự nghe chính mình | Đảm bảo `tts_node` publish `/voice/speaking` và `stt_node` subscribe được (cùng namespace) |
| Nhận dạng sai nhiều | Model small → đổi sang model lớn hơn; dùng micro mảng (ReSpeaker 4-Mic) thay micro laptop |
| Robot hiểu nhầm intent | Thêm câu ví dụ thật vào `examples`, hoặc thêm `boost_keywords` |
| Không có tiếng ra loa | Thử đổi `player` sang `paplay` hoặc `ffplay`; kiểm tra `aplay -l` |
| Nav2 không nhận goal | Kiểm tra `frame_id` đúng là `map` và AMCL đã định vị xong |

## 6. Phần cứng gợi ý

- **Máy tính**: Jetson Orin Nano / Raspberry Pi 5 / mini PC — Vosk small chạy realtime trên CPU.
- **Micro**: ReSpeaker Mic Array v2.0 hoặc 4-Mic (có khử ồn, beamforming) — yếu tố quan trọng
  nhất quyết định độ chính xác ở môi trường ồn như sân bay.
- **Loa**: loa USB nhỏ 5–10 W.

## 7.5 Vì sao từng bị 4/14 và đã sửa thế nào

Nếu bạn từng thấy độ chính xác rất thấp khi tự chạy `test_nlu.py`, nguyên nhân
**không nằm ở dữ liệu** trong `intents.json` mà ở 3 lỗi trong code `nlu.py`:

1. **Phụ thuộc thư viện tuỳ chọn (rapidfuzz)**: bản đầu tiên thử dùng
   `rapidfuzz` nếu cài được, không thì lùi về `difflib`. Hai thư viện này
   chấm điểm rất khác nhau, nên cùng một ngưỡng (`threshold`) mà máy có
   mạng (cài được rapidfuzz) và máy không mạng (chỉ có difflib) ra kết quả
   khác hẳn nhau. **Đã sửa**: bỏ hẳn rapidfuzz, viết thuật toán chấm điểm
   từ khoá có trọng số (TF-IDF thu nhỏ) hoàn toàn bằng Python chuẩn — chạy
   giống hệt nhau trên mọi máy, không phụ thuộc việc cài đặt.

2. **Lỗi logic ưu tiên (priority)**: intent "ra lệnh" (dẫn đường, dừng...)
   được ưu tiên hơn intent "hỏi thông tin" khi hai bên cùng khớp — nhưng
   bản đầu so sánh priority TRƯỚC điểm số một cách vô điều kiện, nên một
   intent ra lệnh chỉ tình cờ trùng 1 từ (điểm rất thấp) vẫn thắng một
   intent hỏi thông tin khớp gần như hoàn hảo. **Đã sửa**: priority giờ chỉ
   phá thế hoà giữa các intent có điểm SÍT SAO với intent tốt nhất (chênh
   lệch dưới `priority_margin`, mặc định 15 điểm) — không còn ghi đè vô tội vạ.

3. **Xoá dấu tiếng Việt quá tay**: bản đầu xoá luôn cả dấu tạo nguyên âm
   gốc (ô, ơ, ê, ư, ă — đây là CHỮ CÁI riêng của tiếng Việt, không phải dấu
   phụ), khiến các từ khác nghĩa hoàn toàn bị gộp làm một, ví dụ "đói"
   (hungry) và "đổi" (exchange) đều thành "doi". **Đã sửa**: chỉ xoá dấu
   THANH ĐIỆU (sắc, huyền, hỏi, ngã, nặng) khi câu có dấu đầy đủ; nếu câu
   hoàn toàn không dấu (gõ tay hoặc STT mất dấu) mới chuyển sang so khớp bỏ
   dấu toàn bộ. Xem chi tiết trong docstring đầu file `nlu.py`.

Sau khi sửa cả 3, bộ test đã mở rộng lên 57 câu (đa dạng cách nói, có câu
không dấu, có câu ngoài phạm vi) và đạt 57/57 — chạy `python3
scripts/test_nlu.py` để tự kiểm chứng trên máy bạn.

## 7.6 Cách tự debug nếu vẫn gặp câu bị hiểu sai

```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from airport_robot_voice.nlu import NluEngine
e = NluEngine('config/intents.json','config/places.json')
it, s = e.match_intent('câu bạn muốn kiểm tra')
print(it['name'] if it else None, s)
"
```

Nếu điểm quá thấp: thêm câu ví dụ gần giống vào `examples` của intent đúng.
Nếu bị nhận nhầm sang intent khác: thêm `boost_keywords` đặc trưng hơn cho
intent đúng, hoặc kiểm tra xem 2 intent có đang share một từ không đặc
trưng (như "thôi", "robot") — nếu có, sửa lại ví dụ để bớt từ đó.

## 7. Nếu sau này muốn nâng cấp

Kiến trúc này giữ nguyên, chỉ thay từng khối:
- STT: Vosk → `faster-whisper` (model `small`, chính xác hơn, vẫn chạy offline).
- NLU: rule-based → phân loại intent bằng embedding (sentence-transformers) hoặc LLM nhỏ,
  chỉ cần đổi hàm `match_intent()` trong `nlu.py`.
