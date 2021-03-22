import requests
from bs4 import BeautifulSoup
import os.path
import telegram
from time import sleep
import datetime
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
    global bot_channel
    global bot

    # 저장된 파일이 없어서 처음부터 실행할 때, 파일은 있으나 오류가 발생하여 중간에서부터 읽어올 때
    # 이중반복문(while-페이지 넘어가서 계속 스크래핑 수행)을 빠져나오기 위한 체크 변수
    recent_break = False

    # 최근 게시물 번호를 file-based 에서 heroku config vars 로 변경
    config_vars_latest = 'LATEST_' + file_scrap.upper()
    latest_file = 'latest_' + file_scrap

    try:
        latest_no = int(os.environ.get(config_vars_latest))
    except KeyError:
        latest_no = 0
        recent_break = True
        print(f'Setting config var - {config_vars_latest}')
        os.system(f'heroku config:set {config_vars_latest}=0')
    except ValueError:
        latest_no = 0
        recent_break = True
        print(f'ValueError on config var - {config_vars_latest}')

    recent_no = latest_no  # 최신 게시글 번호를 저장하기 위해 저장
    scrap_count = 0  # 스크래핑 해 온 게시글 수

    bot_msg_limit = 20  # 20 msgs per minute to the same group
    bot_msg_limit_sleep = 60
    bot_msg_count = 0

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
            if num == recent_no:
                # print(f'latest={str(latest_no)}, num={str(num)}, recent={str(recent_no)}')
                print(f'{title_scrap} / {scrap_count}개의 게시글을 가져왔습니다.')
                # file-based 에서 환경변수 config var로 변경
                os.environ[config_vars_latest] = latest_no
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

            bot.sendMessage(bot_channel, message, parse_mode='Markdown', disable_web_page_preview=True)
            bot_msg_count += 1
            scrap_count += 1

            if (bot_msg_count % bot_msg_limit) == 0:
                print('bot will not be able to send more than 20 messages per minute to the same group.')
                print('waiting a minute.')
                sleep(bot_msg_limit_sleep)

        # 반복문이 다 끝나더라도 최신 게시글이 안 나왔으면
        # => 페이지를 넘겨가서 나올 때까지 해야 함
        if recent_break:
            break  # 이중반복문 빠져나와서 프로그램 종료하기
        else:
            page_num += 1  # 다음페이지의 게시글을 스크래핑 해 오기 위해 페이지번호 설정

@sched.scheduled_job('interval', minutes=1)
def timed_job():
    global bot

    # print("Testing interval scheduled job")

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

    # 현재시간 구하기
    now = datetime.datetime.now()
    nowDatetime = now.strftime('%Y-%m-%d %H:%M:%S')
    message = f'수행중 {nowDatetime}'
    bot.sendMessage(bot_channel, message)
    print(message)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    # telegram token, channel check
    with open('token.txt', 'r') as fp:
        try:
            lines = fp.readlines()
        except FileNotFoundError:
            print('\'token.txt\' file not found.')
            exit(1)
        try:
            bot_token = lines[0].strip()
            bot_channel = lines[1].strip()
        except IndexError:
            print('Check file. \'token.txt\'')
            exit(1)

        if bot_token == '' or bot_channel == '':
            print('Check token or channel information.')
            exit(1)

    bot = telegram.Bot(bot_token)

    sched.start()
