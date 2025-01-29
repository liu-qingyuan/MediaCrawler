# 声明：本代码仅供学习和研究目的使用。
import os
import sys
import json
import asyncio
import pandas as pd
from datetime import datetime
import aiohttp
import aiofiles
from urllib.parse import urlparse, unquote

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from playwright.async_api import async_playwright
import config
from media_platform.douyin.core import DouYinCrawler

async def get_all_user_posts(crawler, sec_uid):
    """
    获取用户的所有作品列表
    使用分页方式获取全部作品
    """
    try:
        # 使用已有的 get_all_user_aweme_posts 方法
        posts = await crawler.dy_client.get_all_user_aweme_posts(sec_uid)
        print(f"已获取 {len(posts)} 个作品")
        return posts
    except Exception as e:
        print(f"获取作品列表出错: {e}")
        return []

async def get_user_info_and_posts(sec_uid: str, crawler: DouYinCrawler):
    """通过 sec_uid 获取用户信息和作品列表"""
    try:
        # 访问用户主页
        user_url = f"https://www.douyin.com/user/{sec_uid}"
        print(f"正在访问用户主页: {user_url}")
        
        # 访问页面
        await crawler.context_page.goto(user_url)
        await asyncio.sleep(3)
        
        # 创建 DOUYINClient 实例
        print("正在获取用户信息...")
        crawler.dy_client = await crawler.create_douyin_client(None)
        
        # 使用 API 获取用户信息
        user_data = await crawler.dy_client.get_user_info(sec_user_id=sec_uid)
        
        if user_data.get("status_code") != 0:
            print(f"获取用户信息失败: {user_data.get('status_msg')}")
            return None, []
            
        user_info = user_data.get("user", {})
        
        try:
            # 获取所有作品
            posts = await crawler.dy_client.get_all_user_aweme_posts(sec_user_id=sec_uid)
            print(f"总共获取到 {len(posts)} 个作品")
            
            # 打印所有作品的封面图片链接
            print("\n作品封面图片链接:")
            for i, post in enumerate(posts, 1):
                cover_urls = post.get('video', {}).get('cover', {}).get('url_list', [])
                if cover_urls:
                    print(f"\n作品 {i}:")
                    print(f"标题: {post.get('desc')}")
                    print(f"封面链接: {cover_urls[0]}")
            
            return user_info, posts
            
        except Exception as e:
            error_msg = str(e)
            if "account blocked" in error_msg:
                print("\n账号被限制，请按以下步骤操作：")
                print("1. 在浏览器中完成任何验证")
                print("2. 确认可以正常访问后")
                print("3. 按回车键继续...")
                input()
                
                # 重新创建 client 并重试
                crawler.dy_client = await crawler.create_douyin_client(None)
                posts = await crawler.dy_client.get_all_user_aweme_posts(sec_user_id=sec_uid)
                return user_info, posts
            else:
                print(f"获取作品列表出错: {e}")
                return user_info, []
            
    except Exception as e:
        print(f"发生错误: {e}")
        return None, []

def get_valid_video_url(url_list):
    """
    从视频链接列表中获取有效的链接
    优先获取 v5-dy-o-abtest.zjcdn.com 域名的链接
    """
    if not url_list:
        return ''
    
    # 优先查找 zjcdn 域名的链接
    for url in url_list:
        if 'v5-dy-o-abtest.zjcdn.com' in url:
            return url
    
    return ''  # 如果没找到有效链接，返回空字符串

async def get_proxy():
    """获取代理IP"""
    # 这里替换为你的代理IP获取接口
    proxy_api = "http://your-proxy-api.com/get"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(proxy_api) as response:
                if response.status == 200:
                    proxy_data = await response.json()
                    return f"http://{proxy_data['ip']}:{proxy_data['port']}"
    except Exception as e:
        print(f"获取代理IP失败: {e}")
    return None

async def collect_user_info(input_excel):
    """从Excel文件中读取sec_uid并收集用户信息"""
    print(f"正在读取Excel文件: {input_excel}")
    df = pd.read_excel(input_excel)
    
    if 'douyin_user_sec_id' not in df.columns:
        print("错误：Excel文件中没有 douyin_user_sec_id 列")
        return
    
    # 创建输出目录
    output_dir = os.path.join(ROOT_DIR, "data", "douyin", "user_info")
    os.makedirs(output_dir, exist_ok=True)
    
    # 固定输出文件名
    user_output_file = os.path.join(output_dir, "douyin_user_info.xlsx")
    posts_output_file = os.path.join(output_dir, "douyin_posts_info.xlsx")
    
    # 定义列名
    user_columns = [
        'account', 'sec_uid', 'nickname', 'signature', 
        'follower_count', 'following_count', 'total_favorited', 
        'aweme_count', 'unique_id', 'short_id'
    ]
    
    posts_columns = [
        'account', 'sec_uid', 'aweme_id', 'desc', 
        'create_time', 'comment_count', 'digg_count', 
        'share_count', 'collect_count',
        'video_url',  # 无水印视频链接
        'cover_url'   # 视频封面链接
    ]
    
    # 读取已存在的数据
    try:
        user_df = pd.read_excel(user_output_file)
        print(f"读取到已有用户数据: {len(user_df)} 条")
    except FileNotFoundError:
        user_df = pd.DataFrame(columns=user_columns)
        print("创建新的用户数据文件")
    
    try:
        posts_df = pd.read_excel(posts_output_file)
        print(f"读取到已有作品数据: {len(posts_df)} 条")
    except FileNotFoundError:
        posts_df = pd.DataFrame(columns=posts_columns)
        print("创建新的作品数据文件")
    
    # 创建浏览器实例
    crawler = DouYinCrawler()
    print("正在启动浏览器...")
    async with async_playwright() as playwright:
        chromium = playwright.chromium
        crawler.browser_context = await crawler.launch_browser(
            chromium,
            None,  # 移除代理参数
            user_agent=None,
            headless=config.HEADLESS
        )
        
        # 添加反检测脚本
        await crawler.browser_context.add_init_script(path="libs/stealth.min.js")
        crawler.context_page = await crawler.browser_context.new_page()
        
        try:
            # 遍历每一行
            for index, row in df.iterrows():
                sec_uid = row['douyin_user_sec_id']
                if pd.isna(sec_uid):
                    continue
                    
                # 检查用户是否已存在
                if not user_df.empty and sec_uid in user_df['sec_uid'].values:
                    print(f"\n用户 {sec_uid} 已存在，跳过")
                    continue
                    
                print(f"\n处理第 {index + 1} 行")
                print(f"sec_uid: {sec_uid}")
                
                try:
                    user_info, posts = await get_user_info_and_posts(sec_uid, crawler)
                    if user_info:
                        # 处理用户信息
                        user_info['account'] = row['Account']
                        user_info['sec_uid'] = sec_uid
                        new_user_row = pd.DataFrame([{
                            col: user_info.get(col) for col in user_columns
                        }])
                        user_df = pd.concat([user_df, new_user_row], ignore_index=True)
                        user_df.to_excel(user_output_file, index=False)
                        print(f"已保存用户信息到: {user_output_file}")
                        
                        # 处理作品信息
                        new_posts_count = 0
                        for post in posts:
                            aweme_id = post.get('aweme_id')
                            # 检查作品是否已存在
                            if not posts_df.empty and aweme_id in posts_df['aweme_id'].values:
                                print(f"作品 {aweme_id} 已存在，跳过")
                                continue
                                
                            # 获取视频链接
                            video_urls = post.get('video', {}).get('play_addr', {}).get('url_list', [])
                            video_url = get_valid_video_url(video_urls)
                            
                            # 获取封面图片链接（使用第一个链接）
                            cover_urls = post.get('video', {}).get('cover', {}).get('url_list', [])
                            cover_url = cover_urls[0] if cover_urls else ''
                            
                            post_info = {
                                'account': row['Account'],
                                'sec_uid': sec_uid,
                                'aweme_id': aweme_id,
                                'desc': post.get('desc'),
                                'create_time': post.get('create_time'),
                                'comment_count': post.get('statistics', {}).get('comment_count'),
                                'digg_count': post.get('statistics', {}).get('digg_count'),
                                'share_count': post.get('statistics', {}).get('share_count'),
                                'collect_count': post.get('statistics', {}).get('collect_count'),
                                'video_url': video_url,
                                'cover_url': cover_url
                            }
                            new_post_row = pd.DataFrame([post_info])
                            posts_df = pd.concat([posts_df, new_post_row], ignore_index=True)
                            new_posts_count += 1
                        
                        if new_posts_count > 0:
                            posts_df.to_excel(posts_output_file, index=False)
                            print(f"已保存 {new_posts_count} 个新作品信息到: {posts_output_file}")
                        else:
                            print("没有新的作品需要保存")
                
                except Exception as e:
                    print(f"处理用户信息时出错: {e}")
                    continue
                    
        finally:
            # 确保浏览器最后关闭
            if crawler.browser_context:
                await crawler.browser_context.close()
    
    print(f"\n当前总共有 {len(user_df)} 个用户的信息")
    print(f"\n当前总共有 {len(posts_df)} 个作品的信息")

async def main():
    input_excel = "data/51cg1_hyperlinks_results2.xlsx"
    await collect_user_info(input_excel)

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断") 