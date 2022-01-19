import time
from typing import Dict

from abquant.trader.common import OrderType, Direction, Offset
from abquant.trader.object import CancelRequest, OrderRequest, PositionData, OrderData
from abquantui.strategy_lifecycle import StrategyLifecycle
from tabulate import tabulate


class Liquidator(StrategyLifecycle):
    """
        With the accounts/gateways config in yaml config file,
        this class will directly liquidate all position and open orders with start() method
    """
    def __init__(self, config: Dict):
        super().__init__(config)
        self.order_manager = self._event_dispatcher.order_manager
        gw_cfg = self._config.get('gateway')
        self.gateway_second_rate_limits = {}
        self.gateway_minute_rate_limits = {}
        self.gateway_symbols = {}
        self.order_processed_second = {}
        self.order_processed_minute = {}
        for gateway_name, gateway in gw_cfg.items():
            self.gateway_second_rate_limits.update({gateway_name: gateway.get('second_limit')})
            self.gateway_minute_rate_limits.update({gateway_name: gateway.get('minute_limit')})
            self.gateway_symbols.update({gateway_name: gateway.get('target_symbol')})
            self.order_processed_second.update({gateway_name: 0})
            self.order_processed_minute.update({gateway_name: 0})

    def add_init_strategy(self):
        pass
    
    def log(self, msg):
        self._strategy_runner.write_log(msg)

    def start(self):
        try:
            self.liquidate()
        except Exception as e:
            self.log(e)

    def status(self):
        try:
            ret = self.get_current_status_str()
        except Exception as e:
            self.log(e)
            ret = 'Error when fetching liquidation status'
        return ret

    def liquidate(self):
        gateway_names = self.gateways.keys()
        if len(gateway_names) == 0:
            return
        self.log(f"Liquidator START >>>>>>>>>>>>")
        remains_position = True
        while remains_position:
            remains_position = self.clear_position()
            if remains_position:
                time.sleep(12)
        remains_orders = True
        while remains_orders:
            remains_orders = self.cancel_orders()
            if remains_orders:
                time.sleep(12)
        self.log("Liquidator END <<<<<<<<<<<<")

    def clear_position(self):
        """ """
        try:
            position_list: Dict = self.order_manager.positions
        except:
            self.log(f"Warning: error occur getting order manager positions")
            return False
        if not position_list:
            return False
        action = False
        for pkey in position_list:
            position: PositionData = position_list[pkey]
            if position.volume == 0:
                continue
            gateway = self.gateways[position.gateway_name]
            symbol = self.gateway_symbols[position.gateway_name]
            if not gateway:
                self.log(f"Warning: no gateway [{position.gateway_name}] found for position "
                             f"[{position.gateway_name}-{position.symbol}-{position.volume}]")
                continue
            direction = Direction.LONG if position.volume < 0 else Direction.SHORT
            posym = position.symbol
            if symbol and symbol != posym:
                continue
            req = OrderRequest(
                symbol=posym,
                exchange=position.exchange,
                direction=direction,
                offset=Offset.CLOSE,
                type=OrderType.MARKET,
                price=position.price,
                volume=abs(position.volume)
            )
            ab_orderid = gateway.send_order(req)
            action = True
            self.log(f"Liquidator: position [{gateway.gateway_name} {posym} {position.volume}] called to CLEAR !\n"
                  f"Liquidator: client order id: {ab_orderid}")
        return action

    def cancel_orders(self):
        """  """
        try:
            order_list: Dict = self.order_manager.orders
        except:
            self.log(f"Warning: error occur getting order manager orders")
            return False
        if not order_list:
            return False
        order_num = len(order_list)
        action = False
        for okey in order_list:
            order: OrderData = order_list[okey]
            symbol = self.gateway_symbols[order.gateway_name]
            if symbol and symbol != order.symbol:
                continue
            gateway_name = order.gateway_name
            gateway = self.gateways[order.gateway_name]
            if not gateway:
                self.log(f"Warning: no gateway [{gateway_name}] found for position "
                             f"[{order.gateway_name}-{order.symbol}-{order.volume}-{order.direction}]")
                continue
            second_remaining = self.gateway_second_rate_limits[gateway_name]
            minute_remaining = self.gateway_minute_rate_limits[gateway_name]
            order_processed_second = self.order_processed_second[gateway_name]
            order_processed_minute = self.order_processed_minute[gateway_name]
            self.order_processed_second.update({gateway_name: order_processed_second + 1})
            self.order_processed_minute.update({gateway_name: order_processed_minute + 1})
            if order_num >= second_remaining:
                if order_processed_second > second_remaining - 1:
                    self.log(f"gateway {gateway.gateway_name} exceed second limit {second_remaining}, sleep 10 secs")
                    self.order_processed_second.update({gateway_name: 0})
                    return True
            if order_num >= minute_remaining:
                if order_processed_minute > minute_remaining - 1:
                    self.log(f"gateway {gateway.gateway_name} exceed minute limit {minute_remaining}, sleep 60 secs")
                    self.order_processed_minute.update({gateway_name: 0})
                    time.sleep(50)
                    return True
            req = CancelRequest(orderid=order.orderid, symbol=order.symbol, exchange=order.exchange)
            gateway.cancel_order(req)
            action = True
            self.log(f"Liquidator: order [{gateway_name} {order.symbol} {order.volume} {order.direction.name} "
                  f"{order.orderid}] called to CANCEL !")
        return action

    def get_current_status_str(self) -> str:
        content = '\nCurrent Position:\n'
        positions: Dict = self.order_manager.positions
        available = False
        position_list = []
        for pkey, position in positions.items():
            if position.volume != 0:
                position_list.append({'gateway': position.gateway_name, 'symbol': position.symbol,
                                      'volume': str(position.volume), 'price': str(position.price)})
                available = True
        if available:
            content += tabulate(position_list, headers="keys", tablefmt="psql") + '\n'
        else:
            content += tabulate([{'key':'No position'}], tablefmt="psql")+ '\n'
        content += 'Open Orders:\n'
        orders: dict = self.order_manager.orders
        available = False
        order_list = []
        order_num = len(orders)
        order_i = 0
        has_ellipsis = True if order_num > 50 else False
        for okey, order in orders.items():
            if order.volume != 0:
                if has_ellipsis and order_i == 25:
                    order_list.append({'time': '...'})
                elif has_ellipsis and order_i > 25 and order_i < order_num - 25:
                    pass
                else:
                    order_list.append({'time': str(order.datetime)[:19], 'gateway': order.gateway_name,
                                   'symbol': order.symbol, 'volume': order.volume,
                                   'price': order.price, 'direction': order.direction.name})
                available = True
            order_i += 1
        if available:
            content += tabulate(order_list, headers="keys", tablefmt="psql")
        else:
            content += tabulate([{'key':'No order'}], tablefmt="psql")
        return content
