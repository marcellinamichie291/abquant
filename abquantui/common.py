import os

from abquant.gateway import BinanceUBCGateway, BinanceBBCGateway, BinanceSGateway
from abquant.gateway import BitmexGateway, DydxGateway, BybitBBCGateway, BybitUBCGateway, BybitSpotGateway, FtxGateway


class GatewayName:
    BITMEX = 'BITMEX'
    BINANCEUBC = 'BINANCEUBC'
    BINANCEBBC = 'BINANCEBBC'
    BINANCES = 'BINANCES'
    DYDX = 'DYDX'
    BYBITS = 'BYBITS'
    BYBITBBC = 'BYBITBBC'
    BYBITUBC = 'BYBITUBC'
    FTX = 'FTX'


SUPPORTED_GATEWAY = {
    GatewayName.BITMEX: BitmexGateway,
    GatewayName.BINANCEUBC: BinanceUBCGateway,
    GatewayName.BINANCEBBC: BinanceBBCGateway,
    GatewayName.BINANCES: BinanceSGateway,
    GatewayName.DYDX: DydxGateway,
    GatewayName.BYBITS: BybitSpotGateway,
    GatewayName.BYBITUBC: BybitUBCGateway,
    GatewayName.BYBITBBC: BybitBBCGateway,
    GatewayName.FTX: FtxGateway
}

MINUTE_RATE_LIMITS = {
    GatewayName.BITMEX: 120,
    GatewayName.BINANCEUBC: 1000,
    GatewayName.BINANCEBBC: 1000,
    GatewayName.BINANCES: 1000,
    GatewayName.DYDX: 100,
    GatewayName.BYBITS: 100,
    GatewayName.BYBITUBC: 100,
    GatewayName.BYBITBBC: 100,
    GatewayName.FTX: 2100,
}

SECOND_RATE_LIMITS = {
    GatewayName.BITMEX: 20,
    GatewayName.BINANCEUBC: 200,
    GatewayName.BINANCEBBC: 200,
    GatewayName.BINANCES: 200,
    GatewayName.DYDX: 100,
    GatewayName.BYBITS: 100,
    GatewayName.BYBITUBC: 100,
    GatewayName.BYBITBBC: 100,
    GatewayName.FTX: 35,
}

