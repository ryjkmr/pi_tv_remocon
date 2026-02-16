# pi_tv_remocon
Raspberry Pi Zero 2 Wでブラウザから遠隔操作できるテレビリモコンを作った

https://ryjkmr.com/raspberry-pi-zero-2-w-tv-remocon/

## 起動方法
```
nohup python3 app.py &
```
## 終了方法
```
ps aux | grep app.py
```
でプロセスID（PID）を調べて、
```
kill [PID]
```
