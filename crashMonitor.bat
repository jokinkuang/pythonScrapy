@echo off

C:\Python27\Scripts\scrapy.exe crawl crashMonitor

if "%1"=="" (
	pause
)