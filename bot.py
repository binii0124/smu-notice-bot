import requests
from bs4 import BeautifulSoup
import os

# --- 설정 구간 ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK") # GitHub Secrets에서 가져옴
NOTICE_URL = "https://www.smu.ac.kr/kor/life/notice.do"
DB_FILE = "last_id.txt"
# ----------------

def get_latest_notice():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(NOTICE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 공지사항 아이템(li)들을 모두 찾습니다.
        # 캡처본에 나온 구조: li > dl > dd > ul > li.board-thumb-content-number
        items = soup.select("ul li") # 혹은 더 정확하게 "div.board-thumb-list ul li" 등으로 잡을 수 있습니다.
        
        for item in items:
            # 2. 번호가 들어있는 요소를 찾습니다.
            num_el = item.select_one(".board-thumb-content-number")
            
            if num_el:
                # "No. 764404" 형태에서 숫자만 추출
                raw_text = num_el.get_text(strip=True) # "No.764404"
                notice_id = raw_text.replace("No.", "").strip()
                
                # 숫자인지 확인 (공지 태그 등을 거르기 위함)
                if notice_id.isdigit():
                    # 3. 제목과 링크 추출
                    # dt.board-thumb-content-title 안에 있는 a 태그를 찾습니다.
                    title_el = item.select_one(".board-thumb-content-title a")
                    if title_el:
                        title = title_el.get_text(strip=True)
                        link_href = title_el['href']
                        
                        # 상대 경로 처리 (공지 상세페이지 이동을 위해)
                        if link_href.startswith('?'):
                            link = f"https://www.smu.ac.kr/kor/life/notice.do{link_href}"
                        elif link_href.startswith('.'):
                            link = f"https://www.smu.ac.kr/kor/life/notice.do{link_href[1:]}"
                        else:
                            link = link_href # 절대 경로일 경우
                            
                        return notice_id, title, link
                        
        return None, None, None
    except Exception as e:
        print(f"에러 발생: {e}")
        return None, None, None

def send_discord_message(title, link):
    payload = {
        "content": f"📢 **새로운 학교 공지가 올라왔습니다!**\n\n**제목:** {title}\n**바로가기:** {link}"
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

# 현재 서버에서 받아오는 HTML의 앞부분을 출력해서 구조를 확인해봅니다.
def debug_html():
    response = requests.get(NOTICE_URL)
    print(response.text[:1000]) # 처음 1000자만 출력

def main():
    # 1. 최신 공지 긁어오기
    latest_id, title, link = get_latest_notice()
    
    if not latest_id:
        print("공지를 찾을 수 없습니다.")
        return

    # 2. 이전에 확인한 ID와 비교
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            last_id = f.read().strip()
    else:
        last_id = ""

    # 3. 새로운 공지라면 알림 전송 및 ID 갱신
    if latest_id != last_id:
        print(f"새 공지 발견! ({latest_id}) 알림을 보냅니다.")
        send_discord_message(title, link)
        with open(DB_FILE, "w") as f:
            f.write(latest_id)
    else:
        print("새로운 공지가 없습니다.")

if __name__ == "__main__":
    main()