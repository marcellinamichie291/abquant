

from binance.client import Client
api_key = ""
api_secret = ""

proxies = {
    'http': 'http://127.0.0.1087',
    'https': 'http://127.0.0.1:1087'
}
if __name__ == '__main__':
    client = Client(api_key, api_secret, {'proxies': proxies})
    info = client.get_account()
    for item in info['balances']:
        print(item)
    balance = client.get_asset_balance(asset='BTC')

    # print('info', info)
    # print('info', balance)

    # products = client.get_products()
    # for product in products['data']:

    #     # if product['s'].endwith('USDT'):
    #     print(product)


    order = client.order_market_buy(
    symbol='XRPUSDT',
    quantity=7)
    print(order)