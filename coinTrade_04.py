import numpy as np
import time
import pyupbit
import datetime
import math
import sys
import pandas as pd

access = ""          # 본인 값으로 변경
secret = ""          # 본인 값으로 변경
upbit = pyupbit.Upbit(access, secret)

########################################################################################################
#                                       function    - start                                            #
########################################################################################################

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
    bal  = 0
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                # return float(b['balance'])
                bal = float(b['balance'])
            else:
                # return 0
                bal = 0
    return bal

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]
    

def SMA(data, period= 30, colume='Close'):
    return data[colume].rolling(window=period).mean()


def analyze_coin_timedata(ticker, term):
    data = pyupbit.get_ohlcv(ticker, interval=term,count=loop)

    #현구간 수익율 및 벡터값들 계산
    data['wide'] = (data['close'] - data['open'])
    data['rate'] = round((data['close'] - data['open']) / data['open'] * 100, 3)
    data['v_pm'] = np.where( data['rate'] >= 0 , 1 , -1)
    data['v_turn'] = np.where( data['v_pm'] == data['v_pm'].shift(1) , 0 , 1)
    data['v_flow'] = np.where( data['v_turn'] == 1, np.where( data['v_pm'] == data['v_pm'].shift(-1), data['v_pm'] ,0), data['v_pm'] )    

    # rsi 구하기 start 
    data['rsi_up'] = np.where(data.diff(1)["close"] > 0, data.diff(1)["close"] , 0)
    data['rsi_down'] = np.where(data.diff(1)["close"] < 0, data.diff(1)["close"] * (-1) , 0)
    data['rsi_au'] = data['rsi_up'].rolling(14).mean()
    data['rsi_ad'] = data['rsi_down'].rolling(14).mean()
    data['rsi'] = round(data['rsi_au'] / (data['rsi_au'] + data['rsi_ad']) * 100)

    # rsi 구하기 end

    v_strong = []
    v_lowpoint = []
    v_highpoint =[]
    v_flowStart =[]
    v_rsi_real = []
    
    iStrong = 0
    iStrong_re = 0

    iLowpoint = 0
    iLowpoint_re = 0
    iHighpoint = 0
    iHighpoint_re = 0

    iFlowStart = 0

    for i in range(0, loop):

        #--------------------------------------------------------------------------
        # 추가1) 흐름강도구하기
        iStrong = 0
        if data.iloc[i]['v_flow'] == 0 :
            iStrong = iStrong_re
        elif data.iloc[i]['v_flow'] > 0 :
            if iStrong_re > 0 :
                iStrong = iStrong_re + data.iloc[i]['v_flow']
            else:
                iStrong = data.iloc[i]['v_flow']
        else: 
            if  iStrong_re < 0 :
                iStrong = iStrong_re + data.iloc[i]['v_flow']
            else:
                iStrong = data.iloc[i]['v_flow']
        v_strong.append(iStrong)
        iStrong_re = iStrong

        #--------------------------------------------------------------------------
        # 추가2) 저점 및 고점 포인트 마크
        if data.iloc[i]['v_pm'] > 0 :
            iHighpoint = 1
            ilowpoint = 0
        elif data.iloc[i]['v_pm'] < 0 :
            iHighpoint = 0
            ilowpoint = 1
        else:
            iHighpoint = 0
            ilowpoint = 0

        #저점고점포인트는 다음캔들데이터가 이전내역을 점검해서 업데이트함. 
        if i > 0 :
            if iHighpoint > 0 :
                iHighpoint_re = 0            
            if ilowpoint > 0 :
                iLowpoint_re = 0
            v_highpoint.append(iHighpoint_re)
            v_lowpoint.append(iLowpoint_re)
        

        iHighpoint_re = iHighpoint
        iLowpoint_re = ilowpoint
        
        if i == loop - 1 :
            v_highpoint.append(iHighpoint_re)
            v_lowpoint.append(iLowpoint_re)

        #--------------------------------------------------------------------------
        # 추가3) 흐름의 저점 및 고점 전달해주기
        if iStrong_re > 0 and data.iloc[i]['v_flow'] >= 0 :
            #상승구간일때 
            if iStrong_re == 1:
                iFlowStart = data.iloc[i]['open']
            else:
                if data.iloc[i]['open'] < iFlowStart:
                    iFlowStart = data.iloc[i]['open']

        elif iStrong_re < 0 and data.iloc[i]['v_flow'] <= 0 :
            #하락구간일때 
            if iStrong_re == -1:
                iFlowStart = data.iloc[i]['open']
            else:
                if data.iloc[i]['open'] > iFlowStart:
                    iFlowStart = data.iloc[i]['open']

        v_flowStart.append(iFlowStart)

        #--------------------------------------------------------------------------        
        # 추가4) real-rsi 구하기        
        rsi_auu = 0    
        rsi_add = 0
        if  i == 13 :
            rsi_auu = data.iloc[i]['rsi_au']
            rsi_add = data.iloc[i]['rsi_ad']
        elif i > 13 :            
            rsi_auu = (rsi_auu_re * 13 + data.iloc[i]['rsi_up']) / 14 
            rsi_add = (rsi_add_re * 13 + data.iloc[i]['rsi_down']) / 14
        rsi_auu_re = rsi_auu  
        rsi_add_re = rsi_add
        if rsi_auu + rsi_add <= 0 :
            rsi_real = 0
        else :
            rsi_real = round(rsi_auu / (rsi_auu + rsi_add) * 100)
        v_rsi_real.append(rsi_real)
        #---------------------------  for - End ---------------------------------------

    # 데이터프레임에 추가
    data['v_rsi_real'] = v_rsi_real 
    data['v_strong'] = v_strong 
    data['v_low'] = v_lowpoint 
    data['v_high'] = v_highpoint 
    data['v_start'] = v_flowStart 
    data['v_rate'] = round((data['close'] - data['v_start'] ) / data['v_start'] * 100, 3) 
    
    # 계산끝나고 불필요한 데이터프레임 삭제     
    del data['rsi_up']
    del data['rsi_down']
    del data['rsi_au']
    del data['rsi_ad']

    return data
 
 
def check_orderlist():

    # 미체결 주문내역조회 및 취소 ------------------------- start 
    order_waiting_count = 0
    order_coin = upbit.get_order(Control_Coin, state="wait")
    # print(order_coin)

    for item in order_coin:
        if item["side"] == "bid" or item["side"] == "ask":
            order_waiting_count = order_waiting_count + 1

    if order_waiting_count > 0 :
        time.sleep(10)

        order_waiting_count = 0
        # 미체결 주문내역조회 (10초 뒤 재조회 후 존재하면 취소함.)
        order_coin = upbit.get_order(Control_Coin, state="wait")
        for item in order_coin:
            if item["side"] == "bid" or item["side"] == "ask":                    
                # 주문취소
                ret = upbit.cancel_order(item["uuid"])
                # print(ret)
                order_waiting_count = order_waiting_count + 1
        print("미체결건 취소건수 = " + str(order_waiting_count))
    ret = order_waiting_count
    # 미체결 주문내역조회 및 취소 --------------------------- end 
    return order_waiting_count
########################################################################################################
#                                       function    - end                                              #
########################################################################################################


########################################################################################################
##                                      Main -  Start !!                                              ##
########################################################################################################

#-------------------------------------------------------------------------------------------------------
# 기본설정세팅
#-------------------------------------------------------------------------------------------------------
# INPUT 값 받기 
coin = sys.argv[1]

if coin != "":
    Deal_Coin = coin
    print("Deal_Coin : " + Deal_Coin)
else :
    print("Deal_Coin : None!!" )
    exit
    

# 매매코인설정
# Deal_Coin = "ETH"
Control_Coin = "KRW-" + Deal_Coin

# 로그파일생성
file_name = "log-"+Deal_Coin+".txt"
file = open(file_name, 'w')
file.write("autotrade start \n")
file.flush()

#-------------------------------------------------------------------------------------------------------
#  실제매매/테스트매매 구분 ( 1:실제매매, 2:테스트매매)
real_test_gubun = 1
#-------------------------------------------------------------------------------------------------------

krw_base = 0
krw_limit = 300000
print("최대거래금액 = " + str(krw_limit))

# print("매매시간 : "+ str(datetime.datetime.now()))

# 매매 횟수
deal_count = 0
# 추가매수 횟수
deal_add_count = 0  

deal_limit = 10

order_waiting_count = 0
order_waiting_limit = 5

#대상코인 데이터 조회 
loop = 200


item_qty =  0
item_avg_buy_price = 0

bef_buy_check_strong = 0
bef_sell_check_strong = 0

sign_buy_from_type_log = 0
#-------------------------------------------------------------------------------------------------------
# 
#               자동매매 시작 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
while True:
    try:

        now = datetime.datetime.now()
        print("--------------------------------------------------------------------------------")
        print("자동매매 시도시간   : " + str(now))
        print("--------------------------------------------------------------------------------")

        #-------------------------------------------------------------------------------------------------------
        #  미체결내역 조회 및 정리
        #-------------------------------------------------------------------------------------------------------
        # cancel_cnt = check_orderlist()


        #-------------------------------------------------------------------------------------------------------
        #  원화(잔고) 및 매매가능금액 세팅
        #-------------------------------------------------------------------------------------------------------
        krw_base = 0
        # 실제매매시
        if real_test_gubun == 1 : 
            # 보유잔고 조회
            krw_base = get_balance("KRW")
            # 매매최소금액 세팅
            krw_game_money = 10000
            # krw_game_money = krw_base - krw_limit

            # 보유코인 수량
            item_qty =  get_balance(Deal_Coin)
            # 매입평균단가 조회
            item_avg_buy_price = upbit.get_avg_buy_price(Deal_Coin)
        
        # 테스트 매매시
        if real_test_gubun == 2 : 
            # 보유잔고 조회
            krw_base = 1000000            
            # 매매최소금액 세팅
            krw_game_money = 20000

            # 보유코인 수량
            # item_qty
            # 매입평균단가 조회
            # item_avg_buy_price
            price = get_current_price(Control_Coin)

        print("원화(잔고) = " + str(krw_base) + ", 매매가능 원화금액 = " + str(krw_game_money))


        #-------------------------------------------------------------------------------------------------------
        #  매매 캔들 기초데이터 조회 (코인종목, 인터벌)
        #-------------------------------------------------------------------------------------------------------
        df_15 = analyze_coin_timedata(Control_Coin, "minute15")
        print(df_15[loop-10:loop])
        df = analyze_coin_timedata(Control_Coin, "minute1")
        print(df[loop-10:loop])
        print("--------------------------------------------------------------------------------")




        #-------------------------------------------------------------------------------------------------------
        # 현재시세조회, 현재수익률
        #-------------------------------------------------------------------------------------------------------
        #현재시세조회
        price = get_current_price(Control_Coin)
        #전 종가 대비 현재가의 수익률
        price_rate = 0
        if price > 0:
            price_rate = round((price - df.iloc[loop -2]['close']) / price * 100,3)
        #현재 매입잔고의 수익률
        expect_rate = 0
        if item_avg_buy_price > 0 : 
            expect_rate = round(( price  - item_avg_buy_price ) / item_avg_buy_price * 100, 3)

        print("item_qty   : " + str(item_qty) + " , item_avg_buy_price = " + str(item_avg_buy_price) + " , expect_rate = " + str(expect_rate))

        #-------------------------------------------------------------------------------------------------------
        # 매입가능포지션여부, 매도가능포지션여부
        # 1) 잔고금액이 최소매매금액보다 커야 매수포지션을 가짐.
        # 2) 잔고수량의 가격이 5100 이상이면 매도포지션.
        # -------------------------------------------------------------------------------------------------------
        # 1) 현금이 있다면 기본적으로 매수가능 포지션을 가짐.
        if krw_base >= krw_game_money :
            buy_pos = "Y"
            buy_add_pos = "Y"
        else :
            buy_pos = "N"
            buy_add_pos = "N"
            
        # 2) 잔고수량이 있다면 매도 포지션을 우선적으로 가짐.
        if item_avg_buy_price * item_qty > 5100 :
            sell_pos = "Y"
            buy_pos = "N"
        else :
            sell_pos = "N"

        #  잔고수량도 없고 돈도 없으면 게임 아웃!!!
        if sell_pos == "N" and buy_pos == "N" :
            print("돈도없고 코인도 없고.. Game Over!!")
            break


        # 현재 잔고 상태에 따른 매도/매수 포지션 체크    
        print("* sell_pos : [ " + sell_pos + " ], buy_pos : [ " + buy_pos + " ] ************************")

        sign_action = ""        
        sign_action_add = ""
        sign_sell_from_type = 0
        #-------------------------------------------------------------------------------------------------------
        # 매도 전략 적용
        #-------------------------------------------------------------------------------------------------------
        # 매도 전략 1
        if sell_pos == "Y" and  df.iloc[loop -2]['v_rsi_real'] > 60:
            # 1-1: 상승중에 현재시그널 수익률이 이전 상승의 수익률보다 커질때 고점으로 판단. 매도!
            if df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -2]['rate'] < price_rate * (-1) :
                sign_sell_from_type = 11
                sign_sell_rate = 1
                sign_action = "SELL"
        
        # 매도 전략 2: 하락분봉 1개뜨고 그다음 현재시그널이 하락인경우
        if sell_pos == "Y" and  df.iloc[loop -3]['v_rsi_real'] > 60:
            if df.iloc[loop -3]['v_pm'] > 0 and  df.iloc[loop -2]['v_pm'] < 0 and price_rate < -0.1 :            
                sign_sell_from_type = 12
                sign_sell_rate = 1
                sign_action = "SELL"
        
        # 매도 전략 3 : 원화 잔고가 보유코인잔고의 평가금액의 절반정도 되는 시점에는 현금비중조절이 필요함 
        if  sell_pos == "Y" and  krw_base < item_qty * item_avg_buy_price / 2  and expect_rate < 0:
            if  df.iloc[loop -2]['v_rsi_real'] > 40 and expect_rate > -1 :
                sign_sell_from_type = 14
                sign_sell_rate = 0.3
                sign_action = "SELL"
            elif df.iloc[loop -2]['v_rsi_real'] > 40 and  expect_rate > -2 :
                sign_sell_from_type = 14
                sign_sell_rate = 0.4
                sign_action = "SELL"
            elif df.iloc[loop -2]['v_rsi_real'] > 40 and  expect_rate > -3 :
                sign_sell_from_type = 14
                sign_sell_rate = 0.5
                sign_action = "SELL"


        #-------------------------------------------------------------------------------------------------------
        # 추가매수 및 물타기
        if sell_pos == "Y" and  df.iloc[loop -2]['v_rsi_real'] < 40 :
            # 1-1: 상승중에 현재시그널 수익률이 이전 상승의 수익률보다 커질때 고점으로 판단. 매도!
            if df.iloc[loop -3]['v_pm'] < 0 and df.iloc[loop -2]['v_pm'] > 0 and price_rate > 0.1 :
                sign_sell_from_type = 21
                sign_add_rate = 1
                sign_action_add = "BUY"

        elif sell_pos == "Y" and  df.iloc[loop -2]['v_rsi_real'] < 50 and expect_rate < 0 :
            if df.iloc[loop -3]['v_pm'] < 0 and  df.iloc[loop -2]['v_pm'] < 0 and price_rate > 0.1 :
                sign_sell_from_type = 11
                sign_add_rate = 0.8
                sign_action_add = "BUY"


        # # 매도전략 1-1 : 상승중에 하방 1연타 발생 후 현재 시그널대비 수익률이 1퍼이상이면 30프로 매도
        # if sell_pos == "Y" and df.iloc[loop -2]['v_pm'] < 0 and expect_rate > 1 :
        #     sign_sell_from_type = 11
        #     sign_sell_rate = 1
        #     sign_action = "SELL"
            
        # # 매도전략 1-2 : 상승중에 하방 1연타 발생 후 상승강도가 5 이상이면 매도
        # if sell_pos == "Y" and df.iloc[loop -2]['v_pm'] < 0 and df.iloc[loop -4]['v_strong'] > 5 and expect_rate > 0.5 :
        #     sign_sell_from_type = 12
        #     sign_sell_rate = 1
        #     sign_action = "SELL"

        # # 매도전략 1-3 : 상승중에 큰상승이후 큰 하방 발생 시 현재 시그널대비 수익률이 1퍼이상이면 30프로 매도
        # if sell_pos == "Y" and df.iloc[loop -2]['rate'] > 1 and c < -0.5 :
        #     if expect_rate > 0.5 :
        #         sign_sell_from_type = 13
        #         sign_sell_rate = 1
        #         sign_action = "SELL"
        #     else:
        #         sign_sell_from_type = 14
        #         sign_add_rate = 0.6
        #         sign_action_add = "BUY"

        # # 매도전략 2 : 상승중에 하방 2연타 발생시 50% 매도
        # if sell_pos == "Y" and df.iloc[loop -2]['v_pm'] < 0 and df.iloc[loop -3]['v_pm'] < 0 and df.iloc[loop -4]['v_pm'] >= 0: 
        #     if df.iloc[loop -1]['v_rsi_real'] > 60 :
        #         sign_sell_from_type = 31
        #         sign_sell_rate = 1
        #         sign_action = "SELL"
            
        #     else :
        #         if df.iloc[loop -2]['v_rsi_real'] > 50 :                     
        #             sign_sell_from_type = 33
        #             sign_add_rate = 0.0
        #             sign_action_add = "WAIT"
        #         elif df.iloc[loop -2]['v_rsi_real'] > 30 and df.iloc[loop -2]['v_rsi_real'] <= 40 :                     
        #             sign_sell_from_type = 34
        #             sign_add_rate = 0.6
        #             sign_action_add = "BUY"
        #         else:
        #             sign_sell_from_type = 35
        #             sign_add_rate = 0.8
        #             sign_action_add = "BUY"


        # # 매도전략 3 : 상승중에 하방 3연타 발생시 매도
        # if sell_pos == "Y" and df.iloc[loop -2]['v_pm'] < 0 and df.iloc[loop -3]['v_pm'] < 0 and price_rate > 0.3: 
        #     if expect_rate > 0.2 :
        #         sign_sell_from_type = 41
        #         sign_sell_rate = 1
        #         sign_action = "SELL"
        #     elif expect_rate < -2: 
        #         sign_sell_from_type = 42
        #         sign_sell_rate = 1
        #         sign_action = "SELL"
        #     else :
        #         if df.iloc[loop -2]['v_rsi_real'] > 50 :                     
        #             sign_sell_from_type = 43
        #             sign_add_rate = 0.6
        #             sign_action_add = "BUY"
        #         elif df.iloc[loop -2]['v_rsi_real'] > 30 and df.iloc[loop -2]['v_rsi_real'] <= 40 :                     
        #             sign_sell_from_type = 44
        #             sign_add_rate = 0.8
        #             sign_action_add = "BUY"
        #         else:
        #             sign_sell_from_type = 45
        #             sign_add_rate = 1.0
        #             sign_action_add = "BUY"

        # # 매도전략 3 : 상승 5연승 중에 하방 시그널이 크게 잡혔을때
        # if sell_pos == "Y" and df.iloc[loop -3]['v_strong'] > 5 and df.iloc[loop -2]['rate'] > 0 and df.iloc[loop -2]['rate'] * 1.6 < price_rate * (-1): 
        #     sign_sell_from_type = 5
        #     sign_sell_rate = 1
        #     sign_action = "SELL"

        # # 매도전략 3 : 상승 5 ~ 10 연승 중에 하방 시그널이 크게 잡혔을때
        # if sell_pos == "Y" and df.iloc[loop -3]['v_strong'] > 5 and df.iloc[loop -2]['rate'] < 0 : 
        #     if price_rate < 0 and expect_rate >= 0.5 :
        #         sign_sell_from_type = 61
        #         sign_sell_rate = 0.8
        #         sign_action = "SELL"
        #     elif price_rate < 0 and expect_rate < 0.5 and expect_rate > 0.1 :
        #         sign_sell_from_type = 62
        #         sign_sell_rate = 0.6
        #         sign_action = "SELL"
        #     elif price_rate < 0 and expect_rate < 0 and df.iloc[loop -2]['v_rsi_real'] > 50:
        #         sign_sell_from_type = 63
        #         sign_add_rate = 0.0
        #         sign_action_add = "WAIT"            
        #     elif price_rate < 0 and expect_rate < 0 and df.iloc[loop -2]['v_rsi_real'] < 40:
        #         sign_sell_from_type = 64
        #         sign_add_rate = 0.6
        #         sign_action_add = "BUY"
            
        # # 매도전략 4 : 상승 3 연승 이고, rsi 가 65 이상이면 매도
        # if sell_pos == "Y" and df.iloc[loop -3]['v_strong'] > 3 and df.iloc[loop -2]['v_pm'] < 0 and df.iloc[loop -2]['v_rsi_real'] >= 60 : 
        #     if expect_rate > 0.1:
        #         sign_sell_from_type = 71
        #         sign_sell_rate = 1.0
        #         sign_action = "SELL"
        #     else : 
        #         sign_sell_from_type = 72
        #         sign_add_rate = 0.6
        #         sign_action_add = "BUY"

        # # 매도전략 last : 현재 기대수익률이 -1.5% 이하면 전량 매도 (급하강발생)
        # if sell_pos == "Y" and expect_rate < -2 :
        #     sign_sell_from_type = 81
        #     sign_sell_rate = 1
        #     sign_action = "SELL"

        # # 매도전략 last 2: 
        # if sell_pos == "Y" and sign_action != 'SELL' and df.iloc[loop -2]['v_rsi_real'] >= 65 :
        #     sign_sell_from_type = 82
        #     sign_sell_rate = 1
        #     sign_action = "SELL"
            
        # # 추매 추가 전략 1: 
        # if sell_pos == "Y" and sign_action != 'SELL' and df.iloc[loop -2]['v_pm'] < 0 and df.iloc[loop -3]['v_rsi_real'] <= 40 :
        #     if expect_rate < 0 and expect_rate > -2  :
        #         sign_sell_from_type = 91
        #         sign_add_rate = 0.8
        #         sign_action_add = "BUY"


        #-------------------------------------------------------------------------------------------------------
        # 매수 전략 적용
        #-------------------------------------------------------------------------------------------------------
        sign_buy_from_type = 0
        
        # rsi 매수시점
        if buy_pos == "Y" and  df.iloc[loop -3]['v_rsi_real'] < 40:
            if df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -3]['v_pm'] > 0 :
                sign_buy_from_type = 1
                sign_action = "BUY"  
                bef_buy_check_strong = df.iloc[loop -3]['v_strong']
            if df.iloc[loop -3]['v_pm'] <= 0 and df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -2]['rate'] > df.iloc[loop -3]['rate'] * (-1) :
                sign_buy_from_type = 1
                sign_action = "BUY"  
                bef_buy_check_strong = df.iloc[loop -3]['v_strong']


        # 매수전략 1 : 직전 2,3,4 구간이 상승이고, 이전 하방마지막 강도가 -3이하이면 매수 시도
        if df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -3]['v_pm'] > 0 and df.iloc[loop -4]['v_pm'] > 0 and df.iloc[loop -5]['v_strong'] <= -3 :
            sign_buy_from_type = 1
            sign_action = "BUY"    
            # 매수직전 하방의 강도를 남겨둔다.
            bef_buy_check_strong = df.iloc[loop -5]['v_strong']

        # 매수전략 1 :  직전 2,3 구간이 상승이고, 직전 4 구간이 하방인데 강도가 -5이하인경우 매수시도
        if df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -3]['v_pm'] > 0 and df.iloc[loop -4]['v_pm'] < 0 and df.iloc[loop -4]['v_strong'] <= -5 :
            sign_buy_from_type = 2
            sign_action = "BUY"    
            # 매수직전 하방의 강도를 남겨둔다.
            bef_buy_check_strong = df.iloc[loop -4]['v_strong']



        # 매수전략 2 :  직전 2,3,4 구간이 상승이고, 직전 3구간의 상승폭이 7 % 미만인경우 매수 시도
        if df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -3]['v_pm'] > 0 and df.iloc[loop -4]['v_pm'] > 0 and df.iloc[loop -2]['rate'] + df.iloc[loop -3]['rate'] + df.iloc[loop -4]['rate'] < 7 :
            sign_buy_from_type = 3
            sign_action = "BUY"    
            # 매수직전 하방의 강도를 남겨둔다.
            bef_buy_check_strong = df.iloc[loop -4]['v_strong']
            
        # 매수전략 3 : 직전 2,3 구간이 상승이고, rsr 가 30 이하이면 매수시도!
        if df.iloc[loop -1]['v_pm'] > 0 and df.iloc[loop -2]['v_pm'] > 0 and df.iloc[loop -3]['v_rsi_real'] <= 40 :
            sign_buy_from_type = 4
            sign_action = "BUY"    
            # 매수직전 하방의 강도를 남겨둔다.
            bef_buy_check_strong = df.iloc[loop -4]['v_strong']

        # 매수전략 last : 
        # if buy_pos == "Y" and sign_action != 'BUY' and df.iloc[loop -2]['v_rsi_real'] < 40 :
        #     sign_sell_from_type = 82
        #     sign_sell_rate = 1
        #     sign_action = "SELL"

        #-------------------------------------------------------------------------------------------------------
        # 매매 요청 주문
        #-------------------------------------------------------------------------------------------------------
        print("-->> sign_action = [ "+ sign_action +" ]" + ",    sign_action_add = [ "+ sign_action_add +" ]") 
          
          
        #-------------------------------------------------------------------------------------------------------
        # 매도  
        if sell_pos == "Y" and sign_action == "SELL" :
            print("매도~ 주문!!!!!!!!!!!")

            # 테스트매매시
            if real_test_gubun == 2:                    
                # medo_qty = item_qty * sign_sell_rate * 0.9995
                medo_qty = item_qty * sign_sell_rate * 0.9994
                medo_amt = medo_qty * price
                if medo_amt > 5100 :
                    if medo_qty * item_avg_buy_price <= 0 :
                        medo_profit = 0
                    else :
                        medo_profit = round((medo_amt - (medo_qty * item_avg_buy_price)) / (medo_qty * item_avg_buy_price) * 100, 3)
                    # upbit.sell_market_order(Control_Coin, medo_qty)

                    # data = "Time : %s SELL_COIN! : %f , ( buy_price :  %f , rate : %f ) \n" % (str(datetime.datetime.now().time()), price, item_avg_buy_price, round((price - item_avg_buy_price) / item_avg_buy_price, 3))
                    data = "SELL_COIN!(%d-%d) : %f ,  buy_price :  %f , rate : %f  \n" % (sign_buy_from_type_log, sign_sell_from_type, price, item_avg_buy_price, medo_profit)
                    file.write(data)
                    file.flush()

                    item_qty  =  item_qty - medo_qty
                    # item_avg_buy_price = 0  #테스트 매도시 수량만 빠지니깐 평균단가는 변동이 없음.
                    deal_count = deal_count + 1

            # 실제매매시
            if real_test_gubun == 1 :                
                # medo_qty = item_qty * sign_sell_rate * 0.9995
                medo_qty = item_qty * sign_sell_rate * 0.9994
                medo_amt = medo_qty * price
                
                if medo_amt > 5100 :
                    if medo_qty * item_avg_buy_price <= 0 :
                        medo_profit = 0
                    else :
                        medo_profit = round((medo_amt - (medo_qty * item_avg_buy_price)) / (medo_qty * item_avg_buy_price) * 100, 3)
                    upbit.sell_market_order(Control_Coin, medo_qty)
                    
                    data = "[%s] SELL_COIN!(%d-%d) : %f ,  buy_price :  %f , rate : %f  \n" % (str(datetime.datetime.now()),sign_buy_from_type_log, sign_sell_from_type, price, item_avg_buy_price, medo_profit)
                    file.write(data)
                    file.flush()
                    deal_count = deal_count + 1

        #-------------------------------------------------------------------------------------------------------
        # 매수 
        if buy_pos == "Y" and sign_action == "BUY" :
            print("매수타이밍!")    
            
            # 테스트매매시
            if real_test_gubun == 2:
                mesu_amt = krw_game_money * 0.9995

                if mesu_amt > 5100 :
                    # upbit.buy_market_order(Control_Coin, mesu_amt)
                    item_qty  = round(mesu_amt / price, 9) 
                    item_avg_buy_price = price

                    sign_buy_from_type_log = sign_buy_from_type
                    deal_count = deal_count + 1
                
            # 실제매매시
            if real_test_gubun == 1 :   
                mesu_amt = krw_game_money * 0.9995
                
                if mesu_amt > 5100 :
                    upbit.buy_market_order(Control_Coin, mesu_amt)

                    sign_buy_from_type_log = sign_buy_from_type
                    deal_count = deal_count + 1

        #-------------------------------------------------------------------------------------------------------
        # 추가 매수 물타기!!!!!    추가매수할돈 있어야가능함 ㅋㅋ
        if sell_pos == "Y" and sign_action_add == "BUY" and buy_add_pos == "Y" :
            print("물타기 타이밍!")    
            
            # 테스트매매시
            if real_test_gubun == 2:
                mesu_2_amt = krw_game_money * sign_add_rate * 0.9994
                # upbit.buy_market_order(Control_Coin, mesu_2_amt)

                add_qty = round(mesu_2_amt / price, 9) 

                item_avg_buy_price = round((item_avg_buy_price * item_qty + mesu_2_amt) / ( item_qty + add_qty),0)

                item_qty  = item_qty + add_qty
                

                sign_buy_from_type_log = sign_buy_from_type
                deal_add_count = deal_add_count + 1

                data = "[%s][sign_sell_from_type : %d ]  added buying (%d) : buy_price :  %f , mesu_2_amt : %f  \n" % (str(datetime.datetime.now()), sign_sell_from_type, deal_add_count, price, mesu_2_amt)
                file.write(data)
                file.flush()
                
            # 실제매매시
            if real_test_gubun == 1 :   
                mesu_2_amt = krw_game_money * sign_add_rate * 0.9994
                upbit.buy_market_order(Control_Coin, mesu_2_amt)

                sign_buy_from_type_log = sign_buy_from_type
                deal_add_count = deal_add_count + 1
                
                data = "[%s][sign_sell_from_type : %d ]  added buying (%d) : buy_price :  %f , mesu_2_amt : %f  \n" % (str(datetime.datetime.now()), sign_sell_from_type, deal_add_count, price, mesu_2_amt)
                file.write(data)
                file.flush()
        #-------------------------------------------------------------------------------------------------------

        print("item_qty = " + str(item_qty) + "     item_avg_buy_price = " + str(item_avg_buy_price) )
        print("매수 / 매도 실행 횟수 : " + str(deal_count) + " , 추가 매수 실행 횟수 : " + str(deal_add_count))

        if sign_action_add == "BUY" :
            time.sleep(60)
        else :
            time.sleep(10)

        # 테스트용이므로 한번만 실행 후 빠져나온다.
        # deal_count = 500
        if deal_count >= 500 :
            break

    except Exception as e:
        print(e)
        file.close()
        time.sleep(1)


print("autotrade end!!!")
