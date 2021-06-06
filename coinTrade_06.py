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

#-------------------------------------------------------------------------------------------------------
# 기본설정세팅
#-------------------------------------------------------------------------------------------------------

# 매매코인설정
Deal_Coin = "ETH"

# INPUT 값 받기 
# coin = sys.argv[1]
# Deal_Coin = coin

if Deal_Coin != "":
    print("Deal_Coin : " + Deal_Coin)
else :
    print("Deal_Coin : None!!" )
    exit
Control_Coin = "KRW-" + Deal_Coin

# 로그파일생성
file_name = "log-"+Deal_Coin+".txt"
file = open(file_name, 'w')
file.write("autotrade start \n")
file.flush()

#-------------------------------------------------------------------------------------------------------
#  실제매매/테스트매매 구분 ( 1:실제매매, 2:테스트매매)
real_test_gubun = 2
#-------------------------------------------------------------------------------------------------------


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

    # CCi 구하기
    data['v_cci_m'] = (data['high'] + data['low'] + data['close']) / 3
    data['v_cci_n'] = data['v_cci_m'].rolling(14).mean()
    data['v_cci_d'] = abs(data['v_cci_m'] - data['v_cci_n'])
    data['v_cci_dd'] = data['v_cci_d'].rolling(14).mean()
    data['v_cci'] = round((data['v_cci_m'] - data['v_cci_n']) / (0.015 * data['v_cci_dd']))
    del data['v_cci_m']
    del data['v_cci_n']
    del data['v_cci_d']
    del data['v_cci_dd']

    # MACD 구하기
    googl_macd = get_macd(data['close'], 26, 12, 9)
    data['v_macd'] = googl_macd['macd']
    data['v_signal'] = googl_macd['signal']
    data['v_macd_osc'] = googl_macd['macd_osc']
    
    # googl_macd.to_excel("macd.xlsx")

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
    

def get_macd(price, slow, fast, smooth):
    exp1 = price.ewm(span = fast, adjust = False).mean()
    exp2 = price.ewm(span = slow, adjust = False).mean()
    macd = pd.DataFrame(exp1 - exp2).rename(columns = {'close':'macd'})
    signal = pd.DataFrame(macd.ewm(span = smooth, adjust = False).mean()).rename(columns = {'macd':'signal'})
    macd_osc = pd.DataFrame(macd['macd'] - signal['signal']).rename(columns = {0:'macd_osc'})
    frames =  [macd, signal, macd_osc]
    df = pd.concat(frames, join = 'inner', axis = 1)

    return df
########################################################################################################
#                                       function    - end                                              #
########################################################################################################


########################################################################################################
##                                      Main -  Start !!                                              ##
########################################################################################################

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

sell_pos = ""
buy_pos = ""

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
        df_3 = analyze_coin_timedata(Control_Coin, "minute3")
        # print(df_3[loop-10:loop])
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
        print("price      : " + str(price) + str(expect_rate) + " , price_rate = " + str(price_rate))

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

        krw_jango = 100000000
        Base_Amt = 0
        Base_Qty = 0
        
        T_Buy_Price = 0
        T_Sell_Price = 0
        T_profit_amt = 0
        T_profit_rate = 0

        T_Buy_Time = ""
        T_Sell_Time = ""    

        sign_action_mesu_1 = 0
        sign_action_mesu_2 = 0
        sign_action_medo_1 = 0 
        sign_action_medo_2 = 0 

        #--------------------------------------------------------------------------
        for i in range(0, loop):
            if i < 20 :
                continue            
            if T_Sell_Time != "" and str(df.index[i]) < T_Sell_Time:
                continue

            #--------------------------------------------------------------------------
            # 매수신호 체크
            sign_action_mesu_1 = 0
            sign_action_mesu_time = str(df.index[i])
            if(df.iloc[i]['v_macd'] - df.iloc[i-1]['v_macd'] >= 0) and (df.iloc[i-1]['v_macd'] - df.iloc[i-2]['v_macd'] >= 0) and (df.iloc[i-2]['v_macd'] - df.iloc[i-3]['v_macd'] < 0) and (df.iloc[i-1]['v_macd_osc'] < 0) and (df.iloc[i-1]['v_rsi_real'] < 45)  :
                sign_action_mesu_1 = 1
        
            #--------------------------------------------------------------------------
            # 매도신호 체크
            sign_action_medo_1 = 0
            for j in range(0, loop):
                # 1분봉에서 매수시그널일때 3분봉에서 한번더 체크
                # if T_Buy_Time == "" and sign_action_mesu_1 == 1 and sign_action_mesu_time <= str(df_3.index[j]):
                #     if(df_3.iloc[j]['v_macd'] - df_3.iloc[j-1]['v_macd'] >= 0) :
                #         sign_action_mesu_1 = 1
                #     else:
                #         sign_action_mesu_1 = 0
                #         continue

                if T_Buy_Time != "" and T_Buy_Time < str(df_3.index[j])  :
                    
                    # 잔고가 없다면
                    if Base_Qty == 0 :
                        continue

                    # 매도신호1 : 최초 상승이 꺽일때
                    if ((df_3.iloc[j]['v_macd'] - df_3.iloc[j-1]['v_macd']) <= 0 and df_3.iloc[j]['v_macd_osc'] > 0) or df_3.iloc[i]['v_rsi_real'] > 60:
                        sign_action_medo_1 = 1

                    # 매도신호2 : 상승이 꺽이고 하락으로 완젼히 돌아섰을때
                    if (df_3.iloc[j]['v_macd'] > 0 and df_3.iloc[j]['v_signal'] > 0 and df_3.iloc[j]['v_macd_osc'] < 0  and df_3.iloc[j-1]['v_macd_osc'] >= 0) :
                        sign_action_medo_2 = 1

                    sign_action_medo_2 = 1
                    # 1차매도
                    if Base_Qty > 0 and sign_action_medo_1 == 1 and sign_action_medo_2 == 0:
                        Tr_Qty = Base_Qty / 2
                        T_Sell_Price = df_3.iloc[j]['close']
                        T_Sell_Time = str(df_3.index[j])
                        
                        # 수익률 먼저계산
                        T_profit_amt = round((T_Sell_Price - Base_Upr) * Tr_Qty, 0)
                        T_profit_rate = round(((T_Sell_Price - Base_Upr) / Base_Upr ) * 100, 3)

                        # 잔고조정
                        Base_Qty = Base_Qty - Tr_Qty
                        Base_Amt = Base_Amt - round(Tr_Qty * T_Sell_Price, 0)
                        Base_Upr = Base_Amt / Base_Qty
                        krw_jango = krw_jango + round(Tr_Qty * T_Sell_Price, 0)

                        print("T_Sell_Price : " + str(T_Sell_Price) +  " , T_Sell_Time = " + str(T_Sell_Time) +  " => 1차 매도 " + ": Base_Qty = " + str(Base_Qty) )
                        print("T_profit_amt : " + str(T_profit_amt) +  " , T_profit_rate = " + str(T_profit_rate))

                    # 2차매도
                    elif Base_Qty > 0 and sign_action_medo_1 == 1 and sign_action_medo_2 == 1:
                        Tr_Qty = Base_Qty
                        T_Sell_Price = df_3.iloc[j]['close']
                        T_Sell_Time = str(df_3.index[j])
                        
                        # 수익률 먼저계산
                        T_profit_amt = round((T_Sell_Price - Base_Upr) * Tr_Qty, 0)
                        T_profit_rate = round(((T_Sell_Price - Base_Upr) / Base_Upr ) * 100, 3)
                        
                        # 잔고조정
                        Base_Qty = 0
                        Base_Amt = 0
                        Base_Upr = 0
                        krw_jango = krw_jango + round(Tr_Qty * T_Sell_Price, 0)

                        print("T_Sell_Price : " + str(T_Sell_Price) +  " , T_Sell_Time = " + str(T_Sell_Time) +  " => 2차 매도(전액) " + ": Base_Qty = " + str(Base_Qty) )
                        print("T_profit_amt : " + str(T_profit_amt) +  " , T_profit_rate = " + str(T_profit_rate))

                        T_Buy_Price = 0
                        T_Buy_Time = ""
                        T_profit_amt = 0
                        T_profit_rate = 0


                    
                    # 추가매수신호 체크
                    if(df_3.iloc[j]['v_macd'] - df_3.iloc[j-1]['v_macd'] >= 0) and (df_3.iloc[j-1]['v_macd'] - df_3.iloc[j-2]['v_macd'] >= 0) and (df_3.iloc[j-2]['v_macd'] - df_3.iloc[j-3]['v_macd'] < 0) and (df_3.iloc[j-1]['v_macd_osc'] < 0) and (df_3.iloc[j-1]['v_rsi_real'] < 45)  :
                        # sign_action_mesu_2 = 1
                        if Base_Upr > 0 and (df_3.iloc[j]['close'] - Base_Upr)/Base_Upr*100 < -1 :
                            sign_action_mesu_2 = 1
                        
                    # 물타기사용안함.
                    # sign_action_mesu_2 = 0

                    # 추가매수(물타기)
                    if Base_Qty > 0 and sign_action_mesu_2 > 0:                    
                        Tr_Qty = 1
                        T_Buy_Price = df_3.iloc[j]['close']
                        T_Buy_Time = str(df_3.index[j])

                        Base_Qty = Base_Qty + Tr_Qty
                        Base_Amt = Base_Amt + round(Tr_Qty * T_Buy_Price, 0)
                        Base_Upr = Base_Amt / Base_Qty
                        krw_jango = krw_jango - round(Tr_Qty * T_Buy_Price, 0)

                        print("T_Buy_Price  : " + str(T_Buy_Price) +  " , T_Buy_Time = " + str(T_Buy_Time) +  " <= 추가매수 " + ": Base_Qty = " + str(Base_Qty) )
            
            # 매도신호 체크 - end
            #--------------------------------------------------------------------------

            # 기본매수
            if Base_Qty == 0 and sign_action_mesu_1 > 0:
                Tr_Qty = 1

                T_Buy_Price = df.iloc[i]['open']
                T_Buy_Time = str(df.index[i])

                Base_Qty = Tr_Qty
                Base_Upr = T_Buy_Price
                Base_Amt = round(Tr_Qty * T_Buy_Price, 0)
                krw_jango = krw_jango - round(Tr_Qty * T_Buy_Price, 0)

                print("T_Buy_Price  : " + str(T_Buy_Price) +  " , T_Buy_Time = " + str(T_Buy_Time) +  " <= 기본매수 " + ": Base_Qty = " + str(Base_Qty) )
                
                


        # df.to_excel("df_macd.xlsx")

        # time.sleep(10)
        
        tot_amt = krw_jango + round(Base_Qty * df.iloc[loop -1]['close'], 0)
        print("Result =>  Base_Amt : " + str(Base_Amt) +  " , Base_Qty = " + str(Base_Qty)+  " , krw_jango = " + str(krw_jango))
        print("Result =>  tot_amt  : " + str(tot_amt))

        # 테스트용이므로 한번만 실행 후 빠져나온다.
        deal_count = 500
        if deal_count >= 500 :
            break

    except Exception as e:
        print(e)
        file.close()
        time.sleep(1)


print("autotrade end!!!")
