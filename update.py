import os
import requests
from requests.auth import HTTPBasicAuth
import random
import itertools
from bs4 import BeautifulSoup
import re

# auth.pyのUSERNAMEとPASSWORDを利用する
import auth

USERNAME = auth.USERNAME
PASSWORD = auth.PASSWORD

# URLのベース部分
base_url = "https://www.toshin-kakomon.com/kakomon_db/ex/menu/"

# 存在するURLを格納するリスト
valid_urls = []

# '0'-'9'と'a'-'z'の文字の組み合わせを生成
characters = '0123456789abcdefghijklmnopqrstuvwxyz'

# 2桁の全組み合わせを生成
for combo in itertools.product(characters, repeat=2):
    hex_value = ''.join(combo)  # 2桁の文字列を生成
    url = base_url + hex_value + ".html"
    
    # URLにGETリクエストを送信して存在するか確認（認証付き）
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        if response.status_code == 200:
            valid_urls.append(url)
    except requests.exceptions.RequestException as e:
        # リクエストが失敗した場合はスキップ
        pass

# 存在するURLをtxtファイルに保存
with open("valid_urls.txt", "w") as file:
    for url in valid_urls:
        file.write(url + "\n")

# ファイルの読み込み（UTF-8で読み込む）
with open('valid_urls.txt', 'r', encoding='utf-8') as file:
    urls = file.readlines()

# 新しいファイルの作成（UTF-8で保存）
with open('university_codes.txt', 'w', encoding='utf-8') as new_file:
    for url in urls:
        url = url.strip()  # URLの前後の空白を削除
        try:
            # Basic認証を追加
            response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=10)
            
            # BeautifulSoupで解析
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

            # タイトルを取得（UTF-8に変換）
            title = soup.title.string if soup.title else "No Title"
            title = title.encode('utf-8', 'replace').decode('utf-8')

            # URLの後ろから7文字目から6文字目を取得
            last_seven_chars = url[-7:-5]

            # UTF-8で書き込み
            new_file.write(f"{last_seven_chars}, {title}\n")

        except Exception as e:
            print(f"Error fetching {url}: {e}")
