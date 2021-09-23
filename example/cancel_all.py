import argparse
from binance.client import Client





def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', type=str, required=True,
                        help='api key')
    parser.add_argument('-s', '--secret', type=str, required=True,
                        help='secret')

    args = parser.parse_args()
    return args

proxies = {
    'http': 'http://127.0.0.1087',
    'https': 'http://127.0.0.1:1087'
}

if __name__ == '__main__':
    '''
    有需要的话可以使用该脚本撤掉某个账户的所有订单。
    '''
    args = parse()

    # proxies = {
    #     'http': 'http://127.0.0.1087',
    #     'https': 'http://127.0.0.1:1087'
    # }
    # client = Client(api_key, api_secret, {'proxies': proxies})
    client = Client(args.key, args.secret)
    client.futures_cancel_all_open_orders()