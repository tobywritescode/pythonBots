import requests
import json
import plotly.graph_objects as go
import config_demo
from datetime import date
from dateutil.relativedelta import relativedelta, MO
from time import sleep
import socket

import pandas as pd

pd.set_option('display.max_columns', None)

xst = ""
cst = ""


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
    gbpusd = config_demo.gbpusd_url + last_monday + "T00:00:00&max=500"

    headers = {
        'X-SECURITY-TOKEN': xst,
        'CST': cst
    }
    response = requests.request("GET", gbpusd, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return pd.json_normalize(data["prices"])
    else:
        text = str(response.status_code), " error returned from method: get_k_lines_and_map_to_df" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        get_k_lines_and_map_to_df()


def get_current_price():
    get_current_price_url = "https://demo-api-capital.backend-capital.com/api/v1/prices/GBPUSD?resolution=MINUTE&max=1"

    headers = {
        'X-SECURITY-TOKEN': xst,
        'CST': cst,
        'Content-type': "application/json"
    }
    response = requests.request("GET", get_current_price_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data["prices"][0]["closePrice"]["ask"]
    else:
        text = str(response.status_code), " error returned from method: get_current_price" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        get_current_price()


def make_trade(direction):
    print("App will ", str(direction))
    num = get_current_price()
    stop_percentage = (0.35 / 100) * num
    if direction == "BUY":
        stop_price = num - stop_percentage
    else:
        stop_price = num + stop_percentage
    open_new_position = "https://demo-api-capital.backend-capital.com/api/v1/positions"

    payload = json.dumps({
        "epic": "GBPUSD",
        "direction": direction,
        "size": 100000,
        "guaranteedStop": True,
        "stopLevel": stop_price
    })
    headers = {
        'X-SECURITY-TOKEN': xst,
        'CST': cst,
        'Content-type': "application/json"
    }
    response = requests.request("POST", open_new_position, headers=headers, data=payload)

    if response.status_code == 200:
        data = response.text
        return send_telegram_message(data)
    else:
        text = str(response.status_code), " error returned from method: make_trade" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        make_trade(direction)


def price_below_vwap(dftc):
    return (dftc.iloc[0]['closePrice.bid'] < dftc.iloc[1]['vwap'] and
            dftc.iloc[1]['closePrice.bid'] < dftc.iloc[1]['vwap'])


def price_above_vwap(dftc):
    return (dftc.iloc[0]['closePrice.bid'] > dftc.iloc[1]['vwap'] and
            dftc.iloc[1]['closePrice.bid'] > dftc.iloc[1]['vwap'])


def print_chart(calculate):
    fig = go.Figure(data=[
        go.Candlestick(x=calculate['snapshotTime'],
                       open=calculate['openPrice.bid'],
                       high=calculate['highPrice.bid'],
                       low=calculate['lowPrice.bid'],
                       close=calculate['closePrice.bid']),
        go.Scatter(x=calculate['snapshotTime'], y=calculate['vwap'], line=dict(color='orange', width=1))])
    fig.show()


def get_open_positions():
    headers = {
        'X-SECURITY-TOKEN': xst,
        'CST': cst,
        'Content-type': "application/json"
    }
    open_positions = requests.request("GET", config_demo.positions_url, headers=headers)

    if open_positions.status_code == 200:
        return open_positions.json()
    else:
        text = str(open_positions.status_code), " error returned from method: get_open_positions" + "\ntrying again..."
        print(text)
        send_telegram_message(text)
        get_open_positions()


def no_open_gbpusd_positions():
    positions = get_open_positions()
    for position in positions:
        if len(positions[position]) == 0:
            return True
        if (positions[position][0]['position']['size'] == 100000.0
                and positions[position][0]['market']['instrumentName'] == 'GBP/USD'):
            return False
    return True


def internet():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except socket.error as ex:
        print(ex)
        return False


def price_close_to_vwap(dftc1):
    return (abs(dftc1.iloc[2]['closePrice.bid'] - dftc1.iloc[2]['vwap']) / dftc1.iloc[2][
        'closePrice.bid']) * 100.0 <= 0.05


def print_price_percent_from_vwap(dftc1):
    price = (abs(dftc1.iloc[2]['closePrice.bid'] - dftc1.iloc[2]['vwap']) / dftc1.iloc[2][
        'closePrice.bid']) * 100.0
    print("price is " + str(price) + "% from vwap")


def do_the_thing():
    start_session()

    if no_open_gbpusd_positions():
        print("Looking for entry...")
        df_obj = get_k_lines_and_map_to_df()
        if df_obj.empty:
            df_obj = get_k_lines_and_map_to_df()
        tp = (df_obj['openPrice.bid'] + df_obj['highPrice.bid'] + df_obj['lowPrice.bid'] + df_obj[
            'closePrice.bid']) / 4
        tp = tp * df_obj['lastTradedVolume']
        df_obj['vwap'] = tp.cumsum() / df_obj['lastTradedVolume'].cumsum()
        # print_chart(df_obj)
        df_to_calculate = df_obj.tail(3)
        # print_chart(df_to_calculate)
        if price_close_to_vwap(df_to_calculate) and price_above_vwap(df_to_calculate):
            make_trade("BUY")
        elif price_close_to_vwap(df_to_calculate) and price_below_vwap(df_to_calculate):
            make_trade("SELL")
        else:
            print_price_percent_from_vwap(df_to_calculate)
            print("no trades to make yet")
    else:
        print("GBPUSD trade already open.")

    end_session()


if __name__ == '__main__':
    while True:
        if internet():
            do_the_thing()
        sleep(30)
