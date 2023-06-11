# Youtube自動投稿プログラム

## 説明
YouTube Data API v3を使用してAutoClippingAppで作成した動画を<br>
YouTubeへ自動投稿してくれるプログラム。<br>
事前にGCPからOAuth 2.0とYouTube Data APIの登録が必要。<br>
プログラムを実行すると、以下の処理で自動投稿が始まる。

・AutoClippingAppで作成したサムネイルのサイズを圧縮<br>
・YouTube API のクライアントを構築<br>
・動画ファイルを指定した設定でアップロードする<br>

サムネイル圧縮処理の際に、以下のサイトにSeleniumで画像を自動アップロードしている。<br>
https://tinypng.com/
