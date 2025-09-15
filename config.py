"""
体育馆预约配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 默认配置
DEFAULT_CONFIG = {
    'username': os.getenv('USERNAME', ''),
    'password': os.getenv('PASSWORD', ''),
    'campus_name': os.getenv('CAMPUS_NAME', '广州校区南校园'),
    'facility_name': os.getenv('FACILITY_NAME', '南校园新体育馆羽毛球场（学生）'),
    'date_number': os.getenv('DATE_NUMBER', '9-17'),
    'time_slot': os.getenv('TIME_SLOT', '21:00-22:00'),
    'base_url': 'https://gym.sysu.edu.cn',
    'debug': False
}

# XPath 配置
XPATHS = {
    'username_input': '//*[@id="username"]',
    'password_input': '//*[@id="password"]',
    'captcha_img': '//*[@id="captchaImg"]',
    'captcha_input': '//*[@id="captcha"]',
    'login_button': '//*[@id="fm1"]/section[2]/input[4]',
    'campus_name': '//*[@class="campus-name"]',
    'facility_name': '//*[@class="facility-name"]',
    'date_number': '//*[@class="date-number"]',
    'time_slot': '//tr[contains(., "{}")]',
    'bookable_slot': 'button.slot-btn.available',
    'book_button': '//*[@class="btn btn-primary btn-large"]',
}
