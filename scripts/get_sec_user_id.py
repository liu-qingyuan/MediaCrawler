import os
import sys
import json
import asyncio
from urllib.parse import quote

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from playwright.async_api import async_playwright
import config
from media_platform.douyin.core import DouYinCrawler
from media_platform.douyin.client import DOUYINClient

async def get_user_sec_id(user_id: str):
    """
    通过抖音号获取 sec_user_id
    :param user_id: 抖音号，如 "91811174783"
    """
    # 设置基础配置
    config.PLATFORM = "dy"
    config.HEADLESS = False
    
    crawler = DouYinCrawler()
    
    try:
        print("正在启动浏览器...")
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            crawler.browser_context = await crawler.launch_browser(
                chromium,
                None,
                user_agent=None,
                headless=config.HEADLESS
            )
            
            try:
                # 添加反检测脚本
                await crawler.browser_context.add_init_script(path="libs/stealth.min.js")
                crawler.context_page = await crawler.browser_context.new_page()

                # 直接访问搜索页面
                search_url = f"https://www.douyin.com/search/{quote(user_id)}?type=user"
                print(f"正在访问: {search_url}")
                
                # 等待API响应
                async with crawler.context_page.expect_response(
                    lambda resp: "aweme/v1/web/discover/search" in resp.url
                ) as response_info:
                    # 访问搜索页面
                    await crawler.context_page.goto(search_url)
                    await asyncio.sleep(4)  # 等待页面加载
                    
                    # 检查是否需要滑块验证
                    slider_selectors = [
                        ".vc-captcha-verify-visibility",  # 验证码容器
                        ".captcha_verify_bar--title",     # 标题文本
                        ".captcha-verify-image",          # 验证图片
                        ".captcha-slider-btn",            # 滑块按钮
                        ".captcha_verify_slide--button"   # 滑块容器
                    ]
                    
                    for selector in slider_selectors:
                        try:
                            element = await crawler.context_page.locator(selector).first
                            if element:
                                print("\n检测到滑块验证，请手动完成验证...")
                                print("完成验证后请按回车继续...")
                                input()
                                await crawler.context_page.reload()
                                await asyncio.sleep(2)
                                break
                        except Exception:
                            continue
                    
                    # 获取响应
                    response = await response_info.value
                    
                    # 获取响应数据
                    data = await response.json()
                    
                    # 解析结果
                    if "user_list" in data:
                        for user in data["user_list"]:
                            if user.get("user_info", {}).get("unique_id") == user_id:
                                sec_uid = user["user_info"]["sec_uid"]
                                print(f"\n找到匹配的用户 sec_uid: {sec_uid}")
                                return sec_uid
                    
                    print("\n未找到匹配的用户")
                    return None
                
            finally:
                if crawler.browser_context:
                    await crawler.browser_context.close()
            
    except Exception as e:
        print(f"发生错误: {e}")
        return None

async def main():
    user_id = "91811174783"
    sec_uid = await get_user_sec_id(user_id)
    if sec_uid:
        print(f"\n抖音号 {user_id} 对应的 sec_uid 是: {sec_uid}")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")