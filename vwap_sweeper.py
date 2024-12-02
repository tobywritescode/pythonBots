import json
import socket
import datetime
import plotly.graph_objects as go
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


def get_k_lines_and_map_to_df(the_date):
    last_monday = str(the_date + relativedelta(weekday=MO(-1)))
    print("getting data beginning from " + last_monday)
    gold = config_demo.gbpusd_url + last_monday + "T00:00:00&max=240"

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
        get_k_lines_and_map_to_df(the_date)


def print_chart(calculate):
    fig = go.Figure(data=[
        go.Candlestick(x=calculate['snapshotTime'],
                       open=calculate['openPrice.bid'],
                       high=calculate['highPrice.bid'],
                       low=calculate['lowPrice.bid'],
                       close=calculate['closePrice.bid']),
        go.Scatter(x=calculate['snapshotTime'], y=calculate['vwap'], line=dict(color='orange', width=1))])
    fig.show()


def is_price_close_to_or_has_been_above_vwap(row):
    return ((abs(row['closePrice.bid'] - row['vwap']) / row['closePrice.bid']) * 100.0 <= 0.05
            or (abs(row['lowPrice.bid'] - row['vwap']) / row['lowPrice.bid']) * 100.0 <= 0.05
        or row['lowPrice.bid'] < row['vwap'] < row['highPrice.bid']
        or row['closePrice.bid'] < row['vwap'] < row['openPrice.bid'])


def is_price_close_to_or_has_been_below_vwap(row):
    return ((abs(row['openPrice.bid'] - row['vwap']) / row['openPrice.bid']) * 100.0 <= 0.05
     or row['openPrice.bid'] < row['vwap'] < row['closePrice.bid']
     or (abs(row['highPrice.bid'] - row['vwap']) / row['highPrice.bid']) * 100.0 <= 0.05
     or row['highPrice.bid'] < row['vwap'] < row['lowPrice.bid'])


def collect_results(peak_price, peak_drawdown):
    pass


def do_the_thing():
    sometime = datetime.datetime.strptime('01012022', "%d%m%Y").date()
    for x in range(1):
        start_session()

        df_obj = get_k_lines_and_map_to_df(sometime)
        if df_obj.empty:
            df_obj = get_k_lines_and_map_to_df(sometime)
        tp = (df_obj['openPrice.bid'] + df_obj['highPrice.bid'] + df_obj['lowPrice.bid'] + df_obj[
            'closePrice.bid']) / 4
        tp = tp * df_obj['lastTradedVolume']
        df_obj['vwap'] = tp.cumsum() / df_obj['lastTradedVolume'].cumsum()
        df_to_calculate = df_obj.tail(120)
        print(df_obj)
        sometime += datetime.timedelta(days=1)
        # print(df_to_calculate.iloc[0])
        # if price_close_to_vwap(df_to_calculate) and price_above_vwap(df_to_calculate):
        #     make_trade("BUY")
        # elif price_close_to_vwap(df_to_calculate) and price_below_vwap(df_to_calculate):
        #     make_trade("SELL")
        x = 1
        print_chart(df_to_calculate)
        in_long_trade = False
        in_short_trade = False
        peak_price = 0
        peak_drawdown = 0
        for index, row in df_to_calculate.iterrows():

            if in_long_trade is True:
                if row['closePrice.bid'] > peak_price:
                    peak_price = row['closePrice.bid']
                if row['highPrice.bid'] > peak_price:
                    peak_price = row['highPrice.bid']
                if is_price_close_to_or_has_been_above_vwap(row):
                    collect_results(peak_price, peak_drawdown)
                    in_long_trade = False
                if row['closePrice.bid'] > peak_price:
                    peak_price = row['closePrice.bid']
                if row['highPrice.bid'] > peak_price:
                    peak_price = row['highPrice.bid']

            if in_short_trade is True:
                continue

            if is_price_close_to_or_has_been_above_vwap(row):
                print("a LONG trade should have been made ", row['snapshotTime'])
                in_long_trade = True

            if is_price_close_to_or_has_been_below_vwap(row):
                print("a SHORT trade should have been made ", row['snapshotTime'])
                in_short_trade = True

        end_session()


if __name__ == '__main__':
    # while True:
    #     if internet():
    #         do_the_thing()
    #     sleep(30)
    do_the_thing()
