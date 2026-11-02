from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def before_all(context):
    # Setel agar Chrome berjalan di latar belakang (headless mode) jika di server CI
    # Atau matikan headless mode agar Anda bisa melihat browser terbuka otomatis
    options = Options()
    # options.add_argument("--headless") # Buka comment ini jika ingin browser tidak terlihat
    
    # Inisialisasi browser Chrome
    context.browser = webdriver.Chrome(options=options)
    # Tunggu maksimal 10 detik jika elemen web agak lambat memuat
    context.browser.implicitly_wait(10)

def after_all(context):
    # Tutup browser setelah semua skenario selesai dijalankan
    context.browser.quit()
#plis men kenapa testing ni susah :(:()