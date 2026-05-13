import os 
import requests
from openai import OpenAI

RUN_OPENAI_TEST = False #従量課金を利用します　約1セント
RUN_X_TEST = False      #従量課金を利用します　約5セント



def test_openai_api():
    client = OpenAI()

    response = client.responses.create(model="gpt-5.5",input="Python初心者に向けて、APIとは何かを一文で説明して。")

    print("OpenAI API応答:")
    print(response.output_text)


def text_x_api():
    x_bearer_token = os.getenv("X_BEARER_TOKEN")

    url = "https://api.x.com/2/tweets/search/recent"

    headers = {"Authorization": f"Bearer {x_bearer_token}"}

    params = {"query":"python lang:ja -is:retweet","max_results":10}

    response = requests.get(url, headers=headers, params=params)

    print("X APIステータスコード:")
    print(response.status_code)

    data = response.json()

    print("取得した投稿:")
    for tweet in data.get("data",[]):
        print("-----")
        print("ID", tweet.get("id"))
        print("本文",tweet.get("text"))  


def main():
    print("API接続テスト開始")

    x_bearer_token = os.getenv("X_BEARER_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if x_bearer_token:
        print("X_BEARER_TOKEN 読み込みOK")
    else:
        print("X_BEARER_TOKEN が接続されていません")

    if openai_api_key:
        print("OPENAI_API_KEY 読み込みOK")
    else:
        print("OPENAI_API_KEY が接続されていません")        
        return
    
    if RUN_OPENAI_TEST:
        test_openai_api()

    if RUN_X_TEST:            
        text_x_api()


if __name__ == "__main__":
    main()