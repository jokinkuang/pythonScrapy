@echo off

C:\Python27\Scripts\scrapy.exe crawl crashMonitor -a mode=daily

if "%1"=="" (
	pause
)