@echo off

C:\Python27\Scripts\scrapy.exe crawl crashMonitor -a mode=weekly

if "%1"=="" (
	pause
)