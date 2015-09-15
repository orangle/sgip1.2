sgip1.2 - python
============

> 基础代码来自于[fy_sgip4py](https://github.com/ElegantCloud/fy_sgip4py)
可能他们实现的sgip的版本比较早，有些东西不好用了，这里用的是1.2版本

主要的作用的是给用户发验证短息，所以有些功能没有完全实现，但是协议部分是可以使用的
实现的内容：
* sgip 协议的基本封包解包
* 通过sgip协议发送命令到网关
* sgip_webapi.py 通过http协议发送短信请求，sgip_webserver.py调用联通短信接口发送短信

主要是sgip.py 和 sgip_client.py 文件

sgip_webapi.py  sgip_webserver.py为了解决其他ip的服务器不能直接调用联通sgip协议的问题，整个实现比较简单，可以根据需求使用其他web框架（django，tornado等）和http客户端（requests等），还有对传输内容的校验和加密等。


