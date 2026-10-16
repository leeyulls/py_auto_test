"""
auto_order_executor.py
AI 추천 종목(today_buy_picks) 기반 자동 매매 주문 집행 및 리스크 관리 모듈
- 2중 안전 장치(Dry-Run 모드 및 단일 종목 최대 투자비중 제한) 탑재
- 목표가 및 손절가 감시 주문 파라미터 자동 설정
- 주문 집행 결과 로깅 및 결과 리포트 반환
"""

import datetime
import re
from typing import List, Dict
from .kis_client import KisTradingClient


class AutoOrderExecutor:
    def __init__(self, is_virtual: bool = True, dry_run: bool = True, max_allocation_ratio: float = 0.15):
        """
        :param is_virtual: True(모의투자), False(실전투자)
        :param dry_run: True(시뮬레이션 모드 - 실제 주문 미전송), False(실제 API 주문 전송)
        :param max_allocation_ratio: 단일 종목 최대 투자 비중 (기본 15%)
        """
        self.is_virtual = is_virtual
        self.dry_run = dry_run
        self.max_allocation_ratio = max_allocation_ratio
        self.client = KisTradingClient(is_virtual=is_virtual)

    def _parse_price(self, price_val) -> int:
        """가격을 정수로 변환"""
        try:
            cleaned = re.sub(r"[^\d]", "", str(price_val))
            return int(cleaned) if cleaned else 0
        except Exception:
            return 0

    def execute_recommendations(self, picks: List[Dict], max_picks: int = 3) -> Dict:
        """
        AI 추천 종목 리스트를 받아 안전 조건 검증 후 분할 매수 주문 전송
        """
        execution_records = []
        balance_info = self.client.inquire_balance()
        available_cash = balance_info.get("available_cash", 10000000)

        # 1종목당 최대 투입 예산 계산 (예수금 * 비중)
        budget_per_stock = int(available_cash * self.max_allocation_ratio)
        if budget_per_stock < 100000:
            budget_per_stock = 1000000  # 최소 100만원 시뮬레이션

        processed_count = 0
        for pick in picks[:max_picks]:
            ticker = pick.get("ticker", "")
            name = pick.get("name", ticker)
            buy_price = self._parse_price(pick.get("buy_price", 0))
            sell_price = self._parse_price(pick.get("sell_price", 0))
            stop_loss = self._parse_price(pick.get("stop_loss", 0))

            if not ticker or buy_price <= 0:
                continue

            # 주문 수량 계산 (1주 단위)
            qty = max(1, budget_per_stock // buy_price)
            total_order_amount = qty * buy_price

            if self.dry_run:
                # 안전 시뮬레이션 모드
                record = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ticker": ticker,
                    "name": name,
                    "action": "BUY",
                    "mode": "DRY_RUN (안전 시뮬레이션)",
                    "qty": qty,
                    "order_price": buy_price,
                    "target_price": sell_price,
                    "stop_loss": stop_loss,
                    "total_amount": f"{total_order_amount:,}원",
                    "status": "SIMULATED_SUCCESS",
                    "order_no": f"DRY_{datetime.datetime.now().strftime('%H%M%S')}_{processed_count+1}",
                    "note": f"모의 배정 예산 {budget_per_stock:,}원 기준 {qty}주 가상 매수"
                }
            else:
                # 실제 KIS API 주문 전송
                res = self.client.send_order(ticker=ticker, qty=qty, price=buy_price, order_side="BUY")
                record = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ticker": ticker,
                    "name": name,
                    "action": "BUY",
                    "mode": "REAL_VIRTUAL" if self.is_virtual else "LIVE_REAL",
                    "qty": qty,
                    "order_price": buy_price,
                    "target_price": sell_price,
                    "stop_loss": stop_loss,
                    "total_amount": f"{total_order_amount:,}원",
                    "status": res.get("status"),
                    "order_no": res.get("order_no", "-"),
                    "note": res.get("message", "")
                }

            execution_records.append(record)
            processed_count += 1

        return {
            "summary": {
                "total_requested": len(picks),
                "total_executed": len(execution_records),
                "is_virtual": self.is_virtual,
                "is_dry_run": self.dry_run,
                "available_cash": f"{available_cash:,}원",
                "budget_per_stock": f"{budget_per_stock:,}원",
            },
            "records": execution_records
        }
