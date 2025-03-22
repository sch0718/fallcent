import argparse
from instagram_reels import instagram_reels
from coupang_product import coupang_product

def main():
    parser = argparse.ArgumentParser(description='쿠팡 상품 크롤링 및 인스타그램 릴스 조회수 추출 도구')
    parser.add_argument('action', choices=['coupang_product', 'instagram_reels'], 
                        help='실행할 작업 (coupang_product: 쿠팡 크롤링, instagram_reels: 인스타그램 릴스 조회수)')
    
    args = parser.parse_args()
    
    if args.action == 'coupang_product':
        results = coupang_product()
        print(f"쿠팡 상품 크롤링 완료: 총 {len(results) if results else 0}개 결과")
    elif args.action == 'instagram_reels':
        results = instagram_reels()
        print(f"인스타그램 릴스 조회수 추출 완료: 총 {len(results)}개 결과")
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 