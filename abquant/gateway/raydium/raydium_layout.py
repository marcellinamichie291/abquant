from construct import Bytes, Padding, Int64ul
from construct import BitsInteger, BitsSwapped, BitStruct, Const, Flag
from construct import Struct

# Serum Open Orders Book
ACCOUNT_FLAGS_LAYOUT = BitsSwapped(
    BitStruct(
        "initialized" / Flag,
        "market" / Flag,
        "open_orders" / Flag,
        "request_queue" / Flag,
        "event_queue" / Flag,
        "bids" / Flag,
        "asks" / Flag,
        Const(0, BitsInteger(57)),
    )
)

# Serum Open Orders Book
OPEN_ORDERS_LAYOUT = Struct(
    Padding(5),
    "account_flags" / ACCOUNT_FLAGS_LAYOUT,
    "market" / Bytes(32),
    "owner" / Bytes(32),
    "base_token_free" / Int64ul,
    "base_token_total" / Int64ul,
    "quote_token_free" / Int64ul,
    "quote_token_total" / Int64ul,
    "free_slot_bits" / Bytes(16),
    "is_bid_bits" / Bytes(16),
    "orders" / Bytes(16)[128],
    "client_ids" / Int64ul[128],
    "referrer_rebate_accrued" / Int64ul,
    Padding(7),
)

# Ray AMM Info
AMM_INFO_LAYOUT_V4 = Struct(

    "status" / Int64ul,
  "nonce" / Int64ul,
  "maxOrder" / Int64ul,
  "depth" / Int64ul,
  "baseDecimal" / Int64ul,
  "quoteDecimal" / Int64ul,
  "state" / Int64ul,
  "resetFlag" / Int64ul,
  "minSize" / Int64ul,
  "volMaxCutRatio" / Int64ul,
  "amountWaveRatio" / Int64ul,
  "baseLotSize" / Int64ul,
  "quoteLotSize" / Int64ul,
  "minPriceMultiplier" / Int64ul,
  "maxPriceMultiplier" / Int64ul,
  "systemDecimalValue" / Int64ul,
  "minSeparateNumerator" / Int64ul,
  "minSeparateDenominator" / Int64ul,
  "tradeFeeNumerator" / Int64ul,
  "tradeFeeDenominator" / Int64ul,
  "pnlNumerator" / Int64ul,
  "pnlDenominator" / Int64ul,
  "swapFeeNumerator" / Int64ul,
  "swapFeeDenominator" / Int64ul,
  "baseNeedTakePnl" / Int64ul,
  "quoteNeedTakePnl" / Int64ul,
  "quoteTotalPnl" / Int64ul,
  "baseTotalPnl" / Int64ul,
)