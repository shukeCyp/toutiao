"""
日志系统 - 每次启动创建独立日志文件
日志保存到项目根目录 logs/ 文件夹
"""

import os
import sys
import logging
from datetime import datetime

# 项目根目录
ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')

_initialized = False


def setup_logger():
    """
    初始化日志系统，每次启动生成一个新的日志文件
    文件名格式: toutiao_2026-02-10_14-30-00.log
    """
    global _initialized
    if _initialized:
        return logging.getLogger('toutiao')

    os.makedirs(LOGS_DIR, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(LOGS_DIR, f'toutiao_{timestamp}.log')

    logger = logging.getLogger('toutiao')
    logger.setLevel(logging.DEBUG)

    # 文件 handler - 记录所有级别
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    file_handler.setFormatter(file_fmt)

    # 控制台 handler - 只显示 INFO 以上
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        '[%(asctime)s] [%(levelname)-7s] %(message)s',
        datefmt='%H:%M:%S',
    )
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _initialized = True

    logger.info('=' * 60)
    logger.info('Toutiao Tool 启动')
    logger.info(f'日志文件: {log_file}')
    logger.info(f'Python: {sys.version}')
    logger.info(f'工作目录: {os.getcwd()}')
    logger.info('=' * 60)

    return logger


def get_logger(name='toutiao'):
    """获取子 logger"""
    return logging.getLogger(f'toutiao.{name}')
