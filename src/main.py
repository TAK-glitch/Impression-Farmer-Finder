import os
from datetime import datetime

from reply_collector import fetch_replies_pages
from reply_collector import build_reply_items
from zombie_score import score_reply
from zombie_score import make_reply_url


#=======================================================================
#操作盤設定
#=======================================================================

TARGET_TWEET_ID = "XXXXXXXXXXXXXXXX"  #対象にするバズ投稿ID  例:https://c/com/etc...

MAX_RESULTS = 100  #取得件数、10件を目安、100件取得すると、ターミナルの表示上限を超えて全件確認しづらいので、RUN_SAVEを利用してtxtデータで取得すること
MAX_PAGES = 3     #MAX_RESULTSを MAX_PAGES 回繰り返す 

#10件取得で約5セント、300件取得で約1.5ドル　2026.5月時点


RUN_GPT_JUDGE = True
GPT_TARGET_LABELS = ["曇り", "晴れ"]
GPT_MAX_ITEMS = 300


DISPLAY_LIMIT = 20

RUN_SAVE_RESULTS = True
RESULTS_DIR ="results"


#=======================================================================
# Python_スコアリング処理
#=======================================================================

def score_reply_items(reply_items):
    scored_items = []

    for item in reply_items:
        tweet = item["tweet"]
        user = item["user"]

        score, label, reasons = score_reply(tweet, user)
        url = make_reply_url(tweet, user)

        scored_items.append({
            "tweet": tweet,
            "user": user,
            "url": url,
            "judgement": {
                "final_label": label,
                "source": "python",
                "label_flow": {
                    "python": label,
                    "gpt": None,
                },
                "score": score,
                "confidence": None,
                "reasons": {
                    "python": reasons,
                    "gpt": [],
                },
            },
        })

    return scored_items


#=======================================================================
#　Chat_GPT スコアリング処理
#=======================================================================

def select_gpt_targets(scored_items):
    gpt_targets = []

    for item in scored_items:
        python_label = item["judgement"]["label_flow"]["python"]

        if python_label in GPT_TARGET_LABELS:
            gpt_targets.append(item)

        if len(gpt_targets) >= GPT_MAX_ITEMS:
            break

    return gpt_targets


def apply_gpt_judgement(scored_items):
    if not RUN_GPT_JUDGE:
        return scored_items

    from gpt_judge import judge_reply_with_gpt

    gpt_targets = select_gpt_targets(scored_items)

    print("========== GPT二次判定開始 ==========")
    print("GPT判定対象件数:", len(gpt_targets))
    print()

    for index, item in enumerate(gpt_targets, start=1):
        tweet = item["tweet"]
        user = item["user"]
        judgement = item["judgement"]

        print(f"[{index}] GPT判定中")
        print("投稿ID:", tweet.get("id"))
        print("Python判定:", judgement["label_flow"]["python"])
        print("Pythonスコア:", judgement["score"])

        gpt_result = judge_reply_with_gpt(tweet, user, judgement)

        judgement["label_flow"]["gpt"] = gpt_result.get("label")
        judgement["confidence"] = gpt_result.get("confidence")
        judgement["reasons"]["gpt"] = gpt_result.get("reasons", [])

        if gpt_result.get("label") in ["晴れ", "曇り", "雨"]:
            judgement["final_label"] = gpt_result.get("label")
            judgement["source"] = "gpt"
        else:
            judgement["source"] = "python_gpt_parse_failed"

        print("GPT判定:", judgement["label_flow"]["gpt"])
        print("信頼度:", judgement["confidence"])
        print()

    print("========== GPT二次判定終了 ==========")
    print()

    return scored_items

#=========================================================================
# 集計処理
# ========================================================================

def count_labels(scored_items):
    label_counts = {
        "雨": 0,
        "曇り": 0,
        "晴れ": 0,
    }

    for item in scored_items:
        label = item["judgement"]["final_label"]

        if label in label_counts:
            label_counts[label] += 1

    return label_counts


def print_summary(scored_items):
    label_counts = count_labels(scored_items)

    print("========== 集計 ==========")
    print("取得・採点件数:", len(scored_items))
    print("雨:", label_counts["雨"])
    print("曇り:", label_counts["曇り"])
    print("晴れ:", label_counts["晴れ"])
    print("==========================")
    print()


#=========================================================================
# ターミナル表示
# ========================================================================

def print_item(item, index):
    tweet = item["tweet"]
    user = item["user"]
    judgement = item["judgement"]

    print(f"[{index}]")
    print("判定:", judgement["final_label"])
    print("判定元:", judgement["source"])
    print("Python判定:", judgement["label_flow"]["python"])
    print("GPT判定:", judgement["label_flow"]["gpt"])
    print("スコア:", judgement["score"])
    print("信頼度:", judgement["confidence"])
    print("URL:", item["url"])
    print("投稿ID:", tweet.get("id"))
    print("作成日時:", tweet.get("created_at"))
    print("言語:", tweet.get("lang"))
    print("本文:", tweet.get("text"))
    print("表示名:", user.get("name"))
    print("ユーザー名:", user.get("username"))
    print("認証済み:", user.get("verified"))
    print("認証タイプ:", user.get("verified_type"))

    print("Python理由:")
    for reason in judgement["reasons"]["python"]:
        print("-", reason)

    if judgement["reasons"]["gpt"]:
        print("GPT理由:")
        for reason in judgement["reasons"]["gpt"]:
            print("-", reason)

    print("----------------------------------------")


def print_top_suspicious(scored_items):
    suspicious_items = []

    for item in scored_items:
        final_label = item["judgement"]["final_label"]

        if final_label in ["雨", "曇り"]:
            suspicious_items.append(item)

    suspicious_items.sort(
        key=lambda item: item["judgement"]["score"],
        reverse=True
    )

    print(f"========== 雨・曇り 上位{DISPLAY_LIMIT}件 ==========")

    for index, item in enumerate(suspicious_items[:DISPLAY_LIMIT], start=1):
        print_item(item, index)


#=========================================================================
# txt保存
# ========================================================================

def save_results_to_txt(scored_items):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results_{timestamp}.txt"
    filepath = os.path.join(RESULTS_DIR, filename)

    label_counts = count_labels(scored_items)

    sorted_items = sorted(
        scored_items,
        key=lambda item: item["judgement"]["score"],
        reverse=True
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("インプレゾンビ判定結果\n")
        f.write("==============================\n\n")

        f.write("========== 集計 ==========\n")
        f.write(f"取得・採点件数: {len(scored_items)}\n")
        f.write(f"雨: {label_counts['雨']}\n")
        f.write(f"曇り: {label_counts['曇り']}\n")
        f.write(f"晴れ: {label_counts['晴れ']}\n")
        f.write("==========================\n\n")

        for index, item in enumerate(sorted_items, start=1):
            tweet = item["tweet"]
            user = item["user"]
            judgement = item["judgement"]

            f.write(f"[{index}]\n")
            f.write(f"最終判定: {judgement['final_label']}\n")
            f.write(f"判定元: {judgement['source']}\n")
            f.write(f"Python判定: {judgement['label_flow']['python']}\n")
            f.write(f"GPT判定: {judgement['label_flow']['gpt']}\n")
            f.write(f"スコア: {judgement['score']}\n")
            f.write(f"信頼度: {judgement['confidence']}\n")
            f.write(f"URL: {item['url']}\n")
            f.write(f"投稿ID: {tweet.get('id')}\n")
            f.write(f"作成日時: {tweet.get('created_at')}\n")
            f.write(f"言語: {tweet.get('lang')}\n")
            f.write(f"本文: {tweet.get('text')}\n")
            f.write(f"表示名: {user.get('name')}\n")
            f.write(f"ユーザー名: {user.get('username')}\n")
            f.write(f"認証済み: {user.get('verified')}\n")
            f.write(f"認証タイプ: {user.get('verified_type')}\n")

            f.write("Python理由:\n")
            for reason in judgement["reasons"]["python"]:
                f.write(f"- {reason}\n")

            if judgement["reasons"]["gpt"]:
                f.write("GPT理由:\n")
                for reason in judgement["reasons"]["gpt"]:
                    f.write(f"- {reason}\n")

            f.write("----------------------------------------\n\n")

    print(f"{filepath} に全件結果を保存しました")


#=========================================================================
# メイン処理
# ========================================================================

def main():
    print("インプレゾンビ判定メイン処理開始")
    print("対象投稿ID:", TARGET_TWEET_ID)
    print()

    data = fetch_replies_pages(
        TARGET_TWEET_ID,
        MAX_RESULTS,
        MAX_PAGES,
        )

    reply_items = build_reply_items(data)
    print("tweet/user ペア数:", len(reply_items))
    print()

    scored_items = score_reply_items(reply_items)

    final_results = apply_gpt_judgement(scored_items)

    print_summary(final_results)
    print_top_suspicious(final_results)

    if RUN_SAVE_RESULTS:
        save_results_to_txt(final_results)


if __name__ == "__main__":
    main()