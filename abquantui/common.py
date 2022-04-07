import os

from abquant.gateway import BinanceUBCGateway, BinanceBBCGateway, BinanceSGateway
from abquant.gateway import BitmexGateway, DydxGateway, BybitBBCGateway, BybitUBCGateway


class GatewayName:
    BITMEX = 'BITMEX'
    BINANCEUBC = 'BINANCEUBC'
    BINANCEBBC = 'BINANCEBBC'
    BINANCES = 'BINANCES'
    DYDX = 'DYDX'
    BYBITBBC = 'BYBITBBC'
    BYBITUBC = 'BYBITUBC'


SUPPORTED_GATEWAY = {
    GatewayName.BITMEX: BitmexGateway,
    GatewayName.BINANCEUBC: BinanceUBCGateway,
    GatewayName.BINANCEBBC: BinanceBBCGateway,
    GatewayName.BINANCES: BinanceSGateway,
    GatewayName.DYDX: DydxGateway,
    GatewayName.BYBITUBC: BybitUBCGateway,
    GatewayName.BYBITBBC: BybitBBCGateway
}

MINUTE_RATE_LIMITS = {
    GatewayName.BITMEX: 120,
    GatewayName.BINANCEUBC: 1000,
    GatewayName.BINANCEBBC: 1000,
    GatewayName.BINANCES: 1000,
    GatewayName.DYDX: 100,
    GatewayName.BYBITUBC: 100,
    GatewayName.BYBITBBC: 100
}

SECOND_RATE_LIMITS = {
    GatewayName.BITMEX: 20,
    GatewayName.BINANCEUBC: 200,
    GatewayName.BINANCEBBC: 200,
    GatewayName.BINANCES: 200,
    GatewayName.DYDX: 100,
    GatewayName.BYBITUBC: 100,
    GatewayName.BYBITBBC: 100
}

