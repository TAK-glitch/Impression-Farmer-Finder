import os
import requests


#API料金の目安 -----2026/5時点----- 
#MAX_RESULTS = 10　で約5セント, MAX_RESULTS = 100 で約50セント 

RUN_PRINT = True  #ターミナル出力
RUN_SAVE = False    #txt保存 実行ごとに、上書き保存なので気を付けること
MAX_RESULTS = 10  #取得件数、10件を目安、100件取得すると、ターミナルの表示上限を超えて全件確認しづらいので、RUN_SAVEを利用してtxtデータで取得して
MAX_PAGES = 2      #MAX_RESULTSを MAX_PAGES 回繰り返す 


#対象にするバズ投稿ID
#例:https://c/com/etc...
TARGET_TWEET_ID = "2050530753524482477"


def get_x_headers():
    x_bearer_token = os.getenv("X_BEARER_TOKEN")

    if not x_bearer_token:
        print("X_BEARER_TOKENが読み込めません")
        return None
 
    return {"Authorization":f"Bearer {x_bearer_token}"}


def fetch_replies(tweet_id, max_results=MAX_RESULTS, next_token=None):
    url = "https://api.x.com/2/tweets/search/recent"

    headers = get_x_headers()
    if headers is None:
        return None
    
    params = {
        "query": f"conversation_id:{tweet_id} is:reply",
        "max_results": max_results,
        "tweet.fields": "id,text,author_id,created_at,lang,conversation_id,public_metrics,referenced_tweets",
        "expansions": "author_id",
        "user.fields": "id,name,username,verified,verified_type,created_at,description,public_metrics",
    }

    if next_token:
        params["pagination_token"] = next_token

    print("送信パラメータ:")
    print(params)    

    response = requests.get(url, headers=headers, params=params)

    print("X APIステータスコード:")
    print(response.status_code)

    data = response.json()

    return data


def fetch_replies_pages(tweet_id, max_results=MAX_RESULTS, max_pages=MAX_PAGES):
    all_tweets = []
    all_users = []
    seen_tweet_ids = set()
    next_token = None

    for page in range(max_pages):
        print(f"{page + 1}ページ目を取得中")

        data = fetch_replies(tweet_id, max_results, next_token)

        if not data:
            print("データ取得に失敗しました")
            break

        tweets = data.get("data", [])
        users = data.get("includes", {}).get("users", [])

        for tweet in tweets:
            reply_id = tweet.get("id")

            if reply_id in seen_tweet_ids:
                print("重複投稿をスキップ", reply_id)
                continue

            seen_tweet_ids.add(reply_id)
            all_tweets.append(tweet)

        all_users.extend(users)    

        meta = data.get("meta", {})
        next_token = meta.get("next_token")

        print("meta:", meta)

        if "errors" in data:
            print("errors:", data["errors"])

        if not tweets:
            print("tweets が空です")
            print("data全体:", data)

        print("今回取得した件数", len(tweets))
        print("累計取得件数", len(all_tweets))

        if not next_token:
            print("次ページがないため取得を終了します")
            break

    merged_data = {
        "data": all_tweets,
        "includes": {
            "users": all_users
        },
    }    

    return merged_data   


def build_reply_items(data):
    if not data:
        return []

    tweets = data.get("data", [])
    user_map = build_user_map(data)

    reply_items = []

    for tweet in tweets:
        author_id = tweet.get("author_id")
        user = user_map.get(author_id, {})  

        reply_items.append({
            "tweet":tweet,
            "user":user,
        })

    return reply_items          


def build_user_map(data):
    users = data.get("includes", {}).get("users", [])

    user_map = {}

    for user in users:
        user_id = user.get("id")
        user_map[user_id] = user

    return user_map


def print_replies(data):
    if not data:
        print("データがありません")
        return

    if "errors" in data:
        print("エラー:")
        print(data["errors"])

    tweets = data.get("data",[])

    if not tweets:
        print("リプライを取得できませんでした")
        print("API制限,検索期間,対象ID,権限などが原因の可能性があります")
        return

    user_map = build_user_map(data) 

    print("取得したリプライ:")
    print("====================================================")

    for tweet in tweets:
        author_id = tweet.get("author_id")
        user = user_map.get(author_id, {})

        public_metrics = tweet.get("public_metrics", {})
        user_metrics = user.get("public_metrics", {})

        print("------")
        print("投稿ID:", tweet.get("id"))
        print("作成日時:", tweet.get("created_at"))
        print("言語:", tweet.get("lang"))
        print("本文:", tweet.get("text"))

        print("投稿者ID:", author_id)
        print("表示名:", user.get("name"))
        print("ユーザー名:", user.get("username"))
        print("認証済み:", user.get("verified"))
        print("認証タイプ:", user.get("verified_type"))    
        print("プロフィール:", user.get("description"))

        print("投稿メトリクス:")
        print("  いいね:", public_metrics.get("like_count"))
        print("  リポスト:", public_metrics.get("retweet_count"))
        print("  返信:", public_metrics.get("reply_count"))
        print("  引用:", public_metrics.get("quote_count"))
        print("  ブックマーク:", public_metrics.get("bookmark_count"))
        print("  インプレッション:", public_metrics.get("impression_count"))

        print("ユーザーメトリクス:")
        print("  フォロワー:", user_metrics.get("followers_count"))
        print("  フォロー:", user_metrics.get("following_count"))
        print("  投稿数:", user_metrics.get("tweet_count"))
        print("  リスト登録:", user_metrics.get("listed_count"))   


def save_replies_to_txt(data):
    if not data:
        print("保存するデータがありません")
        return

    tweets = data.get("data", [])

    if not tweets:
        print("保存するリプライがありません")
        return

    user_map = build_user_map(data)

    with open("replies.txt", "w", encoding="utf-8") as f:
        f.write("取得したリプライ一覧\n")
        f.write("==============================\n\n")

        for tweet in tweets:
            author_id = tweet.get("author_id")
            user = user_map.get(author_id, {})

            public_metrics = tweet.get("public_metrics", {})
            user_metrics = user.get("public_metrics", {})

            f.write("------\n")
            f.write(f"投稿ID: {tweet.get('id')}\n")
            f.write(f"作成日時: {tweet.get('created_at')}\n")
            f.write(f"言語: {tweet.get('lang')}\n")
            f.write(f"本文: {tweet.get('text')}\n")
            f.write(f"投稿者ID: {author_id}\n")
            f.write(f"表示名: {user.get('name')}\n")
            f.write(f"ユーザー名: {user.get('username')}\n")
            f.write(f"認証済み: {user.get('verified')}\n")
            f.write(f"認証タイプ: {user.get('verified_type')}\n")
            f.write(f"プロフィール: {user.get('description')}\n")

            f.write("投稿メトリクス:\n")
            f.write(f"  いいね: {public_metrics.get('like_count')}\n")
            f.write(f"  リポスト: {public_metrics.get('retweet_count')}\n")
            f.write(f"  返信: {public_metrics.get('reply_count')}\n")
            f.write(f"  引用: {public_metrics.get('quote_count')}\n")
            f.write(f"  ブックマーク: {public_metrics.get('bookmark_count')}\n")
            f.write(f"  インプレッション: {public_metrics.get('impression_count')}\n")

            f.write("ユーザーメトリクス:\n")
            f.write(f"  フォロワー: {user_metrics.get('followers_count')}\n")
            f.write(f"  フォロー: {user_metrics.get('following_count')}\n")
            f.write(f"  投稿数: {user_metrics.get('tweet_count')}\n")
            f.write(f"  リスト登録: {user_metrics.get('listed_count')}\n")

            f.write("\n")

    print("replies.txt に保存しました")              


def main():
    print("リプライ取得テスト開始")
    print("対象投稿ID:",TARGET_TWEET_ID)

    data = fetch_replies_pages(TARGET_TWEET_ID)

    reply_items = build_reply_items(data)
    print("tweet/user ペア数", len(reply_items))

    if RUN_PRINT:
        print_replies(data)

    if RUN_SAVE:
        save_replies_to_txt(data)


if __name__=="__main__":
    main()    
