import requests
from bs4 import BeautifulSoup
import os
import telegram
from time import sleep
import datetime
import dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

# logging.basicConfig()
sched = BlockingScheduler()

# 전주시청 게시판 스크래핑
def scrap_board(
        board='/list.9is?boardUid=9be517a74f8dee91014f90e8502d0602&page=',
        title_scrap='전주시 공지사항',
        file_scrap='jeonju_noti',
        table_class='tstyle MT10',
        domain='http://www.jeonju.go.kr/planweb/board',
        mobile=''
):
    global TELEGRAM_CHANNEL
    global bot
    global BOT_MSG_LIMIT, BOT_MSG_SLEEP, bot_msg_count

    # 이중반복문(while-페이지 넘어가서 계속 스크래핑 수행)을 빠져나오기 위한 체크 변수
    recent_break = False

    # 가장 최근 게시물 번호
    latest_no = 1

    # 최근 게시물 번호를 file-based 에서 heroku config vars 로 변경
    config_vars_latest = 'LATEST_' + file_scrap.upper()

    try:
        latest_no = int(os.environ.get(config_vars_latest))
        # print(f'latest_no={latest_no}')
    except KeyError:
        recent_break = True  # 처음 실행될 때는 1페이지만 읽어오고, 환경변수 세팅함
        # print(f'Setting config var - {config_vars_latest}')
        os.environ[config_vars_latest] = 0
        os.system('heroku config:set ' + config_vars_latest + '=0')
    except TypeError:
        recent_break = True
        # print(f'config_vars_latest={config_vars_latest}')
        # print('os.environ[' + config_vars_latest + ']=' + os.environ[config_vars_latest])

    # 가장 마지막에 가져온 (저장돼 있는) 최근 게시물 번호
    recent_no = latest_no  # 최신 게시글 번호를 저장하기 위해 저장
    scrap_count = 0  # 스크래핑 해 온 게시글 수

    # HTML 스크래핑 해오기
    page_num = 1  # get parameter 'startPage'
    while True:
        res = requests.get(domain + board + str(page_num))
        # print(domain + board + str(page_num))
        soup = BeautifulSoup(res.content, 'html.parser')
        try:
            table = soup.find('table', {'class': table_class})
            tbody = table.find('tbody')  # 게시물만 있는 tr을 찾음
            trs = tbody.find_all('tr')  # 결과값 = ResultSet
        except Exception as ex:
            print('.Error: ' + str(ex))
            exit(1)

        for post in trs:
            tds = post.find_all('td')
            try:
                num = int(tds[0].text.strip())
            except ValueError:
                print('Not Number!\nCHECK HTML STRUCTURE')
                # print(post.find('td', {'scope': 'row'}).text)
                # 공지용으로 사용하는 상단고정용 게시물은 pass
                continue

            # 저장할 최신 게시글 번호로 세팅
            if latest_no > 0 and latest_no < num:
                latest_no = num

            # 최신 게시글이 있는지 확인
            if (num == recent_no) or (recent_break == True):
                # print(f'latest={str(latest_no)}, num={str(num)}, recent={str(recent_no)}')
                print(f'{title_scrap} / {scrap_count}개의 게시글을 가져왔습니다.')
                if scrap_count > 0:
                    # file-based 에서 환경변수 config var 로 변경
                    os.environ[config_vars_latest] = str(latest_no)
                    dotenv.set_key(dotenv_file, config_vars_latest, os.environ[config_vars_latest])
                    os.system('heroku config:set ' + config_vars_latest + '=' + os.environ[config_vars_latest])
                recent_break = True
                break

            title = tds[1].find('a').text
            link_m = domain + mobile + tds[1].find('a').attrs['href'].lstrip('.')
            author = tds[2].text
            date = tds[3].text

            message = '*' + title_scrap + '*\n' + str(num) + '. ' + title + '\n_' + author + ' ' + date + '_\n[Click for More](' + link_m + ')'
            message.replace('&', '%26')  # & 문자를 UTF-8로 변경
            print(f'[{str(num)}]{date}/{title}({author})')
            # 시간(번호)순으로 할 때 역순으로 출력해야 하지만 주기적으로 실행하면 게시글을 많이 가져오지 않으므로 그냥 출력

            send_message(message)
            scrap_count += 1

        # 반복문이 다 끝나더라도 최신 게시글이 안 나왔으면
        # => 페이지를 넘겨가서 나올 때까지 해야 함
        if recent_break:
            break  # 이중반복문 빠져나와서 프로그램 종료하기
        else:
            page_num += 1  # 다음페이지의 게시글을 스크래핑 해 오기 위해 페이지번호 설정

def send_message(message):
    global bot_msg_count, BOT_MSG_SLEEP, BOT_MSG_LIMIT, TELEGRAM_CHANNEL, bot

    # print(f'BOT_MSG_LIMIT={BOT_MSG_LIMIT},BOT_MSG_SLEEP={BOT_MSG_SLEEP},bot_msg_count={bot_msg_count}')
    if (bot_msg_count >= BOT_MSG_LIMIT) and (bot_msg_count % BOT_MSG_LIMIT) == 0:
        print('bot will not be able to send more than 20 messages per minute to the same group.')
        print('waiting a minute.')
        sleep(BOT_MSG_SLEEP)
    bot_msg_count += 1
    bot.sendMessage(TELEGRAM_CHANNEL, message, parse_mode='Markdown', disable_web_page_preview=True)

@sched.scheduled_job('interval', minutes=60)
def timed_job():
    global bot
    global bot_msg_count

    # 전주시 새소식
    url_jeonju = [
        '/list.9is?boardUid=9be517a74f8dee91014f90e8502d0602&page=',
        '전주시 새소식',
        'jeonju_noti',
        'tstyle MT10',
        'http://www.jeonju.go.kr/planweb/board'
    ]
    scrap_board(url_jeonju[0], url_jeonju[1], url_jeonju[2], url_jeonju[3])

    # 전주시 유관기관 소식
    url_jeonju = [
        '/list.9is?boardUid=9be517a74f8dee91014f90f516c906f9&page=',
        '전주시 유관기관 소식',
        'jeonju_ref',
        'tstyle MT10',
        'http://www.jeonju.go.kr/planweb/board'
    ]
    scrap_board(url_jeonju[0], url_jeonju[1], url_jeonju[2], url_jeonju[3])

    # 현재시간 구해서 실행중인 메시지 보여주기
    now = datetime.datetime.now()
    nowDatetime = now.strftime('%Y-%m-%d %H:%M:%S')
    message = f'수행중 {nowDatetime}'

    print(message)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    dotenv_file = dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file, verbose=True)

    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL')

    bot = telegram.Bot(TELEGRAM_TOKEN)

    BOT_MSG_LIMIT = 20  # 20 msgs per minute to the same group
    BOT_MSG_SLEEP = 60
    bot_msg_count = 0

    sched.start()
