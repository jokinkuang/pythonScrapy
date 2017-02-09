# -*- coding: utf-8 -*-

# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'crashMonitor'

SPIDER_MODULES = ['crashMonitor.spiders']
NEWSPIDER_MODULE = 'crashMonitor.spiders'

# Scrapy Settings
LOG_LEVEL = 'INFO'           #scrapy log level
COOKIES_DEBUG = False

DEVELOPING = True             #如果开启，则所有邮件只发送到maintainer，所以测试结束需置为False

# Project Settings
YY_MODULE_NAME = 'gametask' #搜索关键字 模块名称
YY_BUSINESS_NAME = ''        #搜索关键字 业务名称
YY_USERNAME = 'kuangzukai'  #崩溃网站登录名
YY_PASSWORD = '123456'      #崩溃网站登录密码
CRASH_TABLE_SIZE = 20        #TOP 20
CRASH_WARNING_LINE = 50      #崩溃告警线 （只有monitor模式监控才有告警邮件）

# Email Settings
MAIL_ENABLED = True
MAIL_SUBJECT = '游戏宝贝模板'
MAIL_HOST = 'mail.yy.com'
MAIL_PORT = 25
MAIL_FROM = '<kuangzukai@yy.com>'         #MAIL_FROM要与MAIL_USER一致，否则可能无法发送邮件
MAIL_USER = 'kuangzukai@yy.com'
MAIL_PASS = 'Kuangzukai'

MAIL_CC = []    #抄送
MAIL_TO = {
            "daily": ["kuangzukai@yy.com","gaozili@yy.com","chenyuxuan@yy.com"], #崩溃日报（当日）发送列表
            "weekly": ["kuangzukai@yy.com","gaozili@yy.com","chenyuxuan@yy.com","liyaochun@yy.com","zhoujun@yy.com","guoliping@yy.com"], #崩溃周报（过去一周）发送列表
            "custom": ["kuangzukai@yy.com"], #自定义查询发送列表
            "crash": ["kuangzukai@yy.com","gaozili@yy.com","chenyuxuan@yy.com","345106552@qq.com","340625992@qq.com","409165447@qq.com"], #崩溃告警发送列表
            "maintainer": ["kuangzukai@yy.com"] #开发时发送列表（维护者）
          }



