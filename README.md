谷歌网盘文件夹，分享链接下载python脚本

### 使用说明

1. **安装为全局命令**：
   ```bash
   git clone git@github.com:Map9876/gdown.git

   cd gdown
   
   pip install .
   ```

2. **命令行模式**：
   ```bash
   google -u "URL" -p "PROXY" -o "OUTPUT_DIR"
   ```

3. **交互模式**：
   ```bash
   google -i
   # 或直接
   google
   ```

   执行示例：

```
~/ $ google

==================================================
Google Drive 下载工具 - 交互模式
==================================================

请输入Google Drive链接（文件或文件夹）: https://drive.google.com/drive/folders/1nWyDlwNq2NrXREulM1Uj60Tt7vRMlGce?usp=drive_link

当前默认代理: https://c.map987.dpdns.org/
(直接回车使用默认代理，输入'n'不使用代理)
请输入代理地址:

请输入保存路径（直接回车使用当前目录）:

检测到文件夹链接，开始下载...
正在获取文件夹内容...
获取文件夹: 1NbuT-l8IOUV38sf7OU4zm0NFeEt-hiZA Anne Shirley
处理文件: 1o3DdvsbsNrIF
```
