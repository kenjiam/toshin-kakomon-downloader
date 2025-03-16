import os
import re
import itertools
import requests
import toml
import csv
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
import argparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.toml")
UNIVERSITY_CODES = os.path.join(BASE_DIR, "university_codes.csv")

def get_config():
    def generate_config():
        print("メールアドレスとパスワードを入力\n")
        while True:
            username = input("メールアドレス: ")
            if not username:
                print("メールアドレスが空です。再度入力してください。")
                continue
            break
        while True:
            password = input("パスワード　　: ")
            if not password:
                print("PASSWORDが空です。再度入力してください。")
                continue
            break
        config_data = {
            "auth": {
                "username": username,
                "password": password
            },
            "path": {
                "dlpath": ""
            }
        }
        with open(CONFIG_FILE, "w") as f:
            toml.dump(config_data, f)
        print("認証情報を保存しました\n")
    if not os.path.exists(CONFIG_FILE):
        generate_config()

    config = toml.load(CONFIG_FILE)
    username = config["auth"]["username"]
    password = config["auth"]["password"]
    dlpath = config["path"]["dlpath"]
    return username, password, dlpath

USERNAME, PASSWORD, DLPATH = get_config()

def update():  # タスク：進行度の表示
    def generate_possible_urls():
        base_url = "https://www.toshin-kakomon.com/kakomon_db/ex/menu/"
        characters = '0123456789abcdefghijklmnopqrstuvwxyz'
        return {
            ''.join(combo): base_url + ''.join(combo) + ".html"
            for combo in itertools.product(characters, repeat=2)
        }
    
    def get_title(url):
        try:
            response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
            soup = BeautifulSoup(response.content, "html.parser")
            if response.status_code == 200:
                if soup.title:
                    title = soup.title.string
                    print(title)
                    return title
            return None  # 条件を満たさない場合はNoneを返す
        except requests.exceptions.RequestException:
            return None
    
    print("しばらくお待ちください．．．")
    url_dict = generate_possible_urls()
    
    # Noneでないタイトルのみを追加する
    university_list = {}
    for code, url in url_dict.items():
        title = get_title(url)
        if title is not None:
            university_list[code] = title

    with open(UNIVERSITY_CODES, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        for code, title in university_list.items():
            writer.writerow([code, title])
    
    print("\n更新が完了しました。")

def config(key=None, value=None):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = toml.load(f)

    if key is None and value is None:
        key_labels = {"email": "メールアドレス　", "password": "パスワード　　　", "dlpath": "ダウンロードパス"}
        for section, values in config.items():
            for k, v in values.items():
                label = key_labels.get(k, k)
                print(f"{label}: {v}")
        return

    if key in ["email", "password"]:
        section = "auth"
    elif key == "dlpath":
        section = "path"
    else:
        raise ValueError("Invalid key. Use 'email', 'password', or 'dlpath'.")

    # 現在の値を出力
    if value is None:
        key_labels = {"email": "メールアドレス", "password": "パスワード", "dlpath": "ダウンロードパス"}
        label = key_labels.get(key, key)
        print(f"{label}: {config[section].get(key, 'Not found')}")
        return

    # 新しい値を設定
    config[section][key] = value

    # TOMLファイルを更新
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        toml.dump(config, f)

def search(query):
    with open(UNIVERSITY_CODES, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        lines = list(reader)  # すべての行をリストとして取得

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []

    for row in lines:
        if len(row) > 1 and pattern.search(row[1]):  # タイトル部分を検索
            highlighted = pattern.sub(lambda m: f"\033[31m{m.group(0)}\033[0m", row[1].strip())
            results.append(highlighted)
    results.sort()
    return results

def download():
    def get_university_code(university):
        codes = {}
        with open(UNIVERSITY_CODES, "r", encoding="utf-8") as file:
            for line in file:
                code, name = line.strip().split(", ", 1)
                codes[name] = code
        code = codes.get(university)
        return code
    while True:
        university = input("大学名を入力: ").strip()
        code = get_university_code(university)
        if code:
            break
        else:
            print("\n\033[33m完全一致する大学名が見つかりませんでした。入力を修正してください。\033[0m")
            rows = []
            count = 1
            for univ in search(university):
                count += 1
                length = len(univ)  
                rows.append(length)
            max_length = (max(rows) - 9) * 2 if rows else 0
            print("-" * max_length)
            print("\n".join(univ for univ in search(university)))
            print("-" * max_length)

    index_url = f"https://www.toshin-kakomon.com/kakomon_db/ex/menu/{code}.html"
    response = requests.get(index_url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=5)
    soup = BeautifulSoup(response.content, 'html.parser')

    def get_kakomon_list(soup):
        def extract_number(link):
            match = re.search(r'../data/\d{4}/[^/]+/([^/]+)/[^/]+\.html', link)
            return match.group(1)[-2:] if match else None
        def extract_prefix(link):
            match = re.search(r'../data/\d{4}/[^/]+/([^/]+)/[^/]+\.html', link)
            return match.group(1)[0] if match else None
        def extract_year(link):
            match = re.search(r'../data/(\d{4})/[^/]+/[^/]+/[^/]+\.html', link)
            return match.group(1) if match else None

        data_list = []

        rows = soup.find_all('tr')
        for row in rows:
            faculty = row.find('td', class_='h2').text.strip() if row.find('td', class_='h2') else None
            links_and_subjects = row.find_all('a')

            if faculty and links_and_subjects:
                for link_subject in links_and_subjects:
                    method = row.find('td', class_='t1').text.strip() if row.find('td', class_='t1') else row.find('td', class_='t2')
                    subject = link_subject.text.strip()
                    link = link_subject.get('href', None)
                    if link:
                        next_sibling = link_subject.find_next_sibling('img')
                        number = extract_number(link)
                        prefix = extract_prefix(link)
                        year = extract_year(link)
                        answer = True if next_sibling and "../img/ka.gif" in next_sibling['src'] else False
                        if number:
                            data = {
                                'faculty': faculty,
                                'method': method,
                                'subject': subject,
                                'number': number,
                                'prefix': prefix,
                                'year': year,
                                'answer': answer
                            }
                            data_list.append(data)
        return data_list
    kakomon_list = get_kakomon_list(soup)

    def select_faculties(kakomon_list):
        faculty_list = sorted(set(item['faculty'] for item in kakomon_list))
        print("\n学部を選択（複数可、カンマ区切り）:")
        for i, faculty in enumerate(faculty_list, 1):
            print(f"{i}. {faculty}")
        faculty_choices = input("\n番号を入力: ").split(',')
        faculties = [faculty_list[int(i)-1] for i in faculty_choices]

        return faculties
    def select_methods(kakomon_list, faculties):
        methods = []
        for faculty in faculties:
            print(f"\n{faculty} の学科・方式を選択（複数可、カンマ区切り）:")
            available_methods = sorted(set(item['method'] for item in kakomon_list if item['faculty'] == faculty))
            for i, method in enumerate(available_methods, 1):
                print(f"{i}. {method}")
            method_choices = input("\n番号を入力: ").split(',')
            methods.extend([available_methods[int(i)-1] for i in method_choices])
        return methods
    faculties = select_faculties(kakomon_list)
    methods = select_methods(kakomon_list, faculties)

    def generate_download_list(kakomon_list, faculties, methods):
        download_list = []
        for item in kakomon_list:
            for faculty in faculties:
                for method in methods:
                    if item.get('faculty') == faculty and item.get('method') == method:
                        data = {
                            'faculty': item.get('faculty'), 
                            'method': item.get('method'),
                            'year': item.get('year'),
                            'prefix': item.get('prefix'),
                            'number': item.get('number'),
                            'subject': item.get('subject'),
                            'answer' : item.get('answer')
                        }
                        download_list.append(data)
        return download_list
    download_list = generate_download_list(kakomon_list, faculties, methods)

    def generate_pdf_lists(code, download_list):
        base_url = "https://www.toshin-kakomon.com/kakomon_db/ex/data/{}/{}/{}{}/{}{}{}{}001m0.pdf"
        pdf_lists = []

        for item in download_list:
            year = item.get('year')
            prefix = item.get('prefix')
            number = item.get('number')
            yy = year[-2:]
            number_hex = '{:X}'.format(int(number))
            faculty = item.get('faculty')
            method = item.get ('method')
            subject = item.get('subject')

            if int(year) > 2004:
                url = base_url.format(year, code, prefix, number, prefix, code, yy, number_hex)
                pdf_lists.append({'url': url, 'year': year, 'faculty': faculty, 'method': method, 'subject': subject})

        return pdf_lists
    pdf_lists = generate_pdf_lists(code, download_list)
    
    def generate_answer_lists(code, downloads):
        print("\nしばらくお持ちください．．．")

        base_url = "https://www.toshin-kakomon.com/kakomon_db/ex/data/{}/{}/{}{}/{}{}{}{}{}01k0.gif"
        answer_lists = []

        for item in downloads:
            year = item.get('year')
            prefix = item.get('prefix')
            number = item.get('number')
            yy = year[-2:]
            number_hex = '{:X}'.format(int(number))
            faculty = item.get('faculty')
            method = item.get ('method')
            subject = item.get('subject')
        
            if int(year) > 2004 and item.get('answer'):
                for i in range (1, 10):
                    url = base_url.format(year, code, prefix, number, prefix, code, yy, number_hex, str(i))
                    response = requests.head(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=10)
                    try:
                        if response.status_code == 200:
                            answer_lists.append({'url': url, 'year': year, 'faculty': faculty, 'method': method, 'subject': subject, 'number': str(i)})
                        elif response.status_code == 404:
                            break
                    except requests.RequestException as e:
                        print(f"Error accessing {url}: {e}")
            
        return answer_lists
    answer_lists = generate_answer_lists(code, download_list)

    download_path = f"{university}/" if DLPATH == "" else DLPATH
    os.makedirs(download_path, exist_ok=True)

    def select_download_mode():
        print("\nダウンロード方法を選択:")
        print("1. 年度別")
        print("2. 科目別")
        print("3. 両方")

        while True:
            choice = input("\n番号を入力: ")
            if choice == "1":
                print("\nダウンロードしています...")
                mode = "year"
                break
            elif choice == "2":
                print("\nダウンロードしています...")
                mode = "subject"
                break
            elif choice == "3":
                print("\nダウンロードしています...")
                mode = "both"
                break
            else:
                print("無効な選択です。もう一度やり直してください。")
                continue

        return mode
    mode = select_download_mode()

    def download_file(url, filepath):
        try:
            response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=10)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
            else:
                print(f"ダウンロードに失敗しました: {url}")
        except requests.RequestException as e:
            print(f"ダウンロードエラー: {url}: {e}")
    def download_by_year(download_path, pdf_urls, answer_urls):
        for item in pdf_urls:
            year = item.get('year')
            subject = item.get('subject')
            url = item.get('url')
            faculty = item.get('faculty')
            method = item.get('method')
            year_pdf_path = f"{download_path}/{faculty}/{method}/年度別/{year}"
            os.makedirs(year_pdf_path, exist_ok=True)
            download_file(url, f"{year_pdf_path}/{subject}.pdf")
        
        for item in answer_urls:
            year = item.get('year')
            subject = item.get('subject')
            url = item.get('url')
            number = item.get('number')
            faculty = item.get('faculty')
            method = item.get('method')
            year_answer_path = f"{download_path}/{faculty}/{method}/年度別/{year}/解答"
            os.makedirs(year_answer_path, exist_ok=True)
            download_file(url, f"{year_answer_path}/{subject}_{number}.gif")
    def download_by_subject(download_path, pdf_urls, answer_urls):
        for item in pdf_urls:
            year = item.get('year')
            subject = item.get('subject')
            url = item.get('url')
            faculty = item.get('faculty')
            method = item.get('method')
            subject_pdf_path = f"{download_path}/{faculty}/{method}/科目別/{subject}/{year}"
            os.makedirs(subject_pdf_path, exist_ok=True)
            download_file(url, f"{subject_pdf_path}/問題.pdf")

        for item in answer_urls:
            year = item.get('year')
            subject = item.get('subject')
            url = item.get('url')   
            number = item.get('number')
            faculty = item.get('faculty')
            method = item.get('method')
            subject_answer_path = f"{download_path}/{faculty}/{method}/科目別/{subject}/{year}"
            os.makedirs(subject_answer_path, exist_ok=True)
            download_file(url, f"{subject_answer_path}/解答_{number}.gif")

    if mode in ["year", "both"]:
        download_by_year(download_path, pdf_lists, answer_lists)
    if mode in ["subject", "both"]:
        download_by_subject(download_path, pdf_lists, answer_lists)

    print("完了しました")

def main():
    parser = argparse.ArgumentParser(description="tkdl: toshin-kakomon-downloader")
    subparsers = parser.add_subparsers(dest="command")
    args = parser.parse_args()

    # config
    config_parser = subparsers.add_parser("config", help="設定を変更")
    config_parser.add_argument("key", choices=["email", "password", "dlpath"], nargs="?", help="変更する設定")
    config_parser.add_argument("value", nargs="?")
    # update
    subparsers.add_parser("update", help="大学リストを更新")
    # help
    subparsers.add_parser("help", help="ヘルプを表示")
    # search
    search_parser = subparsers.add_parser("search", help="検索を実行")
    search_parser.add_argument("query", nargs="?", default=None, help="検索する文字列")

    if args.command == "config":
        config(args.key, args.value)
    elif args.command == "update":
        update()
    elif args.command == "help":
        parser.print_help()
    elif args.command == "search":
        for result in search(args.query):
            print(result)
    else:
        download()

if __name__ == "__main__":
    main()