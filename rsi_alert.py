import json
import socket
from datetime import date

import pandas_ta as ta
import pandas as pd
from time import sleep
from dateutil.relativedelta import relativedelta, MO

import requests

import config_demo

xst = ""
cst = ""


def internet():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except socket.error as ex:
        print(ex)
        return False


def send_telegram_message(text):
    get_current_price_url = "https://api.telegram.org/bot7247049361:AAHdoOiXelivThrVz8GFBqJ6HZEuC9V1klA/sendMessage"
    headers_for_telegram = {
        'Content-type': "application/json"
    }
    payload = json.dumps({
        "chat_id": 1647081321,
        "text": text
    })
    response = requests.request("POST", get_current_price_url, headers=headers_for_telegram, data=payload)

    print(response.text)


def start_session():
    global xst, cst

    payload1 = json.dumps({
        "identifier": config_demo.identifier,
        "password": config_demo.password
    })
    headers1 = {
        'X-CAP-API-KEY': config_demo.api_key,
        'Content-Type': 'application/json'
    }
    response1 = requests.request("POST", config_demo.session_url, headers=headers1, data=payload1)

    if response1.status_code == 200:
        xst = response1.headers['X-SECURITY-TOKEN']
        cst = response1.headers['CST']
    else:

        text = str(response1.status_code) + " returned from method: start_session" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        start_session()


def end_session():
    headers = {
        'X-SECURITY-TOKEN': xst,
        'CST': cst
    }
    response1 = requests.request("DELETE", config_demo.session_url, headers=headers, data={})
    if response1.status_code != 200:
        text = str(response1.status_code) + " returned from method: end_session" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        end_session()


def get_k_lines_and_map_to_df():
    today = date.today()
    last_monday = str(today + relativedelta(weekday=MO(-2)))
    print("getting data beginning from " + last_monday)
    gold = config_demo.gold_url + last_monday + "T00:00:00&max=500"

    headers = {
        'X-SECURITY-TOKEN': xst,
        'CST': cst
    }
    response = requests.request("GET", gold, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return pd.json_normalize(data["prices"])
    else:
        text = str(response.status_code), " error returned from method: get_k_lines_and_map_to_df" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        get_k_lines_and_map_to_df()


def do_the_thing():
    start_session()
    df_obj = get_k_lines_and_map_to_df()
    df_obj['rsi'] = ta.rsi(close=df_obj['closePrice.bid'], length=14)
    df_obj1 = ta.stochrsi(close=df_obj['closePrice.bid'], length=14, rsi_length=14, k=3, d=3)
    df_final = df_obj1.tail(2)
    if df_final['STOCHRSIk_14_14_3_3'].iloc[1] < 25 or df_final['STOCHRSIk_14_14_3_3'].iloc[1] > 75:
        message = str(df_final['STOCHRSIk_14_14_3_3'].iloc[1])+" is the value of the stoch RSI signalling entry for gold"
        send_telegram_message(message)
    end_session()


if __name__ == '__main__':
    while True:
        if internet():
            do_the_thing()
        sleep(30)
