import argparse
from v1.instagram_reels import instagram_reels as instagram_reels_v1
from v1.coupang_product import coupang_product as coupang_product_v1
from v2.instagram_reels import instagram_reels as instagram_reels_v2
from v2.coupang_product import coupang_product as coupang_product_v2

def main():
    parser = argparse.ArgumentParser(description='쿠팡 상품 크롤링 및 인스타그램 릴스 조회수 추출 도구')
    parser.add_argument('action', choices=['coupang_product', 'instagram_reels'], 
                        help='실행할 작업 (coupang_product: 쿠팡 크롤링, instagram_reels: 인스타그램 릴스 조회수)')
    parser.add_argument('--version', choices=['v1', 'v2'], default='v2',
                        help='사용할 버전(v1: 기존 버전, v2: 새로운 버전, 기본값: v2)')
    
    args = parser.parse_args()
    
    if args.action == 'coupang_product':
        if args.version == 'v1':
            results = coupang_product_v1()
            print(f"쿠팡 상품 크롤링 완료 (v1): 총 {len(results) if results else 0}개 결과")
        else:
            results = coupang_product_v2()
            print(f"쿠팡 상품 크롤링 완료 (v2): 총 {len(results) if results else 0}개 결과")
    elif args.action == 'instagram_reels':
        if args.version == 'v1':
            results = instagram_reels_v1()
            print(f"인스타그램 릴스 조회수 추출 완료 (v1): 총 {len(results)}개 결과")
        else:
            results = instagram_reels_v2()
            print(f"인스타그램 릴스 조회수 추출 완료 (v2): 총 {len(results) if results else 0}개 결과")
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 