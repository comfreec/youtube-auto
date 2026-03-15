"""
쿠팡파트너스 연동 시스템
"""
import re
import requests
from typing import List, Dict, Optional
from loguru import logger
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse
import tempfile


class CoupangPartnersManager:
    """쿠팡파트너스 링크 및 설명 관리"""
    
    def __init__(self):
        self.partner_id = None  # 사용자 파트너 ID
        self.default_disclaimer = "⚠️ 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
        self.use_selenium = True  # Selenium 사용 여부
    
    def set_partner_id(self, partner_id: str):
        """파트너 ID 설정"""
        self.partner_id = partner_id
        logger.info(f"쿠팡파트너스 ID 설정: {partner_id}")
    
    def extract_product_info_from_coupang_url_selenium(self, coupang_url: str) -> Dict:
        """
        Selenium을 사용하여 쿠팡 링크에서 제품 정보 추출 (봇 차단 우회)
        
        Args:
            coupang_url: 쿠팡 제품 링크
            
        Returns:
            제품 정보 딕셔너리
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            import time
            
            logger.info(f"🌐 Selenium으로 쿠팡 제품 정보 추출 중: {coupang_url}")
            
            # Chrome 옵션 설정 (더 강력한 봇 우회)
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')  # 새로운 headless 모드
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 자동화 감지 우회
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # WebDriver 초기화
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                # 페이지 로드
                driver.get(coupang_url)
                
                # 자동화 감지 우회 스크립트 실행
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                time.sleep(8)  # 페이지 로딩 대기 (5초 → 8초)
                
                # Access Denied 체크
                page_source = driver.page_source
                if 'Access Denied' in page_source or 'access denied' in page_source.lower():
                    logger.error("❌ 쿠팡 Access Denied - 봇으로 감지됨")
                    return {
                        'name': '쿠팡 접근 차단 (수동 입력 필요)',
                        'price': '가격 정보 없음',
                        'image_url': None,
                        'rating': '평점 정보 없음',
                        'original_url': coupang_url
                    }
                
                # 페이지 스크롤 (동적 콘텐츠 로드 유도)
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(3)  # 2초 → 3초
                
                # 제품명 추출 (여러 선택자 시도)
                product_name = "제품명을 가져올 수 없습니다"
                name_selectors = [
                    "h1.prod-buy-header__title",
                    ".prod-buy-header__title",
                    "h1[class*='title']",
                    ".product-title",
                    "h1",
                    "[class*='prod-buy'] h1",
                    "[class*='product'] h1"
                ]
                
                for selector in name_selectors:
                    try:
                        name_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        product_name = name_element.text.strip()
                        if product_name and len(product_name) > 3:
                            logger.info(f"제품명 추출 성공 (selector: {selector}): {product_name[:50]}")
                            break
                    except:
                        continue
                
                if product_name == "제품명을 가져올 수 없습니다":
                    logger.warning("모든 제품명 선택자 실패")
                
                # 가격 추출 (여러 선택자 시도)
                product_price = "가격 정보 없음"
                price_selectors = [
                    ".total-price strong",
                    ".price-value",
                    "[class*='price'] strong",
                    ".prod-price__total",
                    ".price",
                    "[class*='total-price']",
                    "[class*='sale-price']"
                ]
                
                for selector in price_selectors:
                    try:
                        price_element = driver.find_element(By.CSS_SELECTOR, selector)
                        product_price = price_element.text.strip()
                        if product_price and ('원' in product_price or ',' in product_price):
                            logger.info(f"가격 추출 성공 (selector: {selector}): {product_price}")
                            break
                    except:
                        continue
                
                if product_price == "가격 정보 없음":
                    logger.warning("모든 가격 선택자 실패")
                
                # 이미지 URL 추출 (여러 선택자 시도)
                image_url = None
                img_selectors = [
                    ".prod-image__detail img",
                    ".prod-image img",
                    ".product-image img",
                    "img[class*='prod']",
                    ".thumb-image img",
                    "[class*='image'] img",
                    "img[src*='coupangcdn']"
                ]
                
                for selector in img_selectors:
                    try:
                        img_element = driver.find_element(By.CSS_SELECTOR, selector)
                        image_url = img_element.get_attribute('src')
                        if not image_url:
                            image_url = img_element.get_attribute('data-src')
                        
                        # 상대 URL을 절대 URL로 변환
                        if image_url:
                            if image_url.startswith('//'):
                                image_url = 'https:' + image_url
                            elif image_url.startswith('/'):
                                image_url = 'https://image.coupangcdn.com' + image_url
                            
                            if 'coupangcdn' in image_url or 'coupang' in image_url:
                                logger.info(f"이미지 URL 추출 성공 (selector: {selector}): {image_url[:80]}")
                                break
                            else:
                                image_url = None
                    except:
                        continue
                
                if not image_url:
                    logger.warning("모든 이미지 선택자 실패")
                
                logger.info(f"✅ Selenium 추출 완료: {product_name}")
                
                return {
                    'name': product_name,
                    'price': product_price,
                    'image_url': image_url,
                    'rating': '⭐ 쿠팡 제품',
                    'original_url': coupang_url
                }
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Selenium 추출 실패: {str(e)}")
            return {
                'name': '제품명을 가져올 수 없습니다',
                'price': '가격 정보 없음',
                'image_url': None,
                'rating': '평점 정보 없음',
                'original_url': coupang_url
            }
    
    def extract_product_info_from_coupang_url(self, coupang_url: str) -> Dict:
        """
        쿠팡 링크에서 제품 정보 추출 (Selenium 우선, 실패 시 기본 방식)
        
        Args:
            coupang_url: 쿠팡 제품 링크 (coupa.ng 또는 coupang.com)
            
        Returns:
            제품 정보 딕셔너리 {'name': str, 'price': str, 'image_url': str, 'rating': str}
        """
        # Selenium 사용 시도
        if self.use_selenium:
            try:
                return self.extract_product_info_from_coupang_url_selenium(coupang_url)
            except Exception as e:
                logger.warning(f"Selenium 실패, 기본 방식 시도: {e}")
        
        # 기본 방식 (requests + BeautifulSoup) - 403 오류 가능성 높음
        try:
            logger.info(f"쿠팡 제품 정보 추출 중: {coupang_url}")
            
            # User-Agent 설정 (쿠팡에서 봇 차단 방지)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # 단축 URL인 경우 실제 URL로 리다이렉트
            if 'coupa.ng' in coupang_url:
                response = requests.get(coupang_url, headers=headers, allow_redirects=True, timeout=10)
                actual_url = response.url
                logger.info(f"실제 URL: {actual_url}")
            else:
                actual_url = coupang_url
            
            # 쿠팡 페이지 크롤링
            response = requests.get(actual_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 제품 정보 추출
            product_info = {
                'name': self._extract_product_name(soup),
                'price': self._extract_product_price(soup),
                'image_url': self._extract_product_image(soup),
                'rating': self._extract_product_rating(soup),
                'original_url': coupang_url
            }
            
            logger.info(f"제품 정보 추출 완료: {product_info['name']}")
            return product_info
            
        except Exception as e:
            logger.error(f"쿠팡 제품 정보 추출 실패: {str(e)}")
            return {
                'name': '제품명을 가져올 수 없습니다',
                'price': '가격 정보 없음',
                'image_url': None,
                'rating': '평점 정보 없음',
                'original_url': coupang_url
            }
    
    def _extract_product_name(self, soup: BeautifulSoup) -> str:
        """제품명 추출"""
        selectors = [
            'h1.prod-buy-header__title',
            '.prod-buy-header__title',
            'h1[class*="title"]',
            '.product-title',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return "제품명을 찾을 수 없습니다"
    
    def _extract_product_price(self, soup: BeautifulSoup) -> str:
        """가격 추출"""
        selectors = [
            '.total-price strong',
            '.price-value',
            '[class*="price"] strong',
            '.prod-price__total',
            '.price'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # 숫자와 원만 추출
                price_match = re.search(r'[\d,]+원', price_text)
                if price_match:
                    return price_match.group()
        
        return "가격 정보 없음"
    
    def _extract_product_image(self, soup: BeautifulSoup) -> Optional[str]:
        """제품 이미지 URL 추출"""
        selectors = [
            '.prod-image__detail img',
            '.prod-image img',
            '.product-image img',
            'img[class*="prod"]',
            '.thumb-image img'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                img_url = element.get('src') or element.get('data-src')
                if img_url:
                    # 상대 URL을 절대 URL로 변환
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://image.coupangcdn.com' + img_url
                    return img_url
        
        return None
    
    def _extract_product_rating(self, soup: BeautifulSoup) -> str:
        """평점 추출"""
        selectors = [
            '.rating-star-num',
            '.prod-rating-score',
            '[class*="rating"] [class*="score"]',
            '.rating'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                rating_text = element.get_text(strip=True)
                # 평점 숫자 추출 (예: 4.5점, ★4.3)
                rating_match = re.search(r'[\d.]+', rating_text)
                if rating_match:
                    return f"⭐ {rating_match.group()}점"
        
        return "평점 정보 없음"
    
    def download_product_image(self, image_url: str, product_name: str) -> Optional[str]:
        """
        제품 이미지 다운로드
        
        Args:
            image_url: 이미지 URL
            product_name: 제품명 (파일명 생성용)
            
        Returns:
            다운로드된 이미지 파일 경로
        """
        if not image_url:
            return None
        
        try:
            logger.info(f"제품 이미지 다운로드 중: {image_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.coupang.com/'
            }
            
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 파일 확장자 추출
            parsed_url = urlparse(image_url)
            file_ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
            
            # 안전한 파일명 생성
            safe_name = re.sub(r'[^\w\s-]', '', product_name)[:50]
            safe_name = re.sub(r'[-\s]+', '_', safe_name)
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_ext, 
                prefix=f"product_{safe_name}_"
            ) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            logger.info(f"제품 이미지 다운로드 완료: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"제품 이미지 다운로드 실패: {str(e)}")
            return None
    
    def create_product_overlay_data(self, coupang_urls: List[str]) -> List[Dict]:
        """
        쿠팡 링크들로부터 오버레이용 제품 데이터 생성
        
        Args:
            coupang_urls: 쿠팡 제품 링크 리스트
            
        Returns:
            오버레이 데이터 리스트 [{'name': str, 'price': str, 'image_path': str, 'url': str}, ...]
        """
        overlay_data = []
        
        for url in coupang_urls:
            logger.info(f"제품 오버레이 데이터 생성 중: {url}")
            
            # 제품 정보 추출
            product_info = self.extract_product_info_from_coupang_url(url)
            
            # 제품 이미지 다운로드
            image_path = None
            if product_info['image_url']:
                image_path = self.download_product_image(
                    product_info['image_url'], 
                    product_info['name']
                )
            
            overlay_item = {
                'name': product_info['name'],
                'price': product_info['price'],
                'rating': product_info['rating'],
                'image_path': image_path,
                'image_url': product_info['image_url'],
                'coupang_url': url,
                'display_text': f"{product_info['name']}\n{product_info['price']}"
            }
            
            overlay_data.append(overlay_item)
            logger.info(f"오버레이 데이터 생성 완료: {product_info['name']}")
        
        return overlay_data
    
    def generate_product_suggestions(self, video_topic: str, video_script: str) -> List[Dict]:
        """
        영상 주제와 대본을 분석하여 관련 제품 추천
        
        Args:
            video_topic: 영상 주제
            video_script: 영상 대본
            
        Returns:
            추천 제품 리스트 [{'category': str, 'keywords': List[str], 'description': str}, ...]
        """
        suggestions = []
        
        # 주제별 제품 카테고리 매핑
        topic_categories = {
            # 건강/운동
            '운동': {'category': '스포츠/헬스', 'keywords': ['운동기구', '헬스용품', '요가매트', '덤벨'], 'description': '홈트레이닝 필수템'},
            '다이어트': {'category': '건강식품', 'keywords': ['단백질보충제', '다이어트식품', '건강간식'], 'description': '다이어트 도우미'},
            '건강': {'category': '건강관리', 'keywords': ['비타민', '건강보조식품', '마사지기'], 'description': '건강 관리 제품'},
            
            # 라이프스타일
            '요리': {'category': '주방용품', 'keywords': ['조리도구', '주방가전', '식재료'], 'description': '요리 필수템'},
            '청소': {'category': '생활용품', 'keywords': ['청소용품', '세제', '정리용품'], 'description': '깔끔한 생활'},
            '인테리어': {'category': '가구/인테리어', 'keywords': ['가구', '조명', '소품'], 'description': '공간 꾸미기'},
            
            # 뷰티/패션
            '뷰티': {'category': '화장품', 'keywords': ['스킨케어', '메이크업', '헤어케어'], 'description': '뷰티 아이템'},
            '패션': {'category': '의류/잡화', 'keywords': ['옷', '신발', '가방', '액세서리'], 'description': '스타일링 아이템'},
            
            # 취미/여가
            '독서': {'category': '도서', 'keywords': ['베스트셀러', '자기계발서', '소설'], 'description': '추천 도서'},
            '여행': {'category': '여행용품', 'keywords': ['캐리어', '여행가방', '여행용품'], 'description': '여행 준비물'},
            
            # 테크/가전
            '테크': {'category': '전자제품', 'keywords': ['스마트폰', '노트북', '이어폰', '충전기'], 'description': '테크 아이템'},
            '게임': {'category': '게임/취미', 'keywords': ['게임기', '게임', '게이밍용품'], 'description': '게이밍 기어'},
        }
        
        # 영상 주제에서 키워드 추출
        for keyword, info in topic_categories.items():
            if keyword in video_topic or keyword in video_script:
                suggestions.append(info)
        
        # 대본에서 구체적인 제품명 추출
        script_products = self._extract_products_from_script(video_script)
        if script_products:
            suggestions.extend(script_products)
        
        return suggestions[:5]  # 최대 5개 추천
    
    def _extract_products_from_script(self, script: str) -> List[Dict]:
        """대본에서 구체적인 제품 언급 추출"""
        products = []
        
        # 일반적인 제품 키워드 패턴
        product_patterns = {
            r'(아이폰|갤럭시|스마트폰)': {'category': '스마트폰', 'keywords': ['아이폰', '갤럭시', '스마트폰'], 'description': '스마트폰'},
            r'(노트북|맥북|컴퓨터)': {'category': '컴퓨터', 'keywords': ['노트북', '맥북', '컴퓨터'], 'description': '컴퓨터/노트북'},
            r'(이어폰|헤드폰|에어팟)': {'category': '오디오', 'keywords': ['이어폰', '헤드폰', '에어팟'], 'description': '오디오 기기'},
            r'(책|도서|베스트셀러)': {'category': '도서', 'keywords': ['책', '도서', '베스트셀러'], 'description': '추천 도서'},
        }
        
        for pattern, info in product_patterns.items():
            if re.search(pattern, script):
                products.append(info)
        
        return products
    
    def generate_description_with_links(
        self, 
        original_description: str, 
        product_links: List[Dict],
        include_disclaimer: bool = True
    ) -> str:
        """
        기존 설명에 쿠팡파트너스 링크 추가
        
        Args:
            original_description: 기존 영상 설명
            product_links: 제품 링크 리스트 [{'name': str, 'url': str, 'description': str}, ...]
            include_disclaimer: 파트너스 고지 포함 여부
            
        Returns:
            쿠팡파트너스 링크가 포함된 설명
        """
        description_parts = [original_description]
        
        if product_links:
            description_parts.append("\n\n🛒 영상 관련 추천 제품:")
            
            for i, link in enumerate(product_links, 1):
                product_line = f"✅ {link['name']}"
                if 'description' in link:
                    product_line += f" - {link['description']}"
                product_line += f"\n👉 {link['url']}"
                description_parts.append(product_line)
        
        if include_disclaimer:
            description_parts.append(f"\n\n{self.default_disclaimer}")
        
        return "\n".join(description_parts)
    
    def generate_cta_suggestions(self, video_topic: str) -> List[str]:
        """
        영상 주제에 맞는 CTA(Call To Action) 제안
        
        Args:
            video_topic: 영상 주제
            
        Returns:
            CTA 문구 리스트
        """
        cta_templates = [
            "🛒 구매링크는 설명란에서 확인하세요!",
            "💡 더 많은 정보는 댓글 고정글을 확인해주세요",
            "🔗 링크는 프로필 바이오에서 확인 가능합니다",
            "📱 쿠팡에서 더 저렴하게 구매하세요",
            "⭐ 리뷰 확인하고 현명한 쇼핑하세요",
        ]
        
        # 주제별 맞춤 CTA
        topic_specific_cta = {
            '리뷰': "🔍 실제 사용 후기와 구매링크는 설명란에!",
            '추천': "✨ 추천 제품 링크는 설명란에서 확인하세요",
            '비교': "⚖️ 가격 비교하고 최저가로 구매하세요",
            '사용법': "📖 제품 구매 전 꼭 설명란 링크 확인!",
        }
        
        ctas = cta_templates.copy()
        
        for keyword, cta in topic_specific_cta.items():
            if keyword in video_topic:
                ctas.insert(0, cta)  # 관련 CTA를 맨 앞에
        
        return ctas[:3]  # 최대 3개 반환


# 전역 인스턴스
_coupang_manager = None

def get_coupang_manager() -> CoupangPartnersManager:
    """싱글톤 쿠팡파트너스 매니저 반환"""
    global _coupang_manager
    if _coupang_manager is None:
        _coupang_manager = CoupangPartnersManager()
    return _coupang_manager