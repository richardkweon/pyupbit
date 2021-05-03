import time
import pyupbit
import datetime

access = "oiOnPoXqQhTjbERXh2padaW0mmHk3Sy6jR24FXRV"
secret = "dzf0R5aUVhkleD5zmfwYQuLEOIB7cjDf1PmEjIYd"

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")


#시작 원본금액 (원화) 
krw_base = get_balance("KRW") 
print("시작 원본금액 = " + str(krw_base))

krw_safe = krw_base * 0.75
print("안전현금보유액 = " + str(krw_safe))


# 하루 매매 가능 횟수
deal_count = 0
deal_limit = 1

# 자동매매 시작
while True:
    try:
        print("------------------------------------------------------------")
        now = datetime.datetime.now()
        print("자동매매 시도시간   : " + str(now))

        start_time = get_start_time("KRW-BTC")
        print("매매가능 start_time : " + str(start_time))

        end_time = get_start_time("KRW-BTC") + datetime.timedelta(days=1) - datetime.timedelta(minutes=30)
        print("매매가능 end_time   : " + str(end_time))


        # 매수할 item 매수금액설정
        target_price = get_target_price("KRW-BTC", 0.3)
        # 매수할 item 현재가조회
        current_price = get_current_price("KRW-BTC")
        krw = get_balance("KRW")       
        krw_buy = krw  - krw_safe

        if start_time < now < end_time:     
            
            #보유코인이 매입시점대비 5% 이상 수익일경우 매도 
            bal_item_qty = get_balance("BTC")
            bal_item_avg_buy_price = upbit.get_avg_buy_price("BTC")
            
            # 코인보유 여부 확인 
            # 보유 - 목표가 도달시 매도
            # 미보유 - 매매제한횟수 내에서 매수시도
            if bal_item_qty * current_price > 5500 :
                print("보유코인 존재 = " + str(bal_item_qty) + "(KRW:" + str(bal_item_qty * current_price) + ")" )
                deal_count = 1
                if current_price - bal_item_avg_buy_price > bal_item_avg_buy_price * 0.02 :
                    print("매도타이밍!")
                    upbit.sell_market_order("KRW-BTC", bal_item_qty*0.9995)

            else :
                if target_price < current_price:
                    if krw_buy > 5000 and deal_count < deal_limit:
                        print("매수타이밍!")
                        deal_count = deal_count + 1
                        upbit.buy_market_order("KRW-BTC", krw_buy*0.9995)


        else:
            
            #매매시간 이후에는 전량 매도 
            print("장마감 : 전량 매도!")
            bal_item_qty = get_balance("BTC")
            if bal_item_qty * current_price > 5500:
                deal_count = 0
                upbit.sell_market_order("KRW-BTC", bal_item_qty*0.9995)
        time.sleep(60)
    except Exception as e:
        print(e)
        time.sleep(1)


print("autotrade end!!!")