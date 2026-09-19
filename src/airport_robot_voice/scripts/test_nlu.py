#!/usr/bin/env python3
"""
Test lõi NLU mà KHÔNG cần cài ROS, không cần micro.

Chạy bộ test tự động:   python3 scripts/test_nlu.py
Chat thử tay:           python3 scripts/test_nlu.py -i
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from airport_robot_voice.nlu import NluEngine   # noqa: E402

CFG = os.path.join(os.path.dirname(HERE), 'config')
engine = NluEngine(os.path.join(CFG, 'intents.json'),
                   os.path.join(CFG, 'places.json'))

TESTS = [
    # --- greeting / thanks / goodbye / capability ---
    ('xin chào robot', 'greeting'),
    ('chào bạn', 'greeting'),
    ('ê robot', 'greeting'),
    ('cảm ơn bạn nhiều', 'thanks'),
    ('cám ơn nhé', 'thanks'),
    ('tạm biệt robot', 'goodbye'),
    ('thôi tôi đi đây', 'goodbye'),
    ('bạn giúp được gì cho tôi', 'capability'),
    ('robot biết làm những gì vậy', 'capability'),

    # --- toilet (nhiều cách nói) ---
    ('cho tôi hỏi nhà vệ sinh ở đâu ạ', 'ask_toilet'),
    ('toilet chỗ nào', 'ask_toilet'),
    ('wc ở đâu vậy bạn', 'ask_toilet'),
    ('tôi muốn đi vệ sinh quá', 'ask_toilet'),
    ('nha ve sinh o dau', 'ask_toilet'),          # không dấu, giống STT nghe thiếu dấu
    ('phòng vệ sinh gần đây nhất ở chỗ nào', 'ask_toilet'),

    # --- checkin ---
    ('quầy check in ở đâu vậy', 'ask_checkin'),
    ('tôi làm thủ tục lên máy bay ở đâu', 'ask_checkin'),
    ('quay lam thu tuc o dau', 'ask_checkin'),
    ('chỗ nộp hành lý ký gửi ở đâu ạ', 'ask_checkin'),

    # --- gate ---
    ('em ơi cổng b2 ở đâu', 'ask_gate_location'),
    ('cong b 2 o dau', 'ask_gate_location'),
    ('cổng ra máy bay của tôi ở đâu', 'ask_gate_location'),
    ('cổng số 15 ở đâu ạ', 'ask_gate_location'),
    ('gate a1 ở chỗ nào', 'ask_gate_location'),
    ('tôi lên máy bay ở cổng nào đây', 'ask_gate_location'),

    # --- food ---
    ('tôi đói quá', 'ask_food'),
    ('có quán cà phê nào gần đây không', 'ask_food'),
    ('chỗ nào bán đồ ăn nhanh không bạn', 'ask_food'),
    ('tôi khát nước quá à', 'ask_food'),

    # --- baggage ---
    ('lấy hành lý ở đâu', 'ask_baggage'),
    ('băng chuyền hành lý chỗ nào', 'ask_baggage'),
    ('vali của tôi ở đâu rồi', 'ask_baggage'),

    # --- info desk / atm / security ---
    ('quầy thông tin ở đâu vậy bạn', 'ask_info_desk'),
    ('tôi cần gặp nhân viên sân bay', 'ask_info_desk'),
    ('cây atm ở đâu', 'ask_atm'),
    ('tôi cần đổi tiền đô la', 'ask_atm'),
    ('cửa an ninh ở đâu ạ', 'ask_security'),
    ('kiểm tra an ninh ở chỗ nào', 'ask_security'),

    # --- guide_me (phải thắng ask_* dù chứa từ địa điểm) ---
    ('dẫn tôi đến nhà vệ sinh', 'guide_me'),
    ('đưa tôi tới quầy check in được không', 'guide_me'),
    ('bạn dẫn tôi đi cổng b2 nhé', 'guide_me'),
    ('chỉ đường cho tôi tới khu ăn uống', 'guide_me'),
    ('robot dẫn tôi đến đó nhé', 'guide_me'),

    # --- stop / go_home ---
    ('dừng lại', 'stop_robot'),
    ('đứng lại đi', 'stop_robot'),
    ('khoan đã bạn ơi', 'stop_robot'),
    ('quay về trạm sạc đi', 'go_home'),

    # --- flight status ---
    ('chuyến bay VN216 thế nào', 'ask_flight_status'),
    ('chuyến bay của tôi có bị trễ không', 'ask_flight_status'),
    ('cho tôi tra cứu chuyến bay VJ130', 'ask_flight_status'),

    # --- time / wifi ---
    ('bây giờ là mấy giờ rồi', 'ask_time'),
    ('wifi sân bay tên gì', 'ask_wifi'),
    ('mật khẩu wifi là gì vậy', 'ask_wifi'),
    ('lấy hành lý ở đâu', 'ask_baggage'),

    # --- câu ngoài phạm vi -> phải trả unknown ---
    ('abcxyz lảm nhảm gì đó', 'unknown'),
    ('hôm nay thời tiết thế nào', 'unknown'),
    ('bạn có người yêu chưa', 'unknown'),
]

def run():
    ok = 0
    for text, expect in TESTS:
        r = engine.process(text)
        good = r['intent'] == expect
        ok += good
        mark = 'OK ' if good else 'SAI'
        print(f'[{mark}] "{text}"\n      -> {r["intent"]} ({r["score"]:.0f}) '
              f'slots={r["slots"]} action={r["action"]}\n      "{r["text"]}"\n')
    print(f'=== Kết quả: {ok}/{len(TESTS)} ===')

def interactive():
    print('Gõ câu hỏi (Ctrl+C để thoát):')
    while True:
        try:
            t = input('> ')
        except (EOFError, KeyboardInterrupt):
            break
        r = engine.process(t)
        if r:
            print(f'  [{r["intent"]} {r["score"]:.0f} {r["slots"]}]')
            print(f'  ROBOT: {r["text"]}\n')

if __name__ == '__main__':
    interactive() if '-i' in sys.argv else run()
