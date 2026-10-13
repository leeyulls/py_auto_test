import datetime
import platform


def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 45)
    print("🚀 py_auto_test: 파이썬 자동화 & 데이터 분석 시작!")
    print(f"⏰ 실행 시각: {now}")
    print(f"🐍 Python 버전: {platform.python_version()}")
    print("=" * 45)

    # 간단한 매출 데이터 분석 예시
    sales = [
        {"menu": "사워도우", "price": 6500, "qty": 18},
        {"menu": "크루아상", "price": 4500, "qty": 32},
        {"menu": "바게트", "price": 5000, "qty": 21},
    ]

    total_revenue = sum(item["price"] * item["qty"] for item in sales)
    best_seller = max(sales, key=lambda x: x["qty"])

    print("\n📊 [일일 판매 요약 리포트]")
    for item in sales:
        subtotal = item["price"] * item["qty"]
        print(f" - {item['menu']}: {item['qty']}개 판매 (매출 {subtotal:,}원)")

    print("-" * 45)
    print(f"💰 총 매출액: {total_revenue:,}원")
    print(f"🏆 최다 판매 메뉴: {best_seller['menu']} ({best_seller['qty']}개)")


if __name__ == "__main__":
    main()
