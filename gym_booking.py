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
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Page
import ddddocr
from config import DEFAULT_CONFIG, XPATHS

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
        """步骤8: 选择日期（每1秒刷新直到出现目标日期）"""
        logger.info(f"步骤8: 选择日期 - {self.config['date_number']}")
        
        # 计算超时时间：预约时间后5分钟
        timeout_time = None
        if self.booking_time:
            timeout_time = self.booking_time + timedelta(minutes=5)
            logger.info(f"日期选择超时时间: {timeout_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        refresh_count = 0
        
        while True:
            refresh_count += 1
            logger.info(f"第 {refresh_count} 次检查日期")
            
            # 检查是否超时
            if timeout_time and datetime.now() > timeout_time:
                raise Exception(f"超出预约时间5分钟，停止日期选择")
            
            # 查找并点击指定的日期
            date_elements = await self.page.query_selector_all(f"{XPATHS['date_number']}")
            
            for element in date_elements:
                text = await element.text_content()
                if self.config['date_number'] in text:
                    await self.human_like_click(element)
                    logger.info(f"✅ 已选择日期: {text}")
                    await self.human_like_delay(0.2, 0.5)
                    return
            
            # 没找到目标日期，等待1秒后刷新页面
            logger.info(f"未找到日期 {self.config['date_number']}，1秒后刷新页面")
            await asyncio.sleep(1)
            await self.page.reload()
            await asyncio.sleep(1)
        
    async def step9_select_time_slot(self) -> List:
        """步骤9: 根据配置的时间段选择可预约按钮"""
        logger.info("步骤9: 根据配置的时间段选择可预约按钮")
        
        # 获取配置的时间段
        target_time_slots = []
        if 'time_slots' in self.config and self.config['time_slots']:
            target_time_slots = self.config['time_slots']
        elif 'time_slot' in self.config and self.config['time_slot']:
            target_time_slots = [self.config['time_slot']]
        
        logger.info(f"目标时间段: {target_time_slots}")
        
        # 获取所有可预约按钮
        all_bookable_buttons = await self.page.query_selector_all(XPATHS['bookable_slot'])
        logger.info(f"找到 {len(all_bookable_buttons)} 个可预约按钮")
        
        if not all_bookable_buttons:
            logger.error("未找到任何可预约按钮")
            raise Exception("未找到任何可预约按钮")
        
        # 如果配置了特定时间段，筛选匹配的按钮
        selected_buttons = []
        if target_time_slots:
            # 获取所有时间段行
            time_rows = await self.page.query_selector_all('tr')
            logger.info(f"找到 {len(time_rows)} 个时间段行")
            
            # 遍历每个时间段行，查找匹配的时间段
            for row in time_rows:
                row_text = await row.text_content()
                logger.info(f"检查时间段行: {row_text.strip()}")
                
                # 检查这一行是否包含目标时间段
                for target_slot in target_time_slots:
                    if target_slot in row_text:
                        logger.info(f"找到匹配的时间段: {target_slot}")
                        
                        # 在这一行中查找可预约按钮
                        row_bookable_buttons = await row.query_selector_all(XPATHS['bookable_slot'])
                        logger.info(f"在时间段 {target_slot} 中找到 {len(row_bookable_buttons)} 个可预约按钮")
                        
                        selected_buttons.extend(row_bookable_buttons)
        
        # 如果没有找到匹配的按钮，使用所有可预约按钮
        if not selected_buttons:
            logger.info("未找到匹配时间段的可预约按钮，使用所有可预约按钮")
            selected_buttons = all_bookable_buttons
        
        # 随机选择2个按钮
        num_buttons = min(2, len(selected_buttons))
        final_selected_buttons = random.sample(selected_buttons, num_buttons)
        
        logger.info(f"最终选择了 {len(final_selected_buttons)} 个时间段按钮")
        
        # 点击选中的按钮
        for idx, button in enumerate(final_selected_buttons):
            await self.human_like_click(button)
            logger.info(f"已选择第 {idx+1} 个时间段按钮")
            await self.human_like_delay(0.1, 0.2)
        
        return final_selected_buttons
        
    async def smart_booking_flow(self) -> bool:
        """智能预约流程：失败后从剩余按钮中选择其他按钮"""
        logger.info("开始智能预约流程")
        
        # 计算超时时间：预约时间后5分钟
        timeout_time = None
        if self.booking_time:
            timeout_time = self.booking_time + timedelta(minutes=5)
            logger.info(f"预约超时时间: {timeout_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取所有可预约按钮
        all_bookable_buttons = await self.page.query_selector_all(XPATHS['bookable_slot'])
        logger.info(f"找到 {len(all_bookable_buttons)} 个可预约按钮")
        
        if not all_bookable_buttons:
            logger.error("未找到任何可预约按钮")
            return False
        
        # 尝试预约，直到成功或所有按钮都尝试过或超时
        while all_bookable_buttons:
            # 检查是否超时
            if timeout_time and datetime.now() > timeout_time:
                logger.error("超出预约时间5分钟，停止预约")
                return False
            
            # 随机选择2个按钮
            num_buttons = min(2, len(all_bookable_buttons))
            selected_buttons = random.sample(all_bookable_buttons, num_buttons)
            
            logger.info(f"选择了 {len(selected_buttons)} 个按钮进行预约")
            
            # 点击选中的按钮
            for idx, button in enumerate(selected_buttons):
                await self.human_like_click(button)
                logger.info(f"已选择第 {idx+1} 个时间段按钮")
                await self.human_like_delay(0.05, 0.1)
            
            # 点击预约按钮
            success = await self.step10_click_book_button_with_retry()
            if not success:
                logger.warning("点击预约按钮失败，尝试其他按钮组合")
                # 从可用按钮中移除已尝试的按钮
                for button in selected_buttons:
                    if button in all_bookable_buttons:
                        all_bookable_buttons.remove(button)
                continue
            
            # 检查预约结果
            booking_success = await self.step11_check_success()
            if booking_success:
                logger.info("🎉 预约成功！")
                return True
            else:
                logger.warning("预约失败，尝试其他按钮组合")
                # 从可用按钮中移除已尝试的按钮
                for button in selected_buttons:
                    if button in all_bookable_buttons:
                        all_bookable_buttons.remove(button)
                
                # 如果还有可用按钮，继续尝试
                if all_bookable_buttons:
                    logger.info(f"还有 {len(all_bookable_buttons)} 个按钮可尝试")
                    await self.human_like_delay(1, 2)
        
        logger.error("所有可预约按钮都已尝试完毕，预约失败")
        return False
        
        
    async def step10_click_book_button_with_retry(self) -> bool:
        """步骤10: 点击预约按钮（每秒8次持续2秒或收到返回消息停止）"""
        logger.info("步骤10: 点击预约按钮（高频点击模式）")
        
        try:
            book_button = await self.page.wait_for_selector(XPATHS['book_button'], timeout=10000)
            
            # 高频点击：每秒8次，持续2秒
            start_time = time.time()
            click_count = 0
            
            while time.time() - start_time < 2.0:
                try:
                    await book_button.click()
                    click_count += 1
                    await asyncio.sleep(0.125)  # 每秒8次 = 每125ms一次
                    
                    # 检查是否出现弹窗
                    modal_content = await self.page.query_selector('.modal-content')
                    if modal_content:
                        logger.info(f"检测到弹窗，停止点击。共点击了 {click_count} 次")
                        return True
                        
                except Exception as e:
                    logger.warning(f"点击过程中出错: {e}")
                    break
            
            logger.info(f"高频点击完成，共点击了 {click_count} 次")
            
            # 等待弹窗出现
            logger.info("等待预约结果弹窗...")
            try:
                await self.page.wait_for_selector('.modal-content', timeout=5000)
                logger.info("预约结果弹窗已出现")
                return True
            except Exception as e:
                logger.warning(f"未检测到预约结果弹窗: {e}")
                return False
            
        except Exception as e:
            logger.error(f"点击预约按钮失败: {e}")
            return False
        
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
        """从第8步开始执行预约流程"""
        try:
            logger.info("从第8步开始执行预约流程")
            
            # 第8步：每1秒刷新页面直到出现目标日期，然后点击目标日期
            await self.step8_select_date()
            
            # 第9步：识别可预约按钮并随机选择2个
            selected_buttons = await self.step9_select_time_slot()
            
            # 第10步：点击预约按钮
            success = await self.step10_click_book_button_with_retry()
            if not success:
                logger.warning("点击预约按钮失败，尝试智能预约流程")
                return await self.smart_booking_flow()
            
            # 第11步：检查预约结果
            booking_success = await self.step11_check_success()
            if booking_success:
                logger.info("🎉 预约成功！")
                return True
            else:
                logger.warning("预约失败，尝试智能预约流程")
                return await self.smart_booking_flow()
            
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
            
            # 从第8步开始执行预约流程
            success = await self.run_booking_from_step8()
            
            if success:
                logger.info("✅ 预约流程完成，预约成功！")
                return True
            else:
                logger.error("❌ 预约失败")
                return False
            
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
    current_time = datetime.now()
    
    logger.info("=" * 50)
    logger.info("时间计算信息:")
    logger.info(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"预约时间: {booking_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"时间差: {start_time - current_time}")
    logger.info("=" * 50)
    
    if current_time < start_time:
        wait_seconds = (start_time - current_time).total_seconds()
        logger.info(f"⏰ 等待 {wait_seconds:.0f} 秒后开始预约...")
        
        # 倒计时显示（每秒更新同一行）
        remaining_seconds = int(wait_seconds)
        print(f"⏳ 倒计时: {remaining_seconds} 秒", end="", flush=True)
        
        while remaining_seconds > 0:
            await asyncio.sleep(1)
            remaining_seconds -= 1
            if remaining_seconds > 0:
                print(f"\r⏳ 倒计时: {remaining_seconds} 秒", end="", flush=True)
        
        print("\r🚀 到达启动时间，开始预约！")
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
    parser.add_argument('--times', help='多个预约时间段，用逗号分隔')
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
    if args.times:
        config['time_slots'] = args.times.split(',')
    if args.debug:
        config['debug'] = True
        
    # 解析预约时间
    booking_time = None
    if args.booking_time:
        try:
            # 解析用户输入的时间
            booking_time = datetime.strptime(args.booking_time, '%Y-%m-%d %H:%M:%S')
            current_time = datetime.now()
            logger.info(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"预约时间: {booking_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if booking_time <= current_time:
                logger.error(f"❌ 预约时间不能是过去时间！")
                logger.error(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(f"预约时间: {booking_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(f"请设置未来的时间，例如: {(current_time + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')}")
                return
                
        except ValueError:
            logger.error("预约时间格式错误，请使用: YYYY-MM-DD HH:MM:SS")
            logger.error(f"正确格式示例: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    if 'time_slots' in config and config['time_slots']:
        logger.info(f"时间段: {config['time_slots']}")
    else:
        logger.info(f"时间段: {config['time_slot']}")
    logger.info(f"调试模式: {'开启' if config['debug'] else '关闭'}")
    if booking_time:
        logger.info(f"预约时间: {booking_time.strftime('%Y-%m-%d %H:%M:%S')}")
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
