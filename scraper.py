import requests
import json
import re
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime
from utils import extract_otp_from_text, clean_phone_number, clean_service_name

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

class IVASMSScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://www.ivasms.com"
        self.is_logged_in = False
        self._update_headers()

    def _update_headers(self):
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        })

    def _delay(self):
        time.sleep(random.uniform(1, 2))

    def load_cookies_from_file(self, cookie_file='cookies.json'):
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            for cookie in cookies:
                self.session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', '.ivasms.com'),
                    path=cookie.get('path', '/')
                )
            print(f"✅ Loaded {len(cookies)} cookies from {cookie_file}")
            self.is_logged_in = True
            return True
        except FileNotFoundError:
            print(f"⚠️ File {cookie_file} tidak ditemukan.")
            return False
        except Exception as e:
            print(f"❌ Gagal load cookie: {e}")
            return False

    def login(self):
        return self.load_cookies_from_file()

    def fetch_messages(self):
        if not self.is_logged_in:
            return []
        messages = []
        for path in ['/dashboard', '/', '/messages']:
            try:
                self._update_headers()
                self._delay()
                url = f"{self.base_url}{path}"
                resp = self.session.get(url)
                if resp.status_code == 200:
                    text = resp.text
                    otps = re.findall(r'\b\d{4,6}\b', text)
                    for otp in set(otps[:5]):
                        messages.append({
                            'otp': otp,
                            'phone': clean_phone_number(self._extract_phone(text)),
                            'service': clean_service_name(self._extract_service(text)),
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'raw_message': text[:200]
                        })
                    if messages:
                        break
            except:
                continue
        return messages

    def _extract_phone(self, text):
        m = re.search(r'(\+?\d{10,15})', text)
        return m.group(1) if m else "Unknown"

    def _extract_service(self, text):
        services = ['facebook','google','whatsapp','telegram','instagram','twitter','linkedin','tiktok']
        for s in services:
            if s in text.lower():
                return s
        return "Unknown"

    def fetch_profile_info(self):
        if not self.is_logged_in:
            return self._dummy_profile()
        try:
            # Pertama, coba akses halaman yang paling mungkin berisi data
            # Biasanya dashboard atau account
            for path in ['/dashboard', '/account', '/profile']:
                self._update_headers()
                self._delay()
                resp = self.session.get(f"{self.base_url}{path}")
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Cari saldo: cari angka yang dekat dengan kata "saldo", "balance", atau format mata uang
                    balance = None
                    # Pola 1: "Saldo: Rp 10.000"
                    match = re.search(r'(?:saldo|balance)[:\s]*([\d.,]+)', text, re.I)
                    if match:
                        balance = match.group(1)
                    else:
                        # Pola 2: angka dengan titik/koma diikuti "IDR" atau "Rp"
                        match = re.search(r'([\d.,]+)\s*(?:Rp|IDR)', text)
                        if match:
                            balance = match.group(1)
                        else:
                            # Pola 3: angka yang muncul di area tertentu (misal card)
                            numbers = re.findall(r'\b[\d.,]+\b', text)
                            if numbers:
                                # Ambil angka yang paling panjang atau yang kelihatan sebagai nominal
                                for num in numbers:
                                    if ',' in num or '.' in num:
                                        balance = num
                                        break
                                if not balance and numbers:
                                    balance = numbers[0]
                    
                    # Total SMS: cari kata sms diikuti angka
                    total_sms = None
                    match = re.search(r'(?:total|jumlah)\s*sms[:\s]*(\d+)', text, re.I)
                    if match:
                        total_sms = match.group(1)
                    else:
                        # Cari angka yang muncul setelah kata "sms"
                        match = re.search(r'sms\s*(\d+)', text, re.I)
                        if match:
                            total_sms = match.group(1)
                        else:
                            # Cari angka besar (biasanya 3-5 digit) di sekitar kata "received"
                            match = re.search(r'received[:\s]*(\d+)', text, re.I)
                            if match:
                                total_sms = match.group(1)
                    
                    # Nama: cari kata "nama" atau "name"
                    name = None
                    match = re.search(r'(?:nama|name)[:\s]*([A-Za-z\s]+)', text, re.I)
                    if match:
                        name = match.group(1).strip()
                    
                    # Telepon: cari nomor HP
                    phone = None
                    match = re.search(r'(\+?\d{10,15})', text)
                    if match:
                        phone = match.group(1)
                    
                    # Jika balance atau total_sms ditemukan, return
                    if balance or total_sms:
                        return {
                            'email': self.email,
                            'balance': balance if balance else 'Tidak ditemukan',
                            'total_sms': total_sms if total_sms else 'Tidak ditemukan',
                            'name': name if name else 'Tidak ditemukan',
                            'phone': phone if phone else 'Tidak ditemukan'
                        }
            # Jika belum ketemu, coba ambil dari halaman utama dashboard dengan pendekatan berbeda
            resp = self.session.get(self.base_url)
            if resp.status_code == 200:
                text = resp.text
                # Cari angka yang mungkin merupakan saldo (biasanya di card atau widget)
                numbers = re.findall(r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?\b', text)
                if numbers:
                    # Ambil angka pertama yang masuk akal (bukan kode OTP)
                    for num in numbers:
                        if len(num) >= 4 and len(num) <= 10:
                            balance = num
                            break
                return {
                    'email': self.email,
                    'balance': balance if 'balance' in locals() else 'Tidak ditemukan',
                    'total_sms': 'Tidak ditemukan',
                    'name': 'Tidak ditemukan',
                    'phone': 'Tidak ditemukan'
                }
            return self._dummy_profile()
        except Exception as e:
            print(f"Error profile: {e}")
            return self._dummy_profile()

    def fetch_traffic_stats(self):
        if not self.is_logged_in:
            return self._dummy_traffic()
        try:
            # Halaman yang mungkin berisi statistik
            for path in ['/statistics', '/stats', '/reports', '/dashboard']:
                self._update_headers()
                self._delay()
                resp = self.session.get(f"{self.base_url}{path}")
                if resp.status_code == 200:
                    text = resp.text
                    received = None
                    sent = None
                    earned = None
                    
                    # Cari total diterima
                    match = re.search(r'(?:received|incoming|masuk)[:\s]*(\d+)', text, re.I)
                    if match:
                        received = match.group(1)
                    # Cari total terkirim
                    match = re.search(r'(?:sent|outgoing|keluar)[:\s]*(\d+)', text, re.I)
                    if match:
                        sent = match.group(1)
                    # Cari pendapatan
                    match = re.search(r'(?:earn|pendapatan|revenue)[:\s]*([\d.,]+)', text, re.I)
                    if match:
                        earned = match.group(1)
                    
                    if received or sent or earned:
                        return {
                            'total_received': received if received else 'N/A',
                            'total_sent': sent if sent else 'N/A',
                            'total_earned': earned if earned else 'N/A'
                        }
            return self._dummy_traffic()
        except Exception:
            return self._dummy_traffic()

    def _dummy_profile(self):
        return {
            'email': self.email,
            'balance': 'Tidak ditemukan',
            'total_sms': 'Tidak ditemukan',
            'name': 'Tidak ditemukan',
            'phone': 'Tidak ditemukan'
        }

    def _dummy_traffic(self):
        return {
            'total_received': 'Tidak tersedia',
            'total_sent': 'Tidak tersedia',
            'total_earned': 'Tidak tersedia'
        }

def create_scraper(email, password):
    return IVASMSScraper(email, password)