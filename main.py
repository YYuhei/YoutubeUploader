import os
import datetime
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError, ResumableUploadError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

# チャンネルID
CHANNEL_ID = "XXXX"

# アップロードする動画ファイルのパス
TODAY = datetime.date.today()
TWODAY = datetime.timedelta(days=2)
DOWNLOADDAY = TODAY - TWODAY
FILE_PATH = "../AutoClippingApp/" + DOWNLOADDAY.strftime("%Y%m%d_") + "dailyranking.mp4"

# アップロードする動画のサムネイル画像のパス
THUMBNAIL_PATH = (
    "../AutoClippingApp/thumbnail/" + DOWNLOADDAY.strftime("%Y%m%d") + "_thumbnail.png"
)
THUMBNAIL_FULL_PATH = (
    "C:/Users/yuhei/Documents/PythonApp/AutoClippingApp/thumbnail/"
    + DOWNLOADDAY.strftime("%Y%m%d")
    + "_thumbnail.png"
)

# 動画のタイトルを記述したテキストファイルのパス
TITLE_FILE = "../AutoClippingApp/movie_title.txt"

# 動画の説明を記述したテキストファイルのパス
DESCRIPTION_FILE = "../AutoClippingApp/video_description.txt"

# OAuth2.0の認証情報用のjsonファイルのパス
TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secrets.json"

# YouTube Data API のスコープ
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# 動画のプライバシー設定
PRIVACY_STATUS = "public"  # public or private

# サムネイルの最大サイズ
MAX_THUMBNAIL_SIZE = 1 * 1024 * 1024  # 1MB

# サムネイルフォルダのパス
THUMBNAIL_FOLDER_PATH = (
    "XXXXXX"
)


def compress_thumbnail(thumbnail_path):
    """
    サムネイルのサイズを1MB未満に調整する
    """

    print("サムネイルのサイズをチェック中...")
    thumbnail_size = os.path.getsize(thumbnail_path)
    if thumbnail_size < MAX_THUMBNAIL_SIZE:
        print(f"サムネイルのサイズは{thumbnail_size/1024/1024:.2f}MBで1MB未満です。")
        return thumbnail_path

    print(f"サムネイルのサイズは{thumbnail_size/1024/1024:.2f}MBで1MBを超えています。圧縮を試みます...")
    compressed_path = thumbnail_path

    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_experimental_option("detach", True)
    # ダウンロード先フォルダの設定
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option(
        "prefs", {"download.default_directory": THUMBNAIL_FOLDER_PATH}
    )
    options.use_chromium = True
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    # tinypng.comにアクセス
    driver.get("https://tinypng.com/")
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver=driver, timeout=30)
    # サムネイル画像アップロード
    element_input = driver.find_element(
        By.XPATH, '//*[@id="top"]/section[2]/div[1]/section/input'
    )
    element_input.send_keys(THUMBNAIL_FULL_PATH)
    # 圧縮処理が終わるまで待機
    wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, '//*[@id="top"]/section[2]/section/div[2]')
        )
    )
    # 元のサムネイル画像を削除
    os.remove(thumbnail_path)
    # 圧縮後のサムネイル画像をダウンロード
    element_a = driver.find_element(
        By.XPATH, '//*[@id="top"]/section[2]/div[2]/section/ul/li/div[3]/a'
    )
    element_a.click()
    time.sleep(2)
    driver.quit()

    compressed_size = os.path.getsize(compressed_path)
    print(f"圧縮後のサムネイルのサイズは{compressed_size/1024/1024:.2f}MBです。")

    if compressed_size > MAX_THUMBNAIL_SIZE:
        print("サムネイルの圧縮に失敗しました。処理を中断します。")
        exit()

    print(f"圧縮されたサムネイルを使用します: {compressed_path}")
    return compressed_path


def get_last_video_id(youtube, channel_id):
    """
    前回投稿した動画のIDを取得する関数
    """
    request = youtube.search().list(
        part="id", channelId=channel_id, order="date", type="video", maxResults=1
    )
    response = request.execute()
    last_video_id = response["items"][0]["id"]["videoId"]
    return last_video_id


def get_credentials():
    """
    Google APIにアクセスするために必要な認証情報を取得する関数
    """
    creds = None
    # 既に認証情報が保存されている場合はファイルから読み込む
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)

    # 保存されている認証情報が無効であれば更新する
    if not creds or not creds.valid:
        # 期限切れであれば自動的にリフレッシュする
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # 初めて認証を行う場合はブラウザで認証を行う
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 新しい認証情報をファイルに保存する
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    # 有効な認証情報を返す
    return creds


def build_youtube_client():
    """
    YouTube Data API のクライアントを構築する関数
    """
    credentials = get_credentials()
    return build("youtube", "v3", credentials=credentials)


def upload_video(youtube, file_path, thumbnail_path):
    """
    動画をアップロードする関数
    """
    # 動画のタイトルと説明をファイルから読み込む
    with open(TITLE_FILE, "r", encoding="UTF-8") as f_title, open(
        DESCRIPTION_FILE, "r", encoding="UTF-8"
    ) as f_description:
        title = f_title.read()
        description = f_description.read()

    # 前回投稿した動画の情報を取得する
    # previous_video_id = get_last_video_id(youtube, CHANNEL_ID)

    # 動画のアップロード情報を設定する
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["にじさんじ", "ホロライブ", "切り抜き", "ランキング", "作業用"],
            "categoryId": 24,
        },
        "status": {"privacyStatus": PRIVACY_STATUS},
    }
    try:
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True),
            notifySubscribers=False,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}.")
        print(f"アップロードが完了しました！ Video ID: {response['id']}")

        # アップロードした動画のIDを取得する
        video_id = response["id"]

        # アップロードした動画にサムネイルを設定する
        upload_thumbnail(youtube, video_id, thumbnail_path)

    except (HttpError, ResumableUploadError) as e:
        print(f"An error occurred: {e}")


def upload_thumbnail(youtube, video_id, thumbnail_path):
    # アップロードした動画にサムネイルを設定する
    request = youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumbnail_path, chunksize=-1, resumable=True),
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}.")
    print("サムネイルのアップロードが完了しました！")


if __name__ == "__main__":
    # サムネイルサイズを調整する
    compress_thumbnail(THUMBNAIL_PATH)

    # YouTube API のクライアントを構築する。
    youtube = build_youtube_client()

    # 動画ファイルをアップロードする。
    upload_video(youtube, FILE_PATH, THUMBNAIL_PATH)
