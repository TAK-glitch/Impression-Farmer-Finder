import re


SPECIAL_LOW_CONTENT_LANGS = {
    "qam",  # mentions only
    "qct",  # cashtags only
    "qht",  # hashtags only
    "qme",  # media links only
    "qst",  # very short text
    "zxx",  # media / Twitter Card only
    "und",  # undefined
}

WATCH_LANGS = {
    "que",  # Quechua。実データ上、要注意ならここに追加
}

SUSPICIOUS_PROFILE_WORDS = {
    "web3",
    "crypto",
    "nft",
    "airdrop",
    "defi",
    "eth",
    "btc",
    "forex",
    "trader",
    "investment",
}


def classify_score(score):
    if score >= 55:
        return "雨"
    elif score >= 30:
        return "曇り"
    else:
        return "晴れ"


def remove_mentions(text):
    return re.sub(r"@\w+", "", text).strip()


def remove_urls(text):
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"t\.co/\S+", "", text)
    return text.strip()


def has_url(text):
    return "http://" in text or "https://" in text or "t.co/" in text


def count_urls(text):
    return len(re.findall(r"https?://\S+|t\.co/\S+", text))


def make_reply_url(tweet, user):
    username = user.get("username")
    tweet_id = tweet.get("id")

    return f"https://x.com/{username}/status/{tweet_id}"


def get_meaningful_text(text):
    """
    メンションとURLを除いた本文。
    URL中心かどうか、短文かどうかを見るために使う。
    """
    text_without_mentions = remove_mentions(text)
    text_without_urls = remove_urls(text_without_mentions)

    return text_without_urls.strip()


def is_url_only_reply(text):
    text_without_mentions = remove_mentions(text)

    if not text_without_mentions:
        return False

    return has_url(text_without_mentions) and len(text_without_mentions.split()) <= 2


def is_short_text(text):
    clean_text = get_meaningful_text(text)

    return len(clean_text) <= 10


def is_grok_account(user):
    username = user.get("username", "")
    name = user.get("name", "")

    return username.lower() == "grok" or name.lower() == "grok"


def has_suspicious_profile_word(user):
    fields = [
        user.get("name", ""),
        user.get("username", ""),
        user.get("description", ""),
    ]

    combined_text = " ".join(fields).lower()

    return any(word in combined_text for word in SUSPICIOUS_PROFILE_WORDS)


def score_reply(tweet, user):
    score = 0
    reasons = []

    # Grok公式応答は、インプレゾンビ本人ではなく派生ノイズとして扱う
    if is_grok_account(user):
        reasons.append("Grok公式応答のため、アカウント判定対象外")
        return 0, "対象外", reasons

    lang = tweet.get("lang")
    text = tweet.get("text", "")

    tweet_metrics = tweet.get("public_metrics", {})
    user_metrics = user.get("public_metrics", {})

    verified = user.get("verified")
    verified_type = user.get("verified_type")
    description = user.get("description", "")

    like_count = tweet_metrics.get("like_count", 0)
    retweet_count = tweet_metrics.get("retweet_count", 0)
    reply_count = tweet_metrics.get("reply_count", 0)
    quote_count = tweet_metrics.get("quote_count", 0)
    bookmark_count = tweet_metrics.get("bookmark_count", 0)
    impression_count = tweet_metrics.get("impression_count", 0)

    followers_count = user_metrics.get("followers_count", 0)
    following_count = user_metrics.get("following_count", 0)
    tweet_count = user_metrics.get("tweet_count", 0)
    listed_count = user_metrics.get("listed_count", 0)

    # 言語判定
    if lang in SPECIAL_LOW_CONTENT_LANGS:
        score += 25
        reasons.append(f"言語コードが {lang} のため、本文情報量が少ない返信")
    elif lang in WATCH_LANGS:
        score += 20
        reasons.append(f"言語が {lang} のため、日本語投稿への自然な返信ではない可能性がある")
    elif lang != "ja":
        score += 15
        reasons.append(f"言語が {lang} のため、日本語投稿への自然な返信ではない可能性がある")

    # 本文判定
    meaningful_text = get_meaningful_text(text)
    url_count = count_urls(text)

    if is_url_only_reply(text):
        if len(meaningful_text) >= 20:
            score += 25
            reasons.append("URL中心だが本文も一定量ある")
        else:
            score += 40
            reasons.append("本文がURL中心の返信")
    elif has_url(text):
        score += 20
        reasons.append("本文にURLが含まれている")

    if url_count >= 2:
        score += 10
        reasons.append("URLが複数含まれている")

    # Grok呼び出し
    # 単独では雨確定にせず、返信欄占有の補助シグナルとして扱う
    if "@grok" in text.lower():
        score += 10
        reasons.append("Grok呼び出しによる返信欄占有")

    # 認証判定
    if verified:
        score += 10
        reasons.append("認証済みアカウント")

    if verified_type == "blue":
        score += 25
        reasons.append("認証タイプが blue")

    # プロフィール判定
    if not description:
        score += 15
        reasons.append("プロフィールが空欄")
    elif len(description) <= 15:
        score += 10
        reasons.append("プロフィールが短い")

    if has_suspicious_profile_word(user):
        score += 15
        reasons.append("プロフィール/名前に投資・Web3・暗号資産系の語が含まれる")

    # 投稿メトリクス判定
    reaction_count = (
        like_count
        + retweet_count
        + reply_count
        + quote_count
        + bookmark_count
    )

    is_suspicious_text = (
        is_url_only_reply(text)
        or is_short_text(text)
        or lang in SPECIAL_LOW_CONTENT_LANGS
        or lang != "ja"
    )

    if impression_count >= 100 and reaction_count == 0:
        if is_suspicious_text:
            score += 15
            reasons.append("怪しい本文条件があり、インプレッションに対して反応がない")
        else:
            score += 5
            reasons.append("インプレッションに対して反応がない")

    # ユーザーメトリクス判定
    if followers_count >= 1000 and following_count >= 1000:
        score += 10
        reasons.append("フォロワー数とフォロー数がどちらも多い")

    # 投稿数は補助条件に弱体化
    if tweet_count >= 100000:
        score += 15
        reasons.append("投稿数が非常に多い")
    elif tweet_count >= 30000:
        score += 10
        reasons.append("投稿数が多い")
    elif tweet_count >= 10000:
        score += 5
        reasons.append("投稿数がやや多い")

    if followers_count >= 1000 and listed_count <= 1:
        score += 5
        reasons.append("フォロワー数に対してリスト登録数が少ない")

    label = classify_score(score)

    if (
        label == "曇り"
        and score >= 50
        and verified_type == "blue"
        and followers_count >= 1000
        and following_count >= 1000
    ):
        label = "雨"
        reasons.append("50点以上かつblue・相互数多めのため雨へ昇格")


    return score, label, reasons


def print_result(tweet, user, score, label, reasons):
    print("スコアリング結果")
    print("========================================")
    print("投稿ID:", tweet.get("id"))
    print("作成日時:", tweet.get("created_at"))
    print("言語:", tweet.get("lang"))
    print("本文:", tweet.get("text"))
    print("URL:", make_reply_url(tweet, user))
    print("投稿者ID:", tweet.get("author_id"))
    print("表示名:", user.get("name"))
    print("ユーザー名:", user.get("username"))
    print("認証済み:", user.get("verified"))
    print("認証タイプ:", user.get("verified_type"))
    print("プロフィール:", user.get("description"))
    print("----------------------------------------")
    print("スコア:", score)
    print("判定:", label)
    print("理由:")

    for reason in reasons:
        print("-", reason)
