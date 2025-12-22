# jobs/selenium_naukri_scraper.py
import time
import random
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from django.core.cache import cache
import os

class SeleniumNaukriScraper:
    """
    Selenium-based Naukri.com scraper that works with real browser
    """
    
    def __init__(self, headless=True):  # Changed default to True
        """
        Initialize Selenium driver
        
        Args:
            headless: Run browser in background (True) or visible (False)
                      Changed default to True so browser doesn't show
        """
        self.base_url = "https://www.naukri.com"
        self.headless = headless
        self.driver = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Chrome driver with anti-detection features"""
        try:
            print("🚀 Initializing Chrome driver in headless mode...")
            
            # Setup Chrome options
            chrome_options = Options()
            
            
            if self.headless:
                chrome_options.add_argument('--headless=new')  
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
            
            if not self.headless:
                chrome_options.add_argument('--start-maximized')
        
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            

                
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
            
        
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
    
            self.driver.set_page_load_timeout(30)
            
            print("✅ Chrome driver initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Chrome driver: {e}")
            raise
    
    def search_jobs(self, skill, location="", experience="", max_results=20):
        """
        Search jobs on Naukri.com using Selenium
        
        Args:
            skill: Job skill/title to search
            location: Job location
            experience: Years of experience
            max_results: Maximum jobs to return
        """
        print(f"\n{'='*80}")
        print(f"🔍 SEARCHING NAUKRI.COM")
        print(f"{'='*80}")
        print(f"Skill: {skill}")
        print(f"Location: {location}")
        print(f"Max Results: {max_results}")
        
        
        cache_key = f"naukri_sel_{skill}_{location}_{experience}"
        cached_jobs = cache.get(cache_key)
        if cached_jobs:
            print("📦 Returning cached results")
            return cached_jobs[:max_results]
        
        jobs = []
        
        try:
            
            search_url = self._build_search_url(skill, location)
            print(f"🌐 Opening: {search_url}")
            
            
            self.driver.get(search_url)
            
            
            time.sleep(random.uniform(3, 5))
            
            
            if self._check_captcha():
                print("🚫 CAPTCHA detected! Trying to handle...")
                self._handle_captcha()
                time.sleep(5)
            
            
            self._simulate_human_scrolling()
            
            
            page_source = self.driver.page_source
            
            
            with open('selenium_page.html', 'w', encoding='utf-8') as f:
                f.write(page_source[:10000])  
            print("💾 Saved page source to selenium_page.html")
            
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            
            jobs = self._extract_jobs(soup, max_results)
            
            print(f"\n✅ Successfully extracted {len(jobs)} jobs")
            
    
            if jobs:
                cache.set(cache_key, jobs, 7200)  # 2 hours
                print("💾 Results cached")
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            
            
            if len(jobs) == 0:
                print("🔄 Trying fallback extraction method...")
                jobs = self._fallback_extraction(skill, location)
        
        print(f"{'='*80}")
        print(f"📊 SEARCH COMPLETE: {len(jobs)} jobs found")
        print(f"{'='*80}\n")
        
        return jobs[:max_results]
    
    def _build_search_url(self, skill, location):
        """Build Naukri search URL"""
        skill_clean = skill.strip().lower().replace(' ', '-')
        
        if location and location.strip():
            location_clean = location.strip().lower().replace(' ', '-')
            return f"{self.base_url}/{skill_clean}-jobs-in-{location_clean}"
        else:
            return f"{self.base_url}/{skill_clean}-jobs"
    
    def _check_captcha(self):
        """Check if CAPTCHA is present"""
        try:
            page_text = self.driver.page_source.lower()
            captcha_indicators = [
                'captcha', 'security check', 'robot', 'not a robot',
                'recaptcha', 'verify you are human', 'cloudflare'
            ]
            
            for indicator in captcha_indicators:
                if indicator in page_text:
                    return True
            
            
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                src = iframe.get_attribute('src') or ''
                if 'recaptcha' in src.lower() or 'captcha' in src.lower():
                    return True
            
            return False
            
        except:
            return False
    
    def _handle_captcha(self):
        """Try to handle CAPTCHA"""
        try:
            print("🔄 Attempting to handle CAPTCHA...")
            
            
            self.driver.refresh()
            time.sleep(5)
            
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            
            new_agent = random.choice(user_agents)
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": new_agent
            })
            
            
            self.driver.delete_all_cookies()
            self.driver.refresh()
            time.sleep(5)
            
            print("✅ CAPTCHA handling attempted")
            
        except Exception as e:
            print(f"⚠️ CAPTCHA handling failed: {e}")
    
    def _simulate_human_scrolling(self):
        """Simulate human-like scrolling behavior"""
        print("🔄 Simulating human scrolling...")
        
        try:
            
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            
            
            current_position = 0
            scroll_increment = random.randint(300, 800)
            
            while current_position < total_height:
            
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                
                
                time.sleep(random.uniform(0.5, 2.0))
                
                
                current_position += scroll_increment
            
        
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
            print("✅ Scrolling simulation complete")
            
        except Exception as e:
            print(f"⚠️ Scrolling simulation failed: {e}")
    
    def _extract_jobs(self, soup, max_results):
        """Extract job listings from HTML"""
        jobs = []
        
        print("🔍 Extracting job listings...")
        
        
        job_selectors = [
            
            'article.jobTuple',
            'article[class*="jobTuple"]',
            'div[class*="jobTuple"]',
            '.srp-jobtuple-wrapper',
            '.jobTuple',
            
        
            '[data-job-id]',
            '.job-list',
            '.job-card',
            '.job-item',
            '.list',
            
            
            '.row',
            '.job-segment',
            '.srp-tuple',
        ]
        
        for selector in job_selectors:
            job_elements = soup.select(selector)
            print(f"  Trying selector '{selector}': found {len(job_elements)} elements")
            
            if job_elements and len(job_elements) > 0:
                print(f"  ✅ Using selector: {selector}")
                
                for i, element in enumerate(job_elements[:max_results]):
                    try:
                        job = self._parse_job_element(element)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        print(f"    ✗ Failed to parse job {i+1}: {e}")
                        continue
                
            
                if jobs:
                    break
        
    
        if not jobs:
            print("🔄 No jobs found with selectors, trying manual extraction...")
            jobs = self._manual_extraction(soup, max_results)
        
        return jobs
    
    def _parse_job_element(self, element):
        """Parse individual job element"""
        try:
            job = {
                'title': 'Not specified',
                'company': 'Not specified',
                'location': 'Not specified',
                'experience': 'Not specified',
                'salary': 'Not disclosed',
                'description': '',
                'skills': [],
                'posted_date': 'Recently',
                'url': '',
                'source': 'Naukri.com'
            }
            
            
            title_selectors = [
                '.title', 
                'a.title',
                '.job-title',
                'h2 a',
                'a[class*="title"]',
                '.srp-title',
                '.jobTitle'
            ]
            
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem and title_elem.text.strip():
                    job['title'] = title_elem.text.strip()
                    
                    
                    if title_elem.name == 'a':
                        url = title_elem.get('href', '')
                        if url:
                            if not url.startswith('http'):
                                url = self.base_url + url if url.startswith('/') else self.base_url + '/' + url
                            job['url'] = url
                    break
            
            
            company_selectors = [
                '.subTitle',
                '.comp-name',
                '.company-name',
                'a[class*="subTitle"]',
                '.comp-dtls',
                '.company'
            ]
            
            for selector in company_selectors:
                company_elem = element.select_one(selector)
                if company_elem and company_elem.text.strip():
                    job['company'] = company_elem.text.strip()
                    break
            
        
            location_selectors = [
                '.locWdth',
                '.location',
                '.loc',
                '.city',
                '[class*="loc"]'
            ]
            
            for selector in location_selectors:
                loc_elem = element.select_one(selector)
                if loc_elem and loc_elem.text.strip():
                    job['location'] = loc_elem.text.strip()
                    break
            
            
            exp_selectors = [
                '.expwdth',
                '.experience',
                '.exp',
                '[class*="exp"]',
                '.yrs'
            ]
            
            for selector in exp_selectors:
                exp_elem = element.select_one(selector)
                if exp_elem and exp_elem.text.strip():
                    job['experience'] = exp_elem.text.strip()
                    break
            
            
            salary_selectors = [
                '.sal',
                '.salary',
                '[class*="sal"]',
                '.ctc'
            ]
            
            for selector in salary_selectors:
                sal_elem = element.select_one(selector)
                if sal_elem and sal_elem.text.strip():
                    job['salary'] = sal_elem.text.strip()
                    break
            
            
            desc_selectors = [
                '.job-description',
                '.desc',
                '.description',
                '.job-desc'
            ]
            
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem and desc_elem.text.strip():
                    desc = desc_elem.text.strip()
                    job['description'] = desc[:200] + '...' if len(desc) > 200 else desc
                    break
            
            
            skills_selectors = [
                '.tags',
                '.skills',
                '.key-skills',
                '[class*="skill"]'
            ]
            
            for selector in skills_selectors:
                skills_elem = element.select_one(selector)
                if skills_elem:
                    skill_tags = skills_elem.find_all(['li', 'span', 'div'])
                    skills = [tag.text.strip() for tag in skill_tags if tag.text.strip()]
                    if skills:
                        job['skills'] = skills
                    break
            
            
            date_selectors = [
                '.fleft.postedDate',
                '.posted-date',
                '.date',
                '[class*="date"]'
            ]
            
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem and date_elem.text.strip():
                    job['posted_date'] = date_elem.text.strip()
                    break
            
            
            if not job['url']:
                job['url'] = f"{self.base_url}/job-details?title={quote_plus(job['title'])}"
            
            return job
            
        except Exception as e:
            print(f"❌ Error parsing job element: {e}")
            return None
    
    def _manual_extraction(self, soup, max_results):
        """Manual extraction when selectors fail"""
        jobs = []
        
        print("🔄 Attempting manual extraction from page...")
        
        
        all_links = soup.find_all('a', href=True)
        job_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = link.text.strip()
            
            
            if ('job' in href.lower() or 'jobs' in href.lower() or 
                'view' in href.lower() or 'listing' in href.lower()):
                
                
                if text and len(text) > 10 and len(text) < 100:
                    job_links.append({
                        'href': href,
                        'title': text,
                        'parent': link.parent
                    })
        
        print(f"  Found {len(job_links)} potential job links")
        
        
        for link_info in job_links[:max_results]:
            try:
                job = {
                    'title': link_info['title'],
                    'company': 'Not specified',
                    'location': 'Not specified',
                    'experience': 'Not specified',
                    'salary': 'Not disclosed',
                    'description': '',
                    'skills': [],
                    'posted_date': 'Recently',
                    'url': link_info['href'],
                    'source': 'Naukri.com'
                }
                
                
                parent = link_info['parent']
                if parent:
                    
                    for elem in parent.find_all(['div', 'span', 'p']):
                        text = elem.text.strip()
                        if text and len(text) < 50 and 'company' not in text.lower():
                            job['company'] = text
                            break
                
                
                if job['url'] and not job['url'].startswith('http'):
                    job['url'] = self.base_url + (job['url'] if job['url'].startswith('/') else '/' + job['url'])
                
                jobs.append(job)
                
            except Exception as e:
                print(f"    ✗ Failed to process link: {e}")
                continue
        
        return jobs
    
    def _fallback_extraction(self, skill, location):
        """Fallback method when everything else fails"""
        print("🔄 Using fallback extraction (sample data)...")
        
        
        sample_titles = [
            f'{skill.title()} Developer',
            f'Senior {skill.title()} Engineer',
            f'{skill.title()} Specialist',
            f'Junior {skill.title()} Developer',
            f'Full Stack {skill.title()} Developer'
        ]
        
        sample_companies = [
            'Tech Solutions Inc.',
            'Software Corp',
            'Digital Innovations Ltd.',
            'Global Tech Services',
            'Startup Ventures'
        ]
        
        sample_locations = [
            location.title() if location else 'Bangalore',
            location.title() if location else 'Bangalore',
            location.title() if location else 'Bangalore',
            'Remote',
            f'{location.title() if location else "Bangalore"} / Hybrid'
        ]
        
        sample_jobs = []
        for i in range(min(5, len(sample_titles))):
            job = {
                'title': sample_titles[i],
                'company': sample_companies[i],
                'location': sample_locations[i],
                'experience': f'{i+1}-{i+4} years',
                'salary': f'₹{3+i},00,000 - ₹{6+i},00,000 PA',
                'description': f'Looking for {skill} professional with relevant experience. Good problem-solving skills required.',
                'skills': [skill, 'Python', 'Django', 'REST API', 'MySQL'],
                'posted_date': f'{i+1} day(s) ago',
                'url': f'{self.base_url}/job-listing-{i+1}',
                'source': 'Naukri.com (Sample)'
            }
            sample_jobs.append(job)
        
        return sample_jobs
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            try:
                print("👋 Closing browser...")
                self.driver.quit()
                print("✅ Browser closed")
            except:
                pass
    
    def __del__(self):
        """Destructor to ensure browser is closed"""
        self.close()


def test_selenium_scraper():
    """Test the selenium scraper"""
    print("🧪 Testing Selenium scraper...")
    
    
    scraper = SeleniumNaukriScraper(headless=True)
    
    try:
        jobs = scraper.search_jobs(
            skill='python developer',
            location='bangalore',
            max_results=10
        )
        
        print(f"\n📋 RESULTS SUMMARY:")
        print(f"Total jobs found: {len(jobs)}")
        
        for i, job in enumerate(jobs, 1):
            print(f"\n{i}. {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Location: {job['location']}")
            print(f"   Experience: {job['experience']}")
            print(f"   Salary: {job['salary']}")
            print(f"   URL: {job['url']}")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    test_selenium_scraper()