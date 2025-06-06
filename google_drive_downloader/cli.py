#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive 下载工具 - 完整版
支持命令行参数和交互式输入
可下载文件/文件夹，支持代理配置
"""

import os
import re
import sys
import json
import requests
import argparse
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple, Union
import collections
import itertools
import warnings

# 常量定义
MAX_NUMBER_FILES = 50000
DEFAULT_PROXY = "https://c.map987.dpdns.org/"

class _GoogleDriveFile(object):
    TYPE_FOLDER = "application/vnd.google-apps.folder"

    def __init__(self, id, name, type, children=None):
        self.id = id
        self.name = name
        self.type = type
        self.children = children if children is not None else []

    def is_folder(self):
        return self.type == self.TYPE_FOLDER

GoogleDriveFileToDownload = collections.namedtuple(
    "GoogleDriveFileToDownload", ("id", "path", "local_path")
)

def _parse_google_drive_file(url, content):
    """解析Google Drive文件夹内容"""
    folder_soup = BeautifulSoup(content, features="html.parser")
    
    # 查找包含文件夹数据的脚本标签
    encoded_data = None
    for script in folder_soup.select("script"):
        inner_html = script.decode_contents()
        if "_DRIVE_ivd" in inner_html:
            regex_iter = re.compile(r"'((?:[^'\\]|\\.)*)'").finditer(inner_html)
            try:
                encoded_data = next(itertools.islice(regex_iter, 1, None)).group(1)
            except StopIteration:
                raise RuntimeError("无法找到文件夹编码数据")
            break

    if encoded_data is None:
        raise RuntimeError(
            "无法从链接获取文件夹信息。请检查权限设置或访问次数是否过多。"
        )

    # 解码数据
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        decoded = encoded_data.encode("utf-8").decode("unicode_escape")
    folder_arr = json.loads(decoded)
    folder_contents = [] if folder_arr[0] is None else folder_arr[0]

    # 提取文件夹名称
    sep = " - "
    splitted = folder_soup.title.contents[0].split(sep)
    if len(splitted) >= 2:
        name = sep.join(splitted[:-1])
    else:
        raise RuntimeError(
            f"无法从标题提取文件名: {folder_soup.title.contents[0]}"
        )

    gdrive_file = _GoogleDriveFile(
        id=url.split("/")[-1],
        name=name,
        type=_GoogleDriveFile.TYPE_FOLDER,
    )

    id_name_type_iter = [
        (e[0], e[2].encode("raw_unicode_escape").decode("utf-8"), e[3])
        for e in folder_contents
    ]

    return gdrive_file, id_name_type_iter

def _download_and_parse_google_drive_link(sess, url, proxy_, quiet=False, remaining_ok=False, verify=True):
    """递归获取Google Drive文件夹结构"""
    return_code = True
    url_ = proxy_ + url
    for _ in range(2):
        res = sess.get(url_, verify=verify)
        url = res.url

    gdrive_file, id_name_type_iter = _parse_google_drive_file(url, res.text)

    for child_id, child_name, child_type in id_name_type_iter:
        if child_type != _GoogleDriveFile.TYPE_FOLDER:
            if not quiet:
                print("处理文件:", child_id, child_name)
            gdrive_file.children.append(
                _GoogleDriveFile(id=child_id, name=child_name, type=child_type)
            )
            if not return_code:
                return return_code, None
            continue

        if not quiet:
            print("获取文件夹:", child_id, child_name)
        return_code, child = _download_and_parse_google_drive_link(
            sess=sess,
            url="https://drive.google.com/drive/folders/" + child_id,
            proxy_=proxy_,
            quiet=quiet,
            remaining_ok=remaining_ok,
        )
        if not return_code:
            return return_code, None
        gdrive_file.children.append(child)
    
    if not remaining_ok and len(gdrive_file.children) == MAX_NUMBER_FILES:
        print(f"警告: 文件夹包含文件数已达上限 {MAX_NUMBER_FILES}")
    
    return return_code, gdrive_file

def _get_directory_structure(gdrive_file, previous_path):
    """生成目录结构列表"""
    directory_structure = []
    for file in gdrive_file.children:
        file.name = file.name.replace(os.path.sep, "_")
        if file.is_folder():
            directory_structure.append((None, os.path.join(previous_path, file.name)))
            directory_structure.extend(
                _get_directory_structure(file, os.path.join(previous_path, file.name))
            )
        elif not file.children:
            directory_structure.append((file.id, os.path.join(previous_path, file.name)))
    return directory_structure

def clean_filename(filename):
    """清理文件名中的非法字符"""
    try:
        return filename.encode('utf-8', 'ignore').decode('utf-8')
    except AttributeError:
        return filename

def download_file(file_id, file_name, save_path, proxy):
    """下载单个文件"""
    if proxy and not proxy.endswith('/'):
        proxy += '/'
    
    url = proxy + f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    
    try:
        file_path = os.path.join(save_path, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        print(f"正在下载: {file_name}...", end='', flush=True)
        response = requests.get(url, stream=True)
        
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print("✓ 完成")
            return True
        print(f"× 失败 (HTTP {response.status_code})")
    except Exception as e:
        print(f"× 错误: {str(e)}")
    return False

def download_folder(proxy_, url=None, id=None, output=None, quiet=False, proxy=None, remaining_ok=False, verify=True):
    """下载整个文件夹"""
    if not (id is None) ^ (url is None):
        raise ValueError("必须指定URL或ID中的一个")
    if id is not None:
        url = f"https://drive.google.com/drive/folders/{id}"
    
    sess = requests.session()
    sess.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
    })

    if not quiet:
        print("正在获取文件夹内容...")
    
    is_success, gdrive_file = _download_and_parse_google_drive_link(
        sess, url, proxy_, quiet, remaining_ok, verify
    )
    
    if not is_success:
        print("获取文件夹内容失败", file=sys.stderr)
        return None

    if not quiet:
        print("正在构建目录结构...")
    
    directory_structure = _get_directory_structure(gdrive_file, "")
    
    if not quiet:
        print("目录结构构建完成")
        print("-"*50)
        print("文件列表:")
        for item in directory_structure:
            print(item[1] if item[0] is None else f"[文件] {item[1]}")
        print("-"*50)

    # 设置输出目录
    if output is None:
        output = os.getcwd()
    elif output.endswith(os.path.sep):
        output = os.path.join(output, gdrive_file.name)
    
    os.makedirs(output, exist_ok=True)

    # 下载所有文件
    downloaded_files = []
    for file_id, file_path in directory_structure:
        if file_id is None:  # 文件夹
            os.makedirs(os.path.join(output, file_path), exist_ok=True)
            continue
        
        local_path = os.path.join(output, file_path)
        if download_file(file_id, file_path, output, proxy):
            downloaded_files.append(local_path)
    
    if not quiet:
        print(f"\n下载完成，共下载 {len(downloaded_files)} 个文件")
    
    return downloaded_files

def 确保代理格式正确(代理地址):
    """确保代理地址格式正确"""
    if 代理地址 and not 代理地址.endswith('/'):
        代理地址 += '/'
    return 代理地址

def 交互模式():
    """交互式用户界面"""
    print("\n" + "="*50)
    print("Google Drive 下载工具 - 交互模式")
    print("="*50)
    
    # 获取下载链接
    while True:
        url = input("\n请输入Google Drive链接（文件或文件夹）: ").strip()
        if any(p in url for p in ['/file/d/', '/drive/folders/']):
            break
        print("错误: 必须是有效的Google Drive文件或文件夹链接")
    
    # 代理设置
    print(f"\n当前默认代理: {DEFAULT_PROXY}")
    print("(直接回车使用默认代理，输入'n'不使用代理)")
    proxy = input("请输入代理地址: ").strip()
    
    if proxy.lower() == 'n':
        proxy = ""
    elif not proxy:
        proxy = DEFAULT_PROXY
    
    proxy = 确保代理格式正确(proxy)
    
    # 输出目录
    output = input("\n请输入保存路径（直接回车使用当前目录）: ").strip()
    if not output:
        output = os.getcwd()
    
    # 判断链接类型
    if '/file/d/' in url:
        print("\n检测到单文件链接，开始下载...")
        file_id = re.search(r'/file/d/([^/]+)', url).group(1)
        filename = os.path.basename(url.rstrip('/'))
        download_file(file_id, filename, output, proxy)
    else:
        print("\n检测到文件夹链接，开始下载...")
        download_folder(proxy_=proxy, url=url, output=output, proxy=proxy)

def 命令行模式(args):
    """处理命令行参数"""
    proxy = 确保代理格式正确(args.proxy)
    
    if '/file/d/' in args.url:
        print("检测到单文件链接，开始下载...")
        file_id = re.search(r'/file/d/([^/]+)', args.url).group(1)
        filename = os.path.basename(args.url.rstrip('/'))
        download_file(file_id, filename, args.output, proxy)
    else:
        print("检测到文件夹链接，开始下载...")
        download_folder(
            proxy_=proxy,
            url=args.url,
            output=args.output,
            proxy=proxy
        )

def main():
    parser = argparse.ArgumentParser(
        description='Google Drive 下载工具',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-u', '--url',
        help='Google Drive链接 (文件或文件夹)',
        type=str,
        default=''
    )
    parser.add_argument(
        '-o', '--output',
        help='输出目录 (默认当前目录)',
        default=os.getcwd(),
        type=str
    )
    parser.add_argument(
        '-p', '--proxy',
        help=f'代理服务器地址 (默认: {DEFAULT_PROXY})',
        default=DEFAULT_PROXY,
        type=str
    )
    parser.add_argument(
        '-i', '--interactive',
        help='进入交互模式',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    if args.interactive or not args.url:
        交互模式()
    else:
        命令行模式(args)

if __name__ == "__main__":
    main()
