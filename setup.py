from setuptools import setup, find_packages

setup(
    name="google-drive-downloader",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.1',
        'beautifulsoup4>=4.9.3',
    ],
    entry_points={
        'console_scripts': [
            'google=google_drive_downloader.cli:main',
        ],
    },
    python_requires='>=3.6',
    author="Your Name",
    description="Google Drive 文件下载工具",
    keywords="google drive downloader",
)
