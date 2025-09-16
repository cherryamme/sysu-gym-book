#!/usr/bin/env python3
"""
中山大学体育馆自动预约脚本
使用Playwright + stealth插件模拟人类行为进行预约
"""

import asyncio
import logging
import random
import time
import argparse
from datetime import datetime, timedelta
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
import ddddocr
from config import DEFAULT_CONFIG, XPATHS
# 移除timezone_utils依赖，使用Python标准库
import pytz

# 时区处理函数
def get_beijing_time():
    """获取当前北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)

def get_utc_time():
    """获取当前UTC时间"""
    return datetime.now(pytz.UTC)

def beijing_to_utc(beijing_time):
    """将北京时间转换为UTC时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    if beijing_time.tzinfo is None:
        beijing_time = beijing_tz.localize(beijing_time)
    return beijing_time.astimezone(pytz.UTC)

def utc_to_beijing(utc_time):
    """将UTC时间转换为北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return utc_time.astimezone(beijing_tz)

def format_beijing_time(dt):
    """格式化时间为北京时间字符串"""
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    beijing_time = dt.astimezone(pytz.timezone('Asia/Shanghai'))
    return beijing_time.strftime('%Y-%m-%d %H:%M:%S')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gym_booking.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GymBookingBot:
    """体育馆预约机器人"""
    
    def __init__(self, config: dict, booking_time: Optional[datetime] = None):
        self.config = config
        self.booking_time = booking_time
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.ocr = ddddocr.DdddOcr()
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_browser()
        
    async def start_browser(self):
        """启动浏览器"""
        playwright = await async_playwright().start()
        
        # 使用Chromium浏览器，启用stealth模式
        self.browser = await playwright.chromium.launch(
            headless=not self.config['debug'],
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-translate',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-client-side-phishing-detection',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-report-upload',
                '--disable-ipc-flooding-protection',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        # 创建新页面
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
        # 注入stealth脚本
        await self.page.add_init_script("""
            // 移除webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 模拟真实的Chrome对象
            window.chrome = {
                runtime: {},
            };
            
            // 模拟真实的插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 模拟真实的语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });
        """)
        
        logger.info("浏览器启动成功")
        
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")
            
    async def human_like_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """模拟人类操作的随机延迟"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        
    async def human_like_click(self, element):
        """模拟人类点击行为"""
        # 先移动到元素上
        await element.hover()
        await self.human_like_delay(0.1, 0.3)
        
        # 随机点击位置
        box = await element.bounding_box()
        if box:
            x = box['x'] + random.uniform(0.2, 0.8) * box['width']
            y = box['y'] + random.uniform(0.2, 0.8) * box['height']
            await self.page.mouse.click(x, y)
        else:
            await element.click()
            
        await self.human_like_delay(0.2, 0.5)
        
    async def human_like_type(self, element, text: str):
        """模拟人类输入行为"""
        await element.click()
        await self.human_like_delay(0.1, 0.3)
        
        # 逐字符输入，模拟真实打字
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
    async def solve_captcha(self) -> str:
        """识别验证码"""
        try:
            # 等待验证码图片加载
            captcha_img = await self.page.wait_for_selector(XPATHS['captcha_img'], timeout=10000)
            await self.human_like_delay(1, 2)
            
            # 截图验证码
            captcha_screenshot = await captcha_img.screenshot()
            
            # 使用ddddocr识别验证码
            result = self.ocr.classification(captcha_screenshot)
            logger.info(f"验证码识别结果: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
            raise
            
    async def step1_open_website(self):
        """步骤1: 打开网站并等待人机验证"""
        logger.info("步骤1: 打开体育馆预约网站")
        
        await self.page.goto(self.config['base_url'], wait_until='networkidle')
        await self.human_like_delay(2, 4)
        
        # 等待登录界面加载
        await self.page.wait_for_selector(XPATHS['username_input'], timeout=30000)
        logger.info("网站加载完成，等待人机验证...")
        
        # 等待更长时间让人机验证完成
        await self.human_like_delay(5, 8)
        
    async def step2_login(self):
        """步骤2: 输入账号密码"""
        logger.info("步骤2: 输入账号密码")
        
        # 输入用户名
        username_input = await self.page.wait_for_selector(XPATHS['username_input'])
        await self.human_like_type(username_input, self.config['username'])
        
        # 输入密码
        password_input = await self.page.wait_for_selector(XPATHS['password_input'])
        await self.human_like_type(password_input, self.config['password'])
        
        logger.info("账号密码输入完成")
        
    async def step3_solve_captcha(self):
        """步骤3: 识别并输入验证码"""
        logger.info("步骤3: 识别验证码")
        
        # 识别验证码
        captcha_text = await self.solve_captcha()
        
        # 输入验证码
        captcha_input = await self.page.wait_for_selector(XPATHS['captcha_input'])
        await self.human_like_type(captcha_input, captcha_text)
        
        logger.info(f"验证码输入完成: {captcha_text}")
        
    async def step4_click_login(self):
        """步骤4: 点击登录按钮"""
        logger.info("步骤4: 点击登录按钮")
        
        login_button = await self.page.wait_for_selector(XPATHS['login_button'])
        await self.human_like_click(login_button)
        
        # 等待页面跳转
        await self.human_like_delay(3, 5)
        
    async def step5_close_notification(self):
        """步骤5: 关闭登录后的悬浮窗通知"""
        logger.info("步骤5: 关闭登录后的悬浮窗通知")
        
        try:
            # 等待悬浮窗出现
            close_button = await self.page.wait_for_selector('button.btn-close', timeout=10000)
            await self.human_like_click(close_button)
            logger.info("已关闭悬浮窗通知")
            await self.human_like_delay(2, 3)
        except Exception as e:
            logger.warning(f"未找到悬浮窗关闭按钮，尝试刷新页面: {e}")
            try:
                # 刷新页面
                logger.info("正在刷新页面...")
                await self.page.reload()
                await self.human_like_delay(3, 5)
                
                # 再次尝试关闭悬浮窗
                close_button = await self.page.wait_for_selector('button.btn-close', timeout=5000)
                await self.human_like_click(close_button)
                logger.info("刷新后成功关闭悬浮窗通知")
                await self.human_like_delay(2, 3)
            except Exception as e2:
                logger.warning(f"刷新后仍未找到悬浮窗关闭按钮，直接进入下一步: {e2}")
                # 继续执行，不影响后续流程

    async def step6_select_campus(self):
        """步骤6: 选择校区"""
        logger.info(f"步骤6: 选择校区 - {self.config['campus_name']}")
        
        # 查找并点击指定的校区
        campus_elements = await self.page.query_selector_all(f"{XPATHS['campus_name']}")
        
        for element in campus_elements:
            text = await element.text_content()
            if self.config['campus_name'] in text:
                await self.human_like_click(element)
                logger.info(f"已选择校区: {text}")
                await self.human_like_delay(2, 3)
                return
                
        raise Exception(f"未找到校区: {self.config['campus_name']}")
        
    async def step7_select_facility(self):
        """步骤7: 选择体育馆"""
        logger.info(f"步骤7: 选择体育馆 - {self.config['facility_name']}")
        
        # 查找并点击指定的体育馆
        facility_elements = await self.page.query_selector_all(f"{XPATHS['facility_name']}")
        
        for element in facility_elements:
            text = await element.text_content()
            if self.config['facility_name'] in text:
                await self.human_like_click(element)
                logger.info(f"已选择体育馆: {text}")
                await self.human_like_delay(2, 3)
                return
                
        raise Exception(f"未找到体育馆: {self.config['facility_name']}")
        
    async def step8_select_date(self):
        """步骤8: 选择日期（带刷新逻辑）"""
        logger.info(f"步骤8: 选择日期 - {self.config['date_number']}")
        
        # 计算超时时间：预约时间后10分钟
        timeout_time = None
        if self.booking_time:
            timeout_time = self.booking_time + timedelta(minutes=10)
            logger.info(f"日期选择超时时间: {format_beijing_time(timeout_time)}")
        
        retry_count = 0
        while True:
            retry_count += 1
            logger.info(f"第 {retry_count} 次尝试选择日期")
            
            # 检查是否超时
            if timeout_time and get_utc_time() > timeout_time:
                raise Exception(f"超出预约时间10分钟，停止日期选择")
            
            # 查找并点击指定的日期
            date_elements = await self.page.query_selector_all(f"{XPATHS['date_number']}")
            
            for element in date_elements:
                text = await element.text_content()
                if self.config['date_number'] in text:
                    await self.human_like_click(element)
                    logger.info(f"已选择日期: {text}")
                    await self.human_like_delay(2, 3)
                    return
            
            # 如果没找到日期，刷新页面
            logger.warning(f"未找到日期 {self.config['date_number']}，1秒后刷新页面")
            await self.page.reload()
            await self.human_like_delay(1, 1)
        
    async def step9_select_time_slot(self):
        """步骤9: 选择时间段"""
        logger.info(f"步骤9: 选择时间段 - {self.config['time_slot']}")
        
        # 查找包含指定时间段的tr元素
        time_slot_xpath = XPATHS['time_slot'].format(self.config['time_slot'])
        time_rows = await self.page.query_selector_all(time_slot_xpath)
        
        if not time_rows:
            raise Exception(f"未找到时间段: {self.config['time_slot']}")
            
        # 在找到的行中查找可预约的按钮
        logger.debug(f"step9_select_time_slot: 共找到 {len(time_rows)} 个时间段行")
        for idx, row in enumerate(time_rows):
            logger.debug(f"检查第 {idx+1} 行时间段")
            # 查找该行中的可预约按钮
            bookable_buttons = await row.query_selector_all(XPATHS['bookable_slot'])
            logger.debug(f"第 {idx+1} 行可预约按钮数量: {len(bookable_buttons)}")
            if bookable_buttons:
                logger.info(f"第 {idx+1} 行存在可预约按钮，准备随机选择一个")
                # 随机选择该行中的一个可预约按钮
                selected_button = random.choice(bookable_buttons)
                button_index = bookable_buttons.index(selected_button)
                logger.info(f"第 {idx+1} 行共 {len(bookable_buttons)} 个可预约按钮，随机选择第 {button_index + 1} 个")
                await self.human_like_click(selected_button)
                logger.info(f"已选择时间段: {self.config['time_slot']}")
                await self.human_like_delay(2, 3)
                return
            else:
                logger.debug(f"第 {idx+1} 行没有可预约按钮")
        
        # 如果没找到，尝试在整个页面查找可预约按钮
        logger.info("在指定时间段行中未找到可预约按钮，尝试在整个页面查找")
        all_bookable_buttons = await self.page.query_selector_all(XPATHS['bookable_slot'])
        logger.debug(f"页面中总共找到 {len(all_bookable_buttons)} 个可预约按钮")
        
        if all_bookable_buttons:
            # 随机选择一个可预约按钮
            selected_button = random.choice(all_bookable_buttons)
            logger.info(f"找到 {len(all_bookable_buttons)} 个可预约按钮，随机选择第 {all_bookable_buttons.index(selected_button) + 1} 个")
            await self.human_like_click(selected_button)
            logger.info(f"已选择时间段: {self.config['time_slot']}")
            await self.human_like_delay(2, 3)
            return
        
        logger.error(f"未找到任何可预约按钮，时间段 {self.config['time_slot']} 不可预约")
        raise Exception(f"时间段 {self.config['time_slot']} 不可预约")
        
    async def step10_click_book_button(self):
        """步骤10: 点击预约按钮并等待弹窗"""
        logger.info("步骤10: 点击预约按钮")
        
        book_button = await self.page.wait_for_selector(XPATHS['book_button'], timeout=10000)
        await self.human_like_click(book_button)
        
        # 等待弹窗出现
        logger.info("等待预约结果弹窗...")
        try:
            await self.page.wait_for_selector('.modal-content', timeout=15000)
            logger.info("预约结果弹窗已出现")
        except Exception as e:
            logger.warning(f"未检测到预约结果弹窗: {e}")
        
        # 等待弹窗内容加载完成
        await self.human_like_delay(2, 3)
        
    async def step11_check_success(self) -> bool:
        """步骤11: 检查预约是否成功"""
        logger.info("步骤11: 检查预约结果")
        
        try:
            # 等待页面加载完成
            await self.human_like_delay(2, 3)
            
            # 检查是否存在弹窗
            modal_content = await self.page.query_selector('.modal-content')
            if modal_content:
                # 获取弹窗内容
                modal_text = await modal_content.text_content()
                logger.info(f"弹窗内容: {modal_text}")
                
                # 检查是否包含成功文本
                if "预约成功" in modal_text or "您已经预约成功" in modal_text:
                    logger.info("🎉 预约成功！")
                    return True
                else:
                    logger.warning("弹窗中未检测到预约成功文本")
                    return False
            else:
                # 如果没有弹窗，检查页面文本
                page_text = await self.page.text_content('body')
                logger.info(f"页面内容: {page_text}")
                
                if "预约成功" in page_text:
                    logger.info("🎉 预约成功！")
                    return True
                else:
                    logger.warning("未检测到预约成功文本")
                    return False
                
        except Exception as e:
            logger.error(f"检查预约结果失败: {e}")
            return False
            
    async def run_booking_from_step8(self) -> bool:
        """从第8步开始执行预约流程（用于重试）"""
        try:
            logger.info("从第8步开始执行预约流程")
            
            await self.step8_select_date()
            await self.step9_select_time_slot()
            await self.step10_click_book_button()
            
            success = await self.step11_check_success()
            return success
            
        except Exception as e:
            logger.error(f"从第8步开始的预约流程失败: {e}")
            if self.config['debug']:
                # 调试模式下截图保存
                await self.page.screenshot(path='error_screenshot.png')
                logger.info("错误截图已保存为 error_screenshot.png")
            return False

    async def run_booking(self) -> bool:
        """执行完整的预约流程"""
        try:
            logger.info("开始执行体育馆预约流程")
            
            # 执行前7步（一次性完成）
            await self.step1_open_website()
            await self.step2_login()
            await self.step3_solve_captcha()
            await self.step4_click_login()
            await self.step5_close_notification()
            await self.step6_select_campus()
            await self.step7_select_facility()
            
            # 从第8步开始重试循环
            retry_count = 0
            while True:
                retry_count += 1
                logger.info(f"第 {retry_count} 次尝试预约")
                
                # 检查是否超时
                if self.booking_time:
                    timeout_time = self.booking_time + timedelta(minutes=10)
                    if get_utc_time() > timeout_time:
                        logger.error(f"超出预约时间10分钟，停止重试")
                        return False
                
                # 执行第8-11步
                success = await self.run_booking_from_step8()
                
                if success:
                    logger.info("✅ 预约流程完成，预约成功！")
                    return True
                else:
                    logger.warning(f"第 {retry_count} 次预约失败，准备重试")
                    # 刷新页面，准备重试
                    await self.page.reload()
                    await self.human_like_delay(2, 3)
            
        except Exception as e:
            logger.error(f"预约流程失败: {e}")
            if self.config['debug']:
                # 调试模式下截图保存
                await self.page.screenshot(path='error_screenshot.png')
                logger.info("错误截图已保存为 error_screenshot.png")
            return False


async def wait_until_booking_time(booking_time: datetime):
    """等待到预约时间前1分钟"""
    start_time = booking_time - timedelta(minutes=1)
    current_time = get_utc_time()
    
    logger.info("=" * 50)
    logger.info("时间计算信息:")
    logger.info(f"当前时间: {format_beijing_time(current_time)}")
    logger.info(f"预约时间: {format_beijing_time(booking_time)}")
    logger.info(f"启动时间: {format_beijing_time(start_time)}")
    logger.info(f"时间差: {start_time - current_time}")
    logger.info("=" * 50)
    
    if current_time < start_time:
        wait_seconds = (start_time - current_time).total_seconds()
        logger.info(f"⏰ 等待 {wait_seconds:.0f} 秒后开始预约...")
        await asyncio.sleep(wait_seconds)
        logger.info("🚀 到达启动时间，开始预约！")
    else:
        logger.warning(f"⚠️ 当前时间已超过启动时间，立即开始预约")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='中山大学体育馆自动预约脚本')
    parser.add_argument('--username', help='登录用户名')
    parser.add_argument('--password', help='登录密码')
    parser.add_argument('--campus', help='校区名称')
    parser.add_argument('--facility', help='体育馆名称')
    parser.add_argument('--date', help='预约日期')
    parser.add_argument('--time', help='预约时间段')
    parser.add_argument('--debug', action='store_true', help='调试模式（显示浏览器）')
    parser.add_argument('--booking-time', help='预约运行时间 (格式: YYYY-MM-DD HH:MM:SS)')
    
    args = parser.parse_args()
    
    # 构建配置
    config = DEFAULT_CONFIG.copy()
    if args.username:
        config['username'] = args.username
    if args.password:
        config['password'] = args.password
    if args.campus:
        config['campus_name'] = args.campus
    if args.facility:
        config['facility_name'] = args.facility
    if args.date:
        config['date_number'] = args.date
    if args.time:
        config['time_slot'] = args.time
    if args.debug:
        config['debug'] = True
        
    # 解析预约时间
    booking_time = None
    if args.booking_time:
        try:
            # 解析用户输入的北京时间，转换为UTC时间存储
            beijing_time = datetime.strptime(args.booking_time, '%Y-%m-%d %H:%M:%S')
            booking_time = beijing_to_utc(beijing_time.replace(tzinfo=None))
            current_time = get_utc_time()
            logger.info(f"当前时间: {format_beijing_time(current_time)}")
            logger.info(f"预约时间: {format_beijing_time(booking_time)}")
            
            if booking_time <= current_time:
                logger.error(f"❌ 预约时间不能是过去时间！")
                logger.error(f"当前时间: {format_beijing_time(current_time)}")
                logger.error(f"预约时间: {format_beijing_time(booking_time)}")
                logger.error(f"请设置未来的时间，例如: {format_beijing_time(current_time + timedelta(minutes=10))}")
                return
                
        except ValueError:
            logger.error("预约时间格式错误，请使用: YYYY-MM-DD HH:MM:SS")
            logger.error(f"正确格式示例: {format_beijing_time(get_utc_time())}")
            return
        
    # 检查必要参数
    if not config['username'] or not config['password']:
        logger.error("请提供用户名和密码")
        return
        
    logger.info("=" * 50)
    logger.info("中山大学体育馆自动预约脚本启动")
    logger.info(f"用户名: {config['username']}")
    logger.info(f"校区: {config['campus_name']}")
    logger.info(f"体育馆: {config['facility_name']}")
    logger.info(f"日期: {config['date_number']}")
    logger.info(f"时间段: {config['time_slot']}")
    logger.info(f"调试模式: {'开启' if config['debug'] else '关闭'}")
    if booking_time:
        logger.info(f"预约时间: {format_beijing_time(booking_time)}")
    logger.info("=" * 50)
    
    # 如果设置了预约时间，等待到启动时间
    if booking_time:
        await wait_until_booking_time(booking_time)
    
    # 执行预约
    async with GymBookingBot(config, booking_time) as bot:
        success = await bot.run_booking()
        
    if success:
        logger.info("🎉 预约成功完成！")
    else:
        logger.error("❌ 预约失败，请检查日志")


if __name__ == "__main__":
    asyncio.run(main())
