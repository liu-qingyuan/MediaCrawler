import os
import sys
import asyncio
import pandas as pd
import re

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from get_sec_user_id import get_user_sec_id

def extract_douyin_id(account_str):
    """
    从Account列提取抖音号
    支持以下格式：
    1. 抖音号：91811174783(douyin)
    2. ms.ashlyn_(douyin)
    3. 快手ID：19951001O(kuaishou), 抖音号：19951001o(douyin)
    """
    if not isinstance(account_str, str):
        return None
        
    # 抖音号匹配 - 支持数字和字母的组合
    douyin_match = re.search(r'抖音号：([a-zA-Z0-9._]+)\s*\(douyin\)', account_str)
    if douyin_match:
        return douyin_match.group(1)
    
    # 直接匹配 xxx(douyin) 格式
    direct_match = re.search(r'([a-zA-Z0-9._]+)\s*\(douyin\)', account_str)
    if direct_match:
        return direct_match.group(1)
    
    return None

async def update_sec_ids(excel_path):
    """更新Excel文件中的sec_id"""
    print(f"正在读取Excel文件: {excel_path}")
    df = pd.read_excel(excel_path)
    
    # 如果不存在douyin_user_sec_id列，则创建
    if 'douyin_user_sec_id' not in df.columns:
        df['douyin_user_sec_id'] = None
        print("创建了新列: douyin_user_sec_id")
    
    # 遍历每一行
    for index, row in df.iterrows():
        user_id = extract_douyin_id(row['Account'])
        
        # 只处理抖音账号
        if user_id:
            print(f"\n处理第 {index + 1} 行")
            print(f"Account: {row['Account']}")
            print(f"提取的抖音号: {user_id}")
            print(f"当前sec_id值: {row['douyin_user_sec_id']}")
            
            # 如果已经有sec_id则跳过
            if pd.isna(row['douyin_user_sec_id']):
                try:
                    sec_uid = await get_user_sec_id(user_id)
                    if sec_uid:
                        print(f"获取到新的sec_uid: {sec_uid}")
                        df.at[index, 'douyin_user_sec_id'] = sec_uid
                        print(f"已更新第 {index + 1} 行的sec_uid")
                        
                        # 每行都保存
                        df.to_excel(excel_path, index=False)
                        print(f"已保存文件")
                except Exception as e:
                    print(f"处理抖音号 {user_id} 时出错: {e}")
            else:
                print(f"已有sec_id，跳过")
    
    # 最后保存一次
    df.to_excel(excel_path, index=False)
    print("\n处理完成，已保存文件")

async def main():
    excel_path = "data/51cg1_hyperlinks_results2.xlsx"
    await update_sec_ids(excel_path)

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断") 