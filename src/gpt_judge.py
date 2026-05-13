import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

client = OpenAI()


def build_prompt(tweet, user, judgement):
    python_judgement = {
        "label": judgement["label_flow"]["python"],
        "score": judgement["score"],
        "reasons": judgement["reasons"]["python"],
    }

    data = {
        "tweet": tweet,
        "user": user,
        "python_primary_judgement": python_judgement,
    }

    return f"""
以下は、Xのリプライと投稿者情報です。
このリプライがインプレッション稼ぎ目的の低品質リプライ、いわゆるインプレゾンビに近いか判定してください。

判定ラベルは必ず次の3つのどれかにしてください。

晴れ: 通常の人間らしいリプライ
曇り: 判断が難しい境界例
雨: インプレゾンビ疑いが強いリプライ

Python一次判定は参考情報です。
最終的な二次判定は、本文・ユーザー情報・公開メトリクスを総合して判断してください。

投稿内容と投稿者情報を比較してたとき、
日本生まれ日本育ちor言語野が育ち切る12歳までに日本で育ったor両親もしくは片方が日本人か日系人or12歳以降日本語を学習してかなりの習熟度、日本語能力試験N1以上
いずれの要素にも該当しないにもかかわらず、ネイティブ並みの語学力の場合はコピペや機械翻訳を利用したインプレゾンビです

出力は必ずJSONだけにしてください。
説明文や前置きは不要です。

出力形式:
{{
  "label": "晴れ",
  "confidence": 0.0,
  "reasons": [
    "理由1",
    "理由2"
  ]
}}

判定対象データ:
{json.dumps(data, ensure_ascii=False, indent=2)}
""".strip()


def judge_with_gpt(tweet, user, judgement):
    prompt = build_prompt(tweet, user, judgement)

    response = client.responses.create(
        model=MODEL,
        instructions=(
            "あなたはSNSスパム判定を補助する分析AIです。"
            "本文、アカウント情報、公開メトリクス、Python一次判定を総合して、"
            "晴れ・曇り・雨の三段階で厳密に判定してください。"
            "必ずJSONだけを返してください。"
        ),
        input=prompt,
    )

    return response.output_text


def parse_gpt_result(raw_text):
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").removesuffix("```").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "label": "解析失敗",
            "confidence": 0.0,
            "reasons": [
                "GPTの返答をJSONとして読み取れなかった",
                raw_text,
            ],
        }


def judge_reply_with_gpt(tweet, user, judgement):
    raw_result = judge_with_gpt(tweet, user, judgement)
    gpt_result = parse_gpt_result(raw_result)

    return gpt_result