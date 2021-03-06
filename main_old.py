import requests
from bs4 import BeautifulSoup
import os.path
import telegram
from time import sleep


# 완주군청 게시판 스크래핑
def scrap_board_wanju(
        board='/board/list.wanju?boardId=BBS_0000107&menuCd=DOM_000000102001001000&startPage=',
        title_scrap='완주군 공지사항',
        file_scrap='wanju_noti',
        domain='https://www.wanju.go.kr',
        mobile='/m'
):
    global bot_token
    global bot_channel

    init_latest_first = 12260  # 저장된 파일이 없어서 처음부터 실행할 때
    init_latest_empty = 12255  # 파일은 있으나 오류가 발생하여 중간에서부터 읽어올 때

    latest_file = 'latest_' + file_scrap
    if not os.path.exists(latest_file):
        latest_no = init_latest_first  # 가장 마지막까지 스크래핑 해 온 게시물 번호
        # print('The latest file does not exist. The file is created.')
        # print(f'latest_no = {latest_no}')
        with open(latest_file, 'w') as fp:
            fp.write(str(latest_no))
    else:
        # print('The latest file exists')
        with open(latest_file, 'r') as fp:
            try:
                latest_no = int(fp.readline().strip())
                # print('readline() was executed')
                # print(f'latest_no = {latest_no}')
            except ValueError:
                latest_no = init_latest_empty
                # print('Error detected in readline()')
                # print(f'latest_no = {latest_no}')

    recent_no = latest_no  # 최신 게시글 번호를 저장하기 위해 저장
    recent_break = False  # 이중반복문(while)을 빠져나오기 위한 체크 변수
    scrap_count = 0  # 스크래핑 해 온 게시글 수

    bot = telegram.Bot(bot_token)
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
            table = soup.find('table', {'class': 'list_normal'})
            tbody = table.find('tbody')  # 게시물만 있는 tr을 찾음
            trs = tbody.find_all('tr')  # 결과값 = ResultSet
        except Exception as ex:
            print('Error: ' + str(ex))
            exit(1)

        for post in trs:
            try:
                num = int(post.find('td', {'scope': 'row'}).text)
            except ValueError:
                # print('Not Number!\nCHECK HTML STRUCTURE')
                # print(post.find('td', {'scope': 'row'}).text)
                # 공지용으로 사용하는 상단고정용 게시물은 pass
                continue

            # 저장할 최신 게시글 번호로 세팅
            if latest_no < num:
                latest_no = num

            # 최신 게시글이 있는지 확인
            if num == recent_no:
                # print(f'latest={str(latest_no)}, num={str(num)}, recent={str(recent_no)}')
                print(f'{scrap_count}개의 게시글을 가져왔습니다.')
                with open(latest_file, 'w') as fp:
                    try:
                        fp.write(str(latest_no))
                    except Exception as ex:
                        print('Error: ' + str(ex))
                        exit(1)
                recent_break = True
                break

            title = post.find('a').text
            link_m = domain + mobile + post.find('a').attrs['href']
            tds = list(post.find_all('td'))
            author = tds[2].text
            date = tds[3].text

            message = title_scrap + '\n[' + str(num) + '] ' + title + '\n' + author + ' ' + date + '\n' + link_m
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


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

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

    url_wanju_noti = [
        '/board/list.wanju?boardId=BBS_0000107&menuCd=DOM_000000102001001000&startPage=',
        '완주군 고시공고',
        'wanju_noti'
    ]
    scrap_board_wanju(url_wanju_noti[0], url_wanju_noti[1], url_wanju_noti[2])
