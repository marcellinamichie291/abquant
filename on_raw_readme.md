#on_raw 事件接收数据结构
##raw_data -> Dict:
- **type** -> str:<br>
可选项：
   - data_restful （API请求的返回结果）
   - data_websocket （websocket通知消息）
   - status_websocket_user_connected （websocket用户数据链接建立消息）
   - status_websocket_user_disconnected （websocket用户数据链接断开消息）

        
- **gateway_name** ->str:<br>
取*gateway*的*gateway_name*字段


- **data_type** ->str:<br>
可选项：
   - account  
   - position
   - order


- **payload** -> str:<br>
交易所返回的原始数据


- **time** -> float:<br>
当*raw_data*的*type*为*data_restfull*时才包含此字段<br>
用于记录request请求的耗时