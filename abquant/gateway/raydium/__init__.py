import pathlib
import json
from typing import Dict
import base64

# rest api
REST_HOST: str = "https://api.mainnet-beta.solana.com/"

# websocket api
WEBSOCKET_HOST: str = "wss://solana--mainnet.datahub.figment.io/apikey/1dd9da503d7798e9bd06025ccbf58083"


parent_path = pathlib.Path(__file__).parent
pools_path = parent_path.joinpath('raydium_pools.json')
with open(pools_path, 'r') as load_f:
    pools_dict = json.load(load_f)


def pool_info(symbol: str):
    """
    Get the pool information for this symbol(pairs)
    """
    return pools_dict[symbol]


LIQUIDITY_FEES_NUMERATOR = 9975
LIQUIDITY_FEES_DENOMINATOR = 10000


def cal_output_amount(input_amount: float, input_reserve: float, output_reserve: float):
    input_amount_with_fee = input_amount * LIQUIDITY_FEES_NUMERATOR
    numerator = input_amount_with_fee * output_reserve
    denominator = input_reserve * LIQUIDITY_FEES_DENOMINATOR + input_amount_with_fee
    output_amount = numerator / denominator
    return output_amount


subscribe_id = 100


def new_subscribe_id():
    """start at 100"""
    global subscribe_id
    subscribe_id += 1
    return subscribe_id


def base64_decode(data, layout):
    data_decode = base64.b64decode(data)
    structured_data = layout.parse(data_decode)
    return structured_data



subscription_sid_map: Dict[int, int] = {}

sid_account_map: Dict[int, str] = {}

account_type_map: Dict[str, str] = {}

account_symbol_map: Dict[str, str] = {}


class RaydiumLiquidityDate(object):
    """
    The data needed to calculate raydium`s liquidity
    """
    base_need_take_pnl: int = 0
    quote_need_take_pnl: int = 0
    base_vault_balance: int = 0
    quote_vault_balance: int = 0
    open_order_base_token_amount: int = 0
    open_order_quote_token_amount: int = 0
    base_decimals: int
    quote_decimals: int

    def __init__(self, base_decimals: int, quote_decimals: int):
        self.base_decimals = base_decimals
        self.quote_decimals = quote_decimals


symbol_liquidity_map: Dict[str, RaydiumLiquidityDate] = {}

# all supported symbols
raydium_symbols = ['CWARUSDC', 'soFTTSRM', 'ATLASUSDC', 'FIDARAY', 'USDTUSDC', 'MNDEmSOL', 'CAVEUSDC', 'YAWUSDC',
                   'SYPUSDC', 'LIQUSDC', 'renDOGEUSDC', 'MNGOUSDC', 'SANDUSDC', 'SYPRAY', 'WOOFRAY', 'XCOPEUSDC',
                   'SVTUSDC', 'soETHSRM', 'APEXUSDC', 'soFTTUSDC', 'APTUSDC', 'CRWNYUSDC', 'soFTTUSDT', 'STEPUSDC',
                   'ETHWSOL', 'PRISMUSDC', 'WSOLUSDC', 'SBRUSDC', 'INUSDC', 'soSUSHIUSDC', 'SNYUSDC', 'POLISRAY',
                   'MAPSRAY', 'MEDIARAY', 'renBTCUSDC', 'CYSUSDC', 'ISOLAUSDT', 'stSOLUSDC', 'MBSUSDC', 'mSOLRAY',
                   'MERPAI', 'BTCUSDC', 'KINRAY', 'PORTUSDC', 'RAYUSDC', 'SOLCUSDT', 'soLINKSRM', 'JSOLUSDC', 'FABUSDC',
                   'SAMOUSDC', 'RINUSDC', 'PRTWSOL', 'WSOLUSDT', 'SLRSUSDC', 'MANAUSDC', 'soYFIUSDT', 'soYFIUSDC',
                   'OXSUSDC', 'soALEPHRAY', 'GENERAY', 'DFLUSDC', 'COPERAY', 'SLIMWSOL', 'RAYsoETH', 'UNIUSDC',
                   'soTOMOUSDC', 'SRMUSDC', 'MEDIAUSDC', 'TULIPUSDC', 'stSOLWSOL', 'soETHWSOL', 'SUSHIUSDC',
                   'POLISUSDC', 'LARIXUSDC', 'REALUSDC', 'SRMUSDT', 'SNYRAY', 'BTCUSDT', 'soETHUSDC', 'DXLUSDC',
                   'FANTUSDC', 'RAYWSOL', 'OXYRAY', 'mSOLUSDT', 'SPWNUSDC', 'MERUSDC', 'MERRAY', 'soSUSHISRM',
                   'BOTUSDC', 'ROPEUSDC', 'DYDXUSDC', 'BLOCKUSDC', 'NOSUSDC', 'SONARUSDC', 'STARSUSDC', 'JSOLWSOL',
                   'SYPWSOL', 'LIKERAY', 'COPEUSDC', 'soTOMOSRM', 'TULIPRAY', 'MIMOWSOL', 'WOOUSDC', 'RAYUSDT',
                   'BTCSRM', 'soSUSHIUSDT', 'soLINKUSDT', 'STRUSDC', 'LARIXRAY', 'mSOLWSOL', 'AURYUSDC', 'GENEUSDC',
                   'ETHUSDC', 'SRMWSOL', 'SAMORAY', 'WOOFUSDC', 'ATLASRAY', 'BNBUSDC', 'WAGUSDC', 'BOKUUSDC', 'UPSUSDC',
                   'SHILLUSDC', 'KKOUSDC', 'RAYSRM', 'soALEPHUSDC', 'soYFISRM', 'PEOPLEUSDC', 'soETHmSOL', 'soTOMOUSDT',
                   'LIKEUSDC', 'ABRUSDC', 'SLNDUSDC', 'FRKTWSOL', 'CRWNYRAY', 'TTTUSDC', 'soETHUSDT', 'AXSetUSDC',
                   'soLINKUSDC', 'LIQRAY', 'XTAGUSDC', 'SLRSRAY', 'VIUSDC', 'BOPRAY', 'SHIBUSDC', 'GRAPEUSDC',
                   'BTCmSOL', 'mSOLUSDC', 'GOFXUSDC', 'RUNUSDC']