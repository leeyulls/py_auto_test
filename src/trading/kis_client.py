"""
kis_client.py
한국투자증권(KIS Developers) Open API 통신 클라이언트
- 모의투자(Virtual) 및 실전투자(Real) 엔드포인트 자동 분기 지원
- OAuth 2.0 Access Token 발급 및 자동 갱신
- 국내주식 잔고 조회, 주식 현재가 조회, 현물 매수/매도 주문 전송
- API 미등록 시 모의 시뮬레이션(Virtual Sandbox) 안전 폴백 제공
"""

import os
import json
import datetime
import requests


class KisTradingClient:
    def __init__(self, is_virtual: bool = True):
        """
        :param is_virtual: True일 경우 모의투자 엔드포인트, False일 경우 실전투자 엔드포인트 사용
        """
        self.is_virtual = is_virtual
        self.app_key = os.environ.get("KIS_APP_KEY", "").strip()
        self.app_secret = os.environ.get("KIS_APP_SECRET", "").strip()
        self.account_no = os.environ.get("KIS_ACCOUNT_NO", "").strip()  # 앞 8자리
        self.account_prdt_cd = os.environ.get("KIS_ACCOUNT_PRDT_CD", "01").strip()  # 뒤 2자리 (보통 01)

        # 도메인 분기
        if self.is_virtual:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"

        self.access_token = None
        self.token_expired_at = None

    def is_configured(self) -> bool:
        """API 연동 필수 환경변수 등록 여부 확인"""
        return bool(self.app_key and self.app_secret and self.account_no)

    def get_access_token(self) -> str:
        """KIS OAuth 2.0 Access Token 발급 (유효시간 내 재사용)"""
        if not self.is_configured():
            return "SIMULATED_TOKEN"

        now = datetime.datetime.now()
        if self.access_token and self.token_expired_at and now < self.token_expired_at:
            return self.access_token

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            if res.status_code == 200:
                data = res.json()
                self.access_token = data.get("access_token")
                expires_in = int(data.get("expires_in", 86400))
                self.token_expired_at = now + datetime.timedelta(seconds=expires_in - 300)
                return self.access_token
            else:
                print(f"[경고] KIS 토큰 발급 실패 ({res.status_code}): {res.text}")
                return "SIMULATED_TOKEN"
        except Exception as e:
            print(f"[오류] KIS 토큰 요청 통신 에러: {e}")
            return "SIMULATED_TOKEN"

    def get_headers(self, tr_id: str) -> dict:
        """공통 헤더 생성"""
        token = self.get_access_token()
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def inquire_balance(self) -> dict:
        """
        국내주식 잔고 및 예수금 총액 조회
        - tr_id: TTTC8434R (실전) / VTTC8434R (모의)
        """
        if not self.is_configured():
            # 시뮬레이션 가상 예수금 반환
            return {
                "status": "SIMULATED",
                "total_deposit": 10000000,       # 1,000만원 가상 시드
                "available_cash": 10000000,
                "holdings": [],
                "message": "KIS API 미설정 상태 - 가상 시뮬레이션 계좌(1,000만원 시드) 운용 중"
            }

        tr_id = "VTTC8434R" if self.is_virtual else "TTTC8434R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self.get_headers(tr_id)
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                output2 = data.get("output2", [{}])[0]
                tot_evlu_amt = int(output2.get("tot_evlu_amt", 0))
                prvs_rcdl_excc_amt = int(output2.get("prvs_rcdl_excc_amt", 0))
                holdings = []
                for item in data.get("output1", []):
                    qty = int(item.get("hldg_qty", 0))
                    if qty > 0:
                        holdings.append({
                            "ticker": item.get("pdno"),
                            "name": item.get("prdt_name"),
                            "qty": qty,
                            "buy_price": float(item.get("pchs_avg_pric", 0)),
                            "cur_price": float(item.get("prpr", 0)),
                            "profit_rate": float(item.get("evlu_pfls_rt", 0)),
                        })
                return {
                    "status": "SUCCESS",
                    "total_deposit": tot_evlu_amt,
                    "available_cash": prvs_rcdl_excc_amt,
                    "holdings": holdings,
                    "message": "계좌 잔고 정상 조회"
                }
            else:
                return {"status": "ERROR", "message": f"잔고 조회 오류 ({res.status_code}): {res.text}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"잔고 조회 예외: {e}"}

    def fetch_price(self, ticker: str) -> dict:
        """
        국내주식 현재가 및 호가 조회
        - tr_id: FHKST01010100
        """
        clean_ticker = ticker.split(".")[0].zfill(6)
        if not self.is_configured():
            return {
                "status": "SIMULATED",
                "ticker": clean_ticker,
                "cur_price": 50000,
                "change_rate": 0.0
            }

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self.get_headers("FHKST01010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": clean_ticker
        }

        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                output = data.get("output", {})
                return {
                    "status": "SUCCESS",
                    "ticker": clean_ticker,
                    "cur_price": int(output.get("stck_prpr", 0)),
                    "change_rate": float(output.get("prdy_ctrt", 0.0)),
                    "high": int(output.get("stck_hgpr", 0)),
                    "low": int(output.get("stck_lwpr", 0)),
                    "volume": int(output.get("acml_vol", 0))
                }
            else:
                return {"status": "ERROR", "ticker": clean_ticker, "message": f"현재가 조회 실패 ({res.status_code})"}
        except Exception as e:
            return {"status": "ERROR", "ticker": clean_ticker, "message": str(e)}

    def send_order(self, ticker: str, qty: int, price: int, order_side: str = "BUY", order_type: str = "00") -> dict:
        """
        주식 현물 주문 전송
        - order_side: 'BUY'(매수) 또는 'SELL'(매도)
        - order_type: '00'(지정가), '01'(시장가)
        - tr_id: VTTC0802U (모의매수) / VTTC0801U (모의매도) / TTTC0802U (실전매수) / TTTC0801U (실전매도)
        """
        clean_ticker = ticker.split(".")[0].zfill(6)
        
        if not self.is_configured():
            # 시뮬레이션 가상 체결
            return {
                "status": "SIMULATED_ORDER",
                "ticker": clean_ticker,
                "order_side": order_side,
                "qty": qty,
                "price": price,
                "order_no": f"SIM_{datetime.datetime.now().strftime('%H%M%S')}",
                "message": f"[시뮬레이션 체결] {clean_ticker} {qty}주 @ {price:,}원 ({order_side}) 주문 정상 접수"
            }

        if order_side.upper() == "BUY":
            tr_id = "VTTC0802U" if self.is_virtual else "TTTC0802U"
        else:
            tr_id = "VTTC0801U" if self.is_virtual else "TTTC0801U"

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = self.get_headers(tr_id)
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_prdt_cd,
            "PDNO": clean_ticker,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price) if order_type == "00" else "0",
        }

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("rt_cd") == "0":
                    order_no = data.get("output", {}).get("ODNO", "")
                    return {
                        "status": "SUCCESS",
                        "ticker": clean_ticker,
                        "order_side": order_side,
                        "qty": qty,
                        "price": price,
                        "order_no": order_no,
                        "message": f"주문 완료 (주문번호: {order_no})"
                    }
                else:
                    return {"status": "REJECTED", "message": data.get("msg1", "주문 거부")}
            else:
                return {"status": "ERROR", "message": f"주문 실패 ({res.status_code}): {res.text}"}
        except Exception as e:
            return {"status": "ERROR", "message": f"주문 통신 예외: {e}"}
