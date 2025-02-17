from bs4 import BeautifulSoup
import os
import re
import requests
from requests.auth import HTTPBasicAuth
import toml

def main():

    # 現在のディレクトリを取得
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    CONFIG_FILE = os.path.join(BASE_DIR, "config.toml")

    # config.tomlが無ければ作成する
    if not os.path.exists(CONFIG_FILE):
        print("メールアドレスとパスワードを入力\n")

        while True:
            username = input("メールアドレス: ")
            if not username:
                print("メールアドレスが空です。再度入力してください。")
                continue
            break

        while True:
            password = input("　パスワード　: ")
            if not password:
                print("PASSWORDが空です。再度入力してください。")
                continue
            break

        # config.toml に保存
        config_data = {
            "auth": {
                "username": username,
                "password": password
            }
        }

        with open(CONFIG_FILE, "w") as f:
            toml.dump(config_data, f)

        print("認証情報を保存しました\n")

    # toml モジュールを使って設定ファイルを読み込む
    config = toml.load(CONFIG_FILE)

    USERNAME = config["auth"]["username"]
    PASSWORD = config["auth"]["password"]

    # university_codes.txtを展開
    university_codes = {}
    with open(f"{BASE_DIR}/university_codes.txt", "r", encoding="utf-8") as file:
        for line in file:
            code, name = line.strip().split(", ", 1)
            university_codes[name] = code

    # ダウンロードする大学を入力
    university = input("大学名を入力: ").strip()

    # 大学コードを取得
    university_code = university_codes.get(university)
    if not university_code:
        print("Invalid university name.") # 無効な大学名

    # その大学の過去問データベースにアクセス
    url = f"https://www.toshin-kakomon.com/kakomon_db/ex/menu/{university_code}.html"

    # HTMLを取得
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=5)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 文字コードをHTMLの<meta>タグから取得
    charset = None
    meta_tag = soup.find('meta', attrs={'charset': True})
    if meta_tag:
        charset = meta_tag['charset']
    else:
        meta_tag = soup.find('meta', attrs={'content': re.compile('charset=', re.I)})
        if meta_tag:
            match = re.search(r'charset=([\w-]+)', meta_tag['content'], re.I)
            if match:
                charset = match.group(1)
                            
    # 取得できなかった場合、`apparent_encoding` を使用
    if not charset:
        charset = response.apparent_encoding

    # エンコーディングを適用
    response.encoding = charset

    # BeautifulSoupオブジェクトを更新
    soup = BeautifulSoup(response.text, 'html.parser')

    # numberを抽出する関数
    def extract_number(link):
        match = re.search(r'../data/\d{4}/[^/]+/([^/]+)/[^/]+\.html', link)
        return match.group(1)[-2:] if match else None

    # prefixを抽出する関数
    def extract_prefix(link):
        match = re.search(r'../data/\d{4}/[^/]+/([^/]+)/[^/]+\.html', link)
        return match.group(1)[0] if match else None

    # yearを抽出する関数
    def extract_year(link):
        match = re.search(r'../data/(\d{4})/[^/]+/[^/]+/[^/]+\.html', link)
        return match.group(1) if match else None

    # データを抽出してリストに格納
    data_list = []
    current_faculty = None
    current_method = None

    rows = soup.find_all('tr')
    for row in rows:
        faculty = row.find('td', class_='h2')
        method_t1 = row.find('td', class_='t1')
        method_t2 = row.find('td', class_='t2')
        links_and_subjects = row.find_all('a')

        if faculty:
            current_faculty = faculty.text.strip()

        if method_t1:
            current_method = method_t1.text.strip()
        if method_t2:
            current_method = method_t2.text.strip()

        if current_faculty and current_method and links_and_subjects:
            for link_subject in links_and_subjects:
                subject = link_subject.text.strip()
                link = link_subject.get('href', None)
                if link:
                    number = extract_number(link)
                    prefix = extract_prefix(link)
                    year = extract_year(link)

                    # answerフィールドを追加
                    next_sibling = link_subject.find_next_sibling('img')
                    answer = True if next_sibling and "../img/ka.gif" in next_sibling['src'] else False

                    if number:  # numberが空でない場合のみリストに追加
                        data = {
                            'faculty': current_faculty,
                            'method': current_method,
                            'subject': subject,
                            'number': number,
                            'prefix': prefix,
                            'year': year,
                            'answer': answer
                        }
                        data_list.append(data)

    faculty_list = sorted(set(item['faculty'] for item in data_list))

    # ユーザーに学部を選択させる
    print("\n学部を選択（複数可、カンマ区切り）:")
    for i, faculty in enumerate(faculty_list, 1):
        print(f"{i}. {faculty}")
    faculty_choices = input("\n番号を入力: ").split(',')
    selected_faculties = [faculty_list[int(i)-1] for i in faculty_choices]

    # ユーザーに学科・方式を選択させる
    selected_methods = []
    for faculty in selected_faculties:
        print(f"\n{faculty} の学科・方式を選択（複数可、カンマ区切り）:")
        available_methods = sorted(set(item['method'] for item in data_list if item['faculty'] == faculty))
        for i, method in enumerate(available_methods, 1):
            print(f"{i}. {method}")
        method_choices = input("\n番号を入力: ").split(',')
        selected_methods.extend([available_methods[int(i)-1] for i in method_choices])

    print("\nしばらくお待ちください...")

    # 一致する項目を抽出して辞書に格納
    downloads = []
    for item in data_list:
        for selected_faculty in selected_faculties:
            for selected_method in selected_methods:
                if item.get('faculty') == selected_faculty and item.get('method') == selected_method:
                    data = {
                        'faculty': item.get('faculty'), 
                        'method': item.get('method'),
                        'year': item.get('year'),
                        'prefix': item.get('prefix'),
                        'number': item.get('number'),
                        'subject': item.get('subject'),
                        'answer' : item.get('answer')
                    }
                    downloads.append(data)

    # 問題・解答のベースURL
    base_pdf_url = "https://www.toshin-kakomon.com/kakomon_db/ex/data/{}/{}/{}{}/{}{}{}{}001m0.pdf"
    base_answer_url = "https://www.toshin-kakomon.com/kakomon_db/ex/data/{}/{}/{}{}/{}{}{}{}{}01k0.gif"

    # リストを初期化
    pdf_urls = []
    answer_urls = []

    for item in downloads:
        year = item.get('year')
        prefix = item.get('prefix')
        number = item.get('number')
        subject = item.get('subject')
        answer = item.get('answer')
        faculty = item.get('faculty')
        method = item.get ('method')
        yy = year[-2:]  # yearの下二桁を取得
        number_hex = '{:X}'.format(int(number))  # numberを1桁の16進数に変換

        # 問題PDFのURLリストを生成
        if int(year) > 2004:
            pdf_url = base_pdf_url.format(year, university_code, prefix, number, prefix, university_code, yy, number_hex)
            pdf_urls.append({'url': pdf_url, 'year': year, 'faculty': faculty, 'method': method, 'subject': subject})

        # 解答GIFのURLリストを生成
        if int(year) > 2004 and answer:
            for i in range (1, 10):
                answer_url = base_answer_url.format(year, university_code, prefix, number, prefix, university_code, yy, number_hex, str(i))
                response = requests.head(answer_url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=10)
                try:
                    if response.status_code == 200:
                        answer_urls.append({'url': answer_url, 'year': year, 'faculty': faculty, 'method': method, 'subject': subject, 'number': str(i)})
                    elif response.status_code == 404:
                        break
                except requests.RequestException as e:
                    print(f"Error accessing {url}: {e}")

    download_path = f"{university}/"
    os.makedirs(download_path, exist_ok=True)

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

    if mode in ["year", "both"]:
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

    if mode in ["subject", "both"]:
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

    print("完了しました")

if __name__ == "__main__":
    main()