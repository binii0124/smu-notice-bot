import requests
from bs4 import BeautifulSoup
import os
import re
import time

# --- 설정 구간 ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
# 로컬 테스트 시에는 아래 줄 주석을 해제하고 실제 웹훅 URL을 넣으세요.
NOTICE_URL = "https://www.smu.ac.kr/kor/life/notice.do"
DB_FILE = "last_id.txt"
# ----------------

def get_notices():
    headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/"
    }
    
    notices = []
    try:
        # 타임아웃을 20초로 넉넉하게 잡습니다.
        response = requests.get(NOTICE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        items = soup.select("ul li")
        
        for item in items:
            num_el = item.select_one(".board-thumb-content-number")
            if not num_el: continue
            
            raw_id_text = num_el.get_text(strip=True).replace("No.", "").strip()
            if not raw_id_text.isdigit(): continue
            
            notice_id = int(raw_id_text)
            title_el = item.select_one(".board-thumb-content-title")
            
            if title_el:
                full_title = title_el.get_text(" ", strip=True)
                link_el = title_el.select_one("a")
                link = "https://www.smu.ac.kr/kor/life/notice.do" + link_el['href'] if link_el else ""

                notices.append({'id': notice_id, 'title': full_title, 'link': link})
        
        return notices
    except Exception as e:
        print(f"데이터 수집 중 에러 발생: {e}")
        return []

def send_discord_message(notice):
    full_title = notice['title']
    
    # 1. 정규식으로 말머리와 본 제목 분리
    # 예: "서울 [학생생활] [비교과_학생복지팀] 2026학년도..." 
    # -> prefix: "서울 [학생생활]", main_title: "[비교과_학생복지팀] 2026학년도..."
    match = re.match(r"^(\S+\s*\[.*?\])\s*(.*)", full_title)
    
    if match:
        prefix = match.group(1)
        main_title = match.group(2)
    else:
        prefix = "공지"
        main_title = full_title

    # 2. 말머리 키워드에 따른 색상 지정 (디스코드 색상은 10진수 사용)
    if "서울" in prefix:
        embed_color = 0x2b579a  # 상명대 파란색 느낌
    elif "천안" in prefix:
        embed_color = 0x8a1538  # 천안캠퍼스 진홍색/갈색 느낌
    elif "상명" in prefix:
        embed_color = 0xe85a71  # 핑크/빨간색 느낌
    else:
        embed_color = 0x808080  # 기본 회색

    # 3. Embed 형태로 페이로드 구성
    payload = {
        "embeds": [{
            "color": embed_color,
            "title": f"📢 **새로운 학교 공지가 올라왔습니다!**",
            "url": notice['link'],
            "fields": [
                {
                    "name": "카테고리",
                    "value": f"**{prefix}**",
                },
                {
                    "name": "제목",
                    "value": main_title,
                    "inline": False
                }
            ],
            "footer": {
                "text": "SMU Notice Bot"
            }
        }]
    }
    
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def main():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            content = f.read().strip()
            last_id = int(content) if content.isdigit() else 0
    else:
        last_id = 0

    current_notices = get_notices()
    
    # 저장된 ID보다 큰 모든 새 공지를 가져옵니다. (last_id 갱신용)
    new_notices = [n for n in current_notices if n['id'] > last_id]
    new_notices.sort(key=lambda x: x['id'])

    if new_notices:
        for n in new_notices:
            # 정규식을 사용해 말머리 부분만 추출
            import re
            match = re.match(r"^(\S+\s*\[.*?\])", n['title'])
            prefix = match.group(1) if match else ""

            # 추출된 말머리(prefix)에 '천안'이 있는지만 검사!
            if "천안" in prefix:
                print(f"필터링됨 (천안 말머리 패스): {n['title']}")
                continue 
            
            send_discord_message(n)
            time.sleep(0.5) # 디스코드 웹훅이 너무 빠르게 연속적으로 호출되는 것을 방지하기 위해 0.5초 딜레이를 추가합니다.
        
        # 마지막 ID 업데이트 (알림을 안 보낸 천안 공지라도 번호는 갱신해야 함!)
        max_id = new_notices[-1]['id']
        with open(DB_FILE, "w") as f:
            f.write(str(max_id))
        print(f"처리가 완료되었습니다. (마지막 ID: {max_id})")
    else:
        print("새로운 공지가 없습니다.")

if __name__ == "__main__":
    main()